# Spec Delta

## ADDED Requirements

### Requirement: Verified launch engine
Before image inspection, building, or session startup, the wrapper SHALL verify that the engine used for those operations reports Linux and rootless operation explicitly. Query failure, rootful operation, or missing or unexpected fields SHALL fail with an actionable error. This requirement SHALL apply independently of YOLO, shell mode, and `--container-build`; wrapper help SHALL require no engine query.

#### Scenario: Rootless engine without a Podman API socket
- **WHEN** local Podman reports a Linux rootless engine
- **THEN** startup can proceed without requiring or exposing any Podman API socket

#### Scenario: Invalid launch engine
- **WHEN** launch-engine information fails or reports rootful, non-Linux, missing, or unexpected required fields
- **THEN** the wrapper exits nonzero before image inspection, building, or session startup

### Requirement: Local or explicit same-host Unix execution
The wrapper SHALL support local Podman and explicit absolute Unix `CONTAINER_HOST` on the same Linux host. Before any Podman query, it SHALL reject nonempty `CONTAINER_CONNECTION`, non-Unix or non-absolute `CONTAINER_HOST`, and Unix paths containing only slashes. Service-remote operation without an explicit Unix endpoint and unverifiable service-remote status SHALL fail closed before image operations.

#### Scenario: Unsupported connection
- **WHEN** the caller selects a named connection, TCP/SSH endpoint, or implicit remote engine
- **THEN** startup fails with guidance to use local Podman or an explicit same-host Unix socket

#### Scenario: Wrapper inside a container
- **WHEN** `CONTAINER_HOST` names an absolute Unix socket for a verified same-host Linux rootless engine
- **THEN** the wrapper can use that engine while preserving host absolute paths for workspace and state bind sources

#### Scenario: Slash-only Unix endpoints
- **WHEN** `CONTAINER_HOST` is `unix://`, `unix:///`, `unix:////`, or any endpoint whose path consists only of slashes
- **THEN** startup fails with guidance to supply an absolute socket path beyond the root directory
- **AND** no Podman query, image operation, or session creation occurs

#### Scenario: Valid absolute socket path
- **WHEN** `CONTAINER_HOST` names an absolute path containing a non-slash character and the selected service satisfies the engine checks
- **THEN** the endpoint is accepted without changing its path or requiring a local engine

### Requirement: Preserve Podman verification response boundaries
The wrapper SHALL validate complete successful Podman verification responses, allowing zero or one final LF terminator. After removing at most one terminator, the launch response SHALL have exactly one record. Additional blank or nonblank records and CR characters SHALL be rejected before image operations or startup. Failed queries SHALL remain failures even when their output looks valid.

#### Scenario: Normal response termination
- **WHEN** a successful launch response contains one valid record, with no final LF or exactly one final LF
- **THEN** record-boundary validation accepts the response and the existing field checks still apply

#### Scenario: Extra blank records
- **WHEN** the verification response contains leading, interior, or additional trailing blank records beyond its required format
- **THEN** startup fails before image inspection, building, or session creation
- **AND** trailing newlines are not silently discarded to make the response valid

#### Scenario: Extra nonblank records or CR
- **WHEN** a response includes an additional nonblank record or a CR character
- **THEN** the wrapper rejects it as an invalid verification response

#### Scenario: Failed query with valid-looking output
- **WHEN** a verification query exits nonzero after writing otherwise valid records
- **THEN** startup fails and no image operation or session creation occurs

### Requirement: Document verification input boundaries
Help and README SHALL explain that Unix launch endpoints require an absolute socket path beyond the root directory and that malformed or additional Podman verification records stop startup. Runtime guidance SHALL document the one-record launch format and its optional final LF.

#### Scenario: Diagnose rejected verification
- **WHEN** a user reads the connection and verification guidance
- **THEN** they find the endpoint constraint, the record format, normal terminator policy, and rejection of additional records

### Requirement: Leftover delegation opt-in is refused
An exact `CODEX_CONTAINER_PODMAN=1` in the launch environment SHALL stop every session launch and build-only operation, in every network mode, before any engine query or image operation. The diagnostic SHALL state that host Podman delegation was removed. It SHALL direct the operator to add needed images as toolchains and to unset the variable. Other values of the variable, and the former socket override, SHALL be ignored.

#### Scenario: Unrestricted launch with the old opt-in
- **WHEN** an operator starts an unrestricted session with `CODEX_CONTAINER_PODMAN=1`
- **THEN** the wrapper exits nonzero before querying an engine, names the variable, and points to image toolchains and the README section on container tests

#### Scenario: Other values
- **WHEN** `CODEX_CONTAINER_PODMAN` is empty or `0`, or `CODEX_CONTAINER_PODMAN_SOCKET` is set
- **THEN** the launch proceeds as if the variables were unset, and no Podman socket is mounted

#### Scenario: Help and toolchain commands
- **WHEN** `--container-help` or `--container-toolchain list` runs with `CODEX_CONTAINER_PODMAN=1`
- **THEN** the command succeeds unchanged

## MODIFIED Requirements

### Requirement: Case-insensitive YOLO environment values
The wrapper SHALL parse `CODEX_YOLO` case-insensitively. Values `1`, `true`, and `yes` SHALL enable wrapper-added YOLO; unset, empty, `0`, `false`, and `no` SHALL disable it. Other values SHALL fail before image operations or startup. Shell mode SHALL validate the value without adding Codex arguments. Help and README SHALL document the accepted values.

#### Scenario: Mixed-case enabled values
- **WHEN** a Codex invocation sets `CODEX_YOLO` to `TrUe`, `YeS`, or another capitalization of an enabled word
- **THEN** the wrapper adds `--yolo` before the unchanged user arguments, retaining their order and boundaries

#### Scenario: Mixed-case disabled values
- **WHEN** `CODEX_YOLO` is unset, empty, `0`, or any capitalization of `false` or `no`
- **THEN** the wrapper does not add `--yolo`
- **AND** explicit native arguments and saved settings retain their existing behavior

#### Scenario: Invalid values
- **WHEN** `CODEX_YOLO` is an unsupported value such as `enabled`, `2`, or a boolean word surrounded by spaces
- **THEN** the wrapper fails with accepted-value guidance before image inspection, building, or session creation

#### Scenario: Shell-mode compatibility
- **WHEN** shell mode receives any valid case-insensitive YOLO value
- **THEN** Bash starts without wrapper-added Codex arguments
- **AND** invalid values remain errors in shell mode

#### Scenario: Exact Podman opt-in remains independent
- **WHEN** a valid mixed-case YOLO value is combined with `CODEX_CONTAINER_PODMAN` equal to `1`, `TrUe`, or `YeS`
- **THEN** only exactly `1` stops the launch as a leftover delegation opt-in, independently of the YOLO value, and the other values are ignored
- **AND** YOLO normalization does not change workspace mounts or the read-only image filesystem

### Requirement: Read-only engine queries are bounded
Every read-only engine query (`info`, `version`, `ps`, image and container existence and inspection, the session container engine's readiness query) SHALL be bounded by a timeout. A response with a carriage return or extra records SHALL be refused. `create`, `start`, `build` and `pull` SHALL NOT be bounded.

#### Scenario: Stalled engine query
- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container
