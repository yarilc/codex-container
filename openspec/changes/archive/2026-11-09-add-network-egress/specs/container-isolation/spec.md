## ADDED Requirements

### Requirement: Explicit isolated application home
A nonempty `CODEX_CONTAINER_STATE_DIR` SHALL select a dedicated writable home mounted at `/codex-home`, containing Codex state, caches and other home data, with `CODEX_HOME=/codex-home/.codex`. The wrapper SHALL NOT mount the shared host `CODEX_HOME` in this mode. A simultaneous nonempty host `CODEX_HOME` SHALL fail with a conflict error before image operations or launch.

#### Scenario: Fresh isolated profile
- **WHEN** a dedicated state directory is selected and host `CODEX_HOME` is unset or empty
- **THEN** the container uses `HOME=/codex-home` and `CODEX_HOME=/codex-home/.codex`, with state persisted under the selected directory
- **AND** no shared host Codex state is mounted or imported

#### Scenario: Conflicting state controls
- **WHEN** dedicated state and a nonempty host `CODEX_HOME` are both selected
- **THEN** startup fails before image operations with instructions to select one state mode

#### Scenario: Isolated paths escape the home
- **WHEN** `.codex` or the CA mount parent inside the isolated home resolves outside it through a symlink
- **THEN** startup fails before image operations and nothing is created outside the home

#### Scenario: Qualification uses isolated state
- **WHEN** `--container-qualify` runs its phases
- **THEN** each phase uses its own disposable isolated state home and never reads or writes the user's `CODEX_HOME`

### Requirement: Isolated home privacy
The wrapper SHALL create the isolated home and its `.codex` directory privately, resolve the physical path, and require caller ownership, read/write/search access and no group/other permission bits on both. It SHALL NOT repair existing permissions recursively, and SHALL reject filesystems that do not enforce user-only modes.

#### Scenario: Unsafe isolated home
- **WHEN** the isolated home or its `.codex` has the wrong owner, lacks access or grants group/other access
- **THEN** startup fails with a path-specific error before image operations, without changing existing permissions

## MODIFIED Requirements

### Requirement: Private persistent state directory

Without `CODEX_CONTAINER_STATE_DIR`, the wrapper SHALL create missing `CODEX_HOME` privately, resolve its physical path, and require caller ownership, read/write/search access and no group/other permission bits. The default SHALL remain `${HOME}/.codex`, and validated state SHALL remain mounted read/write at `/codex-home/.codex` in Codex and shell modes. In restricted modes the validated state directory SHALL be declared writable to the protected-installation checks.

#### Scenario: Create private state
- **WHEN** the selected state directory is absent on a filesystem enforcing Unix permissions
- **THEN** the wrapper creates it with mode `0700` and validates its ownership and access before image inspection, building, or startup
- **AND** the state creation mask does not change subsequent workspace file creation policy

#### Scenario: Existing valid state through a symbolic path
- **WHEN** `CODEX_HOME` names an accessible caller-owned private directory through a relative or symbolic path
- **THEN** the wrapper uses the resolved physical absolute directory as the persistent bind source
- **AND** existing state contents remain available without copying or migration

#### Scenario: Reject insecure or inaccessible state
- **WHEN** state is not a directory, belongs to another user, grants group/other permissions, is inaccessible, or cannot be resolved
- **THEN** the wrapper exits nonzero before image inspection, building, or startup
- **AND** the error identifies the directory and suggests permission correction or a private `CODEX_HOME` as appropriate
- **AND** the wrapper does not change existing permissions or ownership recursively or silently repair the directory

#### Scenario: Filesystem does not enforce private modes
- **WHEN** state creation succeeds but the filesystem does not enforce user-only permissions
- **THEN** startup fails with guidance to select private storage on a filesystem enforcing Unix permissions

#### Scenario: Help has no state side effects
- **WHEN** `--container-help` is requested with missing or insecure state
- **THEN** help succeeds without creating, validating, or modifying the state directory

#### Scenario: Protected installation outside state
- **WHEN** a restricted session starts and the wrapper checkout, guard, policy or profile lies inside the state directory or the workspace
- **THEN** startup fails before the agent runs

### Requirement: Document persistent state protection

The README and runtime guidance SHALL explain state privacy checks, the default shared host `~/.codex`, use of a separate `CODEX_HOME`, the isolated `CODEX_CONTAINER_STATE_DIR` home and its conflict with `CODEX_HOME`, and migration errors on insecure directories or filesystems. Documentation SHALL distinguish directory access control from encryption and state that writable persistent state remains available to the agent.

#### Scenario: Existing user migrates
- **WHEN** a user reads the migration instructions
- **THEN** they find an explicit `chmod 700` correction for their own existing directory and a separate private Linux state example
- **AND** they learn that changing the state path selects different configuration and sessions without automatic copying
- **AND** checks on the selected directory do not establish the privacy of every ancestor, ACL, or existing file

#### Scenario: User selects an isolated home
- **WHEN** a user reads about `CODEX_CONTAINER_STATE_DIR`
- **THEN** they learn that it replaces the shared `CODEX_HOME`, requires a separate login, and cannot be combined with a host `CODEX_HOME`
