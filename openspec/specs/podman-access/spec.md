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

With Podman access enabled, the wrapper SHALL provide the Podman command, validate `/run/user/<host-uid>/podman/podman.sock`, mount it at `/run/podman/podman.sock`, and set `CONTAINER_HOST=unix:///run/podman/podman.sock`. Missing sockets SHALL produce an actionable error before starting a session. Access SHALL NOT require privileged mode or a nested daemon.

#### Scenario: Enabled service access
- **WHEN** the opt-in is enabled and the host socket is usable
- **THEN** the in-container Podman command can contact the host service
- **AND** the image filesystem remains read-only

#### Scenario: Missing enabled socket
- **WHEN** the opt-in is enabled and the expected socket is absent
- **THEN** startup fails with the expected path and instructions to start the service

### Requirement: Keep one image for both access modes

Both access modes SHALL use the same image selection and build behavior, including `--container-build` and `CODEX_CONTAINER_IMAGE`. The supplied image SHALL retain the Podman command independently of the access setting.

#### Scenario: Switch from enabled to disabled
- **WHEN** an enabled session has run and the next invocation omits the opt-in
- **THEN** the next runtime uses the same image with the Podman command installed
- **AND** it has no supplied host socket or `CONTAINER_HOST`

### Requirement: Document the access boundary

Help, README, and repository runtime guidance SHALL describe the exact opt-in, conditional socket setup, read-only behavior, writable exceptions, and the host control granted by the socket. Documentation SHALL distinguish the always-installed command from optional host service access.

#### Scenario: Discover configuration and migration
- **WHEN** a user reads the wrapper help and README
- **THEN** default and enabled invocations are shown and existing users are told how to restore child-container access
- **AND** socket setup is required only for enabled access
