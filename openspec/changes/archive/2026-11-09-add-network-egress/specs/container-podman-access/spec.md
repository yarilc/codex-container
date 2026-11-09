## ADDED Requirements

### Requirement: Delegation only in unrestricted mode
`CODEX_CONTAINER_PODMAN=1` SHALL be accepted only with explicit `CODEX_CONTAINER_NETWORK=unrestricted`. In offline and provider modes it SHALL fail before image or resource operations, explaining that the host API bypasses egress enforcement. Shell, YOLO and native permission settings SHALL NOT change this.

#### Scenario: Delegation requested in a restricted mode
- **WHEN** the wrapper starts in offline or provider mode with `CODEX_CONTAINER_PODMAN=1`, in Codex or shell mode, with or without YOLO
- **THEN** it exits nonzero before image or resource operations and names explicit unrestricted mode as the only mode with delegation

#### Scenario: Delegation in unrestricted mode
- **WHEN** the wrapper starts in unrestricted mode with `CODEX_CONTAINER_PODMAN=1`
- **THEN** delegation behaves as before this change

## MODIFIED Requirements

### Requirement: Explicit Podman opt-in

The wrapper SHALL enable its host Podman service integration only when `CODEX_CONTAINER_PODMAN` equals exactly `1` and the network mode is explicit `unrestricted`. An unset variable, an empty string, or any other value SHALL disable that integration. The rule SHALL apply to Codex and shell modes and SHALL NOT remove the host Podman requirement for building and starting the runtime.

#### Scenario: Default and non-enabling values
- **WHEN** the variable is unset, empty, `0`, `true`, or any value other than `1`
- **THEN** the session starts with the host Podman service integration disabled

#### Scenario: Exact opt-in
- **WHEN** the wrapper starts in unrestricted mode with `CODEX_CONTAINER_PODMAN=1`
- **THEN** the session has the host Podman service integration enabled

### Requirement: Document the access boundary

Help, README, and repository runtime guidance SHALL describe the exact opt-in, its restriction to unrestricted mode, conditional socket setup, read-only behavior, writable exceptions, and the host control granted by the socket. Documentation SHALL distinguish the always-installed command from optional host service access and explain that enabled access requires automatic verification of a reachable rootless service.

#### Scenario: Discover configuration and migration
- **WHEN** a user reads the wrapper help and README
- **THEN** default and enabled invocations are shown and existing users are told how to restore child-container access with explicit unrestricted mode
- **AND** socket setup is required only for enabled access
- **AND** the automatic rootless verification and rejection of rootful or unverifiable services are explained

#### Scenario: Understand delegation and approval boundaries
- **WHEN** a user reads help and the README
- **THEN** they learn that socket access permits new host binds beyond the workspace using the service user's authority, and why it is rejected in restricted modes
- **AND** the README distinguishes agent permissions, internal sandboxing, and outer container isolation without treating disabled YOLO as enforcement of native CLI settings
- **AND** it shows all four YOLO and Podman-access combinations and states that rootless delegation cannot enforce project-only access

#### Scenario: Discover engine checks and socket selection
- **WHEN** a user reads the README and runtime guidance
- **THEN** they find the independent launch-engine requirement, Unix-only same-host support, socket precedence, host-path remapping, and explicit override examples
- **AND** they learn that disabled delegation does not require its socket but a Unix-connected launch engine still requires its own service
