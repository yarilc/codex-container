# Spec Delta

## MODIFIED Requirements

### Requirement: Enabled access uses the host rootless service

With Podman access enabled, the wrapper SHALL provide the Podman command, validate the selected Unix socket, mount its reported host-side path at `/run/podman/podman.sock`, and set `CONTAINER_HOST=unix:///run/podman/podman.sock`. Missing sockets SHALL produce an actionable error before starting a session. The wrapper SHALL verify that the service at that exact socket reports rootless operation before exposing it. A host-side path reported as a `unix://` URL SHALL be reduced to its path before validation. Access SHALL NOT require privileged mode or a nested daemon.

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

#### Scenario: Podman 5 reports a socket URL
- **WHEN** the selected service reports its host-side path as `unix:///run/user/1000/podman/podman.sock`
- **THEN** the wrapper mounts `/run/user/1000/podman/podman.sock` at `/run/podman/podman.sock`

#### Scenario: Invalid host-side socket path
- **WHEN** the selected service reports an empty or non-absolute host-side socket path, also after removing a `unix://` prefix
- **THEN** the wrapper fails with an actionable error before image inspection, building, or startup
