# podman-access Specification

## Purpose

Control the session's host Podman API access through an explicit environment opt-in while keeping the Podman command installed in the runtime.

## Requirements

### Requirement: Explicit Podman opt-in

The wrapper SHALL enable its host Podman service integration only when `CODEX_CONTAINER_PODMAN` equals exactly `1`. An unset variable, an empty string, or any other value SHALL disable that integration. The rule SHALL apply to Codex and shell modes and SHALL NOT remove the host Podman requirement for building and starting the runtime.

#### Scenario: Default and non-enabling values
- **WHEN** the variable is unset, empty, `0`, `true`, or any value other than `1`
- **THEN** the session starts with the host Podman service integration disabled

#### Scenario: Exact opt-in
- **WHEN** the wrapper starts with `CODEX_CONTAINER_PODMAN=1`
- **THEN** the session has the host Podman service integration enabled

### Requirement: Installed command without host connection when disabled

With the integration disabled, the runtime SHALL retain its installed Podman command. The wrapper SHALL NOT expose the host API socket, set or forward `CONTAINER_HOST`, or require the socket to exist. The command SHALL NOT have access to the host service through the wrapper's integration.

#### Scenario: Start without an API service
- **WHEN** Podman access is disabled and local host Podman works but its API socket is absent
- **THEN** the wrapper can build and start the session without a socket validation error
- **AND** `command -v podman` succeeds but the wrapper provides no connection to the host service
- **AND** `/run/podman/podman.sock` is not supplied and `CONTAINER_HOST` is unset

### Requirement: Enabled access uses the host rootless service

With Podman access enabled, the wrapper SHALL provide the Podman command, validate `/run/user/<host-uid>/podman/podman.sock`, mount it at `/run/podman/podman.sock`, and set `CONTAINER_HOST=unix:///run/podman/podman.sock`. Missing sockets SHALL produce an actionable error before starting a session. The wrapper SHALL verify that the service at that exact socket reports rootless operation before exposing it. Access SHALL NOT require privileged mode or a nested daemon.

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

### Requirement: Keep one image for both access modes

Both access modes SHALL use the same image selection and build behavior, including `--container-build` and `CODEX_CONTAINER_IMAGE`. The supplied image SHALL retain the Podman command independently of the access setting.

#### Scenario: Switch from enabled to disabled
- **WHEN** an enabled session has run and the next invocation omits the opt-in
- **THEN** the next runtime uses the same image with the Podman command installed
- **AND** it has no supplied host socket or `CONTAINER_HOST`

### Requirement: Document the access boundary

Help, README, and repository runtime guidance SHALL describe the exact opt-in, conditional socket setup, read-only behavior, writable exceptions, and the host control granted by the socket. Documentation SHALL distinguish the always-installed command from optional host service access and explain that enabled access requires automatic verification of a reachable rootless service.

#### Scenario: Discover configuration and migration
- **WHEN** a user reads the wrapper help and README
- **THEN** default and enabled invocations are shown and existing users are told how to restore child-container access
- **AND** socket setup is required only for enabled access
- **AND** the automatic rootless verification and rejection of rootful or unverifiable services are explained

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
- **AND** existing disabled-mode build and startup behavior remains available
