# Spec Delta

## MODIFIED Requirements

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

### Requirement: Document the access boundary

Help, README, and repository runtime guidance SHALL describe the exact opt-in, conditional socket setup, read-only behavior, writable exceptions, and the host control granted by the socket. Documentation SHALL distinguish the always-installed command from optional host service access and explain that enabled access requires automatic verification of a reachable rootless service.

#### Scenario: Discover configuration and migration
- **WHEN** a user reads the wrapper help and README
- **THEN** default and enabled invocations are shown and existing users are told how to restore child-container access
- **AND** socket setup is required only for enabled access
- **AND** the automatic rootless verification and rejection of rootful or unverifiable services are explained

## ADDED Requirements

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
