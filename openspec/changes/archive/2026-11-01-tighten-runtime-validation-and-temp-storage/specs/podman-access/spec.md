# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Preserve Podman verification response boundaries

The wrapper SHALL validate complete successful Podman verification responses, allowing zero or one final LF terminator. After removing at most one terminator, the launch response SHALL have exactly one record and the delegated-socket response exactly two. Additional blank or nonblank records and CR characters SHALL be rejected before image operations or startup. Failed queries SHALL remain failures even when their output looks valid.

#### Scenario: Normal response termination
- **WHEN** a successful launch response contains one valid record or a successful delegated response contains its two valid records, with no final LF or exactly one final LF
- **THEN** record-boundary validation accepts the response and the existing field checks still apply

#### Scenario: Extra blank records
- **WHEN** either verification response contains leading, interior, or additional trailing blank records beyond its required format
- **THEN** startup fails before image inspection, building, or session creation
- **AND** trailing newlines are not silently discarded to make the response valid

#### Scenario: Extra nonblank records or CR
- **WHEN** a response includes an additional nonblank record or a CR character
- **THEN** the wrapper rejects it as an invalid verification response

#### Scenario: Preserve Codex delegated response and spaces
- **WHEN** the selected service returns `true` on the first record and an absolute host socket path containing spaces on the second
- **THEN** the wrapper accepts the two-record format and retains the complete path as the socket bind source

#### Scenario: Failed query with valid-looking output
- **WHEN** a verification query exits nonzero after writing otherwise valid records
- **THEN** startup fails and no image operation or session creation occurs

### Requirement: Document verification input boundaries

Help and README SHALL explain that Unix launch endpoints require an absolute socket path beyond the root directory and that malformed or additional Podman verification records stop startup. Runtime guidance SHALL document the one-record launch and two-record delegated formats and their optional final LF.

#### Scenario: Diagnose rejected verification
- **WHEN** a user reads the connection and verification guidance
- **THEN** they find the endpoint constraint, record formats, normal terminator policy, and rejection of additional records
