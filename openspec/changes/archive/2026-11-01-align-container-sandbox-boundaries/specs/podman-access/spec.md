# Spec Delta

## ADDED Requirements

### Requirement: Verified launch engine

Before image inspection, building, or session startup, the wrapper SHALL verify that the engine used for those operations reports Linux and rootless operation explicitly. Query failure, rootful operation, or missing or unexpected fields SHALL fail with an actionable error. This requirement SHALL apply independently of delegation, YOLO, shell mode, and `--container-build`; wrapper help SHALL require no engine query.

#### Scenario: Rootless engine without delegation
- **WHEN** delegation is disabled and local Podman reports a Linux rootless engine
- **THEN** startup can proceed without querying or requiring the delegation socket

#### Scenario: Invalid launch engine
- **WHEN** launch-engine information fails or reports rootful, non-Linux, missing, or unexpected required fields
- **THEN** the wrapper exits nonzero before image inspection, building, or session startup
- **AND** a valid delegation service does not satisfy the launch-engine check

#### Scenario: Independent valid engines
- **WHEN** the launch engine and an explicitly selected delegation service are different valid rootless engines on the same host
- **THEN** each endpoint is verified independently and the launch engine performs image and container operations

### Requirement: Local or explicit same-host Unix execution

The wrapper SHALL support local Podman and explicit absolute Unix `CONTAINER_HOST` connections on the same Linux host. It SHALL reject nonempty `CONTAINER_CONNECTION`, non-Unix or non-absolute `CONTAINER_HOST`, and service-remote operation without an explicit Unix `CONTAINER_HOST` before image operations. Unverifiable service-remote status SHALL fail closed.

#### Scenario: Unsupported connection
- **WHEN** the caller selects a named connection, TCP/SSH endpoint, or implicit remote engine
- **THEN** startup fails with guidance to use local Podman or an explicit same-host Unix socket

#### Scenario: Wrapper inside a container
- **WHEN** `CONTAINER_HOST` names an absolute Unix socket for a verified same-host Linux rootless engine
- **THEN** the wrapper can use that engine while preserving host absolute paths for workspace and state bind sources

### Requirement: Explicit delegation socket selection

With delegation enabled, the wrapper SHALL select the first nonempty value from `CODEX_CONTAINER_PODMAN_SOCKET`, the path in an explicit Unix `CONTAINER_HOST`, and `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. The selected path SHALL be absolute, resolve to a readable and writable Unix socket, and be queried explicitly. Disabled delegation SHALL ignore the override.

#### Scenario: Selection precedence
- **WHEN** an explicit override, Unix launch connection, and runtime-directory default are all present
- **THEN** the explicit override selects the delegation endpoint without changing the launch endpoint
- **AND** without the override the Unix launch connection takes precedence over the runtime-directory default

#### Scenario: Default selection
- **WHEN** neither an override nor a Unix launch connection is present
- **THEN** the socket is selected under nonempty `XDG_RUNTIME_DIR`, or `/run/user/<uid>` when that variable is empty or unset

#### Scenario: Invalid selected socket
- **WHEN** delegation is enabled and the selected path is relative, missing, not a socket, inaccessible, or cannot be resolved
- **THEN** the wrapper fails with the selected path and relevant correction guidance before image operations or startup

#### Scenario: Disabled override ignored
- **WHEN** `CODEX_CONTAINER_PODMAN` is unset or has any value other than exactly `1` and the override points to an invalid path
- **THEN** that override causes no delegation query, mount, or startup error

## MODIFIED Requirements

### Requirement: Enabled access uses the host rootless service

With Podman access enabled, the wrapper SHALL provide the Podman command, validate the selected Unix socket, mount its reported host-side path at `/run/podman/podman.sock`, and set `CONTAINER_HOST=unix:///run/podman/podman.sock`. Missing sockets SHALL produce an actionable error before starting a session. The wrapper SHALL verify that the service at that exact socket reports rootless operation before exposing it. Access SHALL NOT require privileged mode or a nested daemon.

#### Scenario: Enabled service access
- **WHEN** the opt-in is enabled and the host socket is usable and reports a rootless engine
- **THEN** the in-container Podman command can contact the host service
- **AND** the image filesystem remains read-only

#### Scenario: Missing enabled socket
- **WHEN** the opt-in is enabled and the expected socket is absent
- **THEN** startup fails with the expected path and instructions to start the service

#### Scenario: Verify the exposed endpoint
- **WHEN** the opt-in is enabled and host client defaults or environment variables select another Podman endpoint
- **THEN** rootless verification explicitly targets the socket that the wrapper will mount
- **AND** a rootless result from a different endpoint does not satisfy the verification

#### Scenario: Socket remapped in a containerized caller
- **WHEN** the selected socket is visible to the wrapper at `/run/podman/podman.sock` and the service reports `/run/user/1000/podman/podman.sock` as its host-side path
- **THEN** the wrapper queries the visible socket explicitly and supplies the reported host-side path as the bind source
- **AND** the session receives `CONTAINER_HOST=unix:///run/podman/podman.sock`

#### Scenario: Invalid host-side socket path
- **WHEN** the selected service reports an empty or non-absolute host-side socket path
- **THEN** the wrapper fails with an actionable error before image inspection, building, or startup

### Requirement: Reject unverified Podman services before startup

When Podman access is enabled, the wrapper SHALL accept only an explicit rootless result of `true` from the selected service. Query failure, `false`, an empty result, or an unexpected result SHALL terminate with a nonzero exit and an actionable error before image inspection, image building, or session startup. This rule SHALL apply to Codex and shell modes, including `--container-build`.

#### Scenario: Reject a rootful service
- **WHEN** the enabled socket reports rootless as `false`
- **THEN** the wrapper exits with an error requiring a rootless service
- **AND** no image inspection, build, or session startup occurs

#### Scenario: Reject an unreachable service
- **WHEN** the enabled socket exists but the service query fails, including connection or permission errors
- **THEN** the wrapper exits with an error identifying the socket and suggesting service or permission checks
- **AND** no image inspection, build, or session startup occurs

#### Scenario: Reject an indeterminate service
- **WHEN** the query succeeds but returns an empty or unexpected rootless result
- **THEN** the wrapper exits with an error explaining that rootless operation could not be verified
- **AND** no image inspection, build, or session startup occurs

#### Scenario: Disabled integration skips service verification
- **WHEN** `CODEX_CONTAINER_PODMAN` is unset, empty, or any value other than `1`
- **THEN** the wrapper does not query the integration socket or require that service to be available
- **AND** build and startup remain available when the independent launch-engine and persistent-state preconditions pass

### Requirement: Document the access boundary

Help, README, and repository runtime guidance SHALL describe the exact opt-in, conditional socket setup, read-only behavior, writable exceptions, and the host control granted by the socket. Documentation SHALL distinguish the always-installed command from optional host service access and explain that enabled access requires automatic verification of a reachable rootless service.

#### Scenario: Discover configuration and migration
- **WHEN** a user reads the wrapper help and README
- **THEN** default and enabled invocations are shown and existing users are told how to restore child-container access
- **AND** socket setup is required only for enabled access
- **AND** the automatic rootless verification and rejection of rootful or unverifiable services are explained

#### Scenario: Understand delegation and approval boundaries
- **WHEN** a user reads help and the README
- **THEN** they learn that socket access permits new host binds beyond the workspace using the service user's authority
- **AND** the README distinguishes agent permissions, internal sandboxing, and outer container isolation without treating disabled YOLO as enforcement of native CLI settings
- **AND** it shows all four YOLO and Podman-access combinations and states that rootless delegation cannot enforce project-only access

#### Scenario: Discover engine checks and socket selection
- **WHEN** a user reads the README and runtime guidance
- **THEN** they find the independent launch-engine requirement, Unix-only same-host support, socket precedence, host-path remapping, and explicit override examples
- **AND** they learn that disabled delegation does not require its socket but a Unix-connected launch engine still requires its own service
