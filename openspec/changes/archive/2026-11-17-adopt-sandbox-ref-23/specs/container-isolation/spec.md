## ADDED Requirements

### Requirement: Read-only state
`CODEX_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the Codex configuration directory read-only below the ephemeral home. The directory is taken from shared state or from the isolated home, and SHALL already exist. The launcher SHALL NOT create it, SHALL NOT check its owner or privacy, and SHALL NOT pass it to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `CODEX_CONTAINER_READONLY_STATE=1` is set and `~/.codex` exists
- **THEN** the session sees `/codex-home/.codex` read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and the configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory

### Requirement: Bounded noexec temporary storage
In Codex and shell sessions, the wrapper SHALL cap the `/tmp` and `/var/tmp` tmpfs mounts at 512 MiB each, `/run` at 32 MiB and the ephemeral home at 512 MiB, independently of delegation and YOLO. All four SHALL be writable with `nosuid`, `nodev` and `noexec`, and `/tmp`, `/var/tmp` and the ephemeral home SHALL have mode 1777. The Codex profile SHALL NOT declare executable temporary storage (`native.exec_tmp`). These caps SHALL NOT change persistent bind mounts.

#### Scenario: Finite capacities in either session mode
- **WHEN** a Codex or shell session starts with any supported delegation and YOLO combination
- **THEN** `/tmp`, `/var/tmp` and the ephemeral home each have a 536870912-byte tmpfs capacity and `/run` has a 33554432-byte tmpfs capacity
- **AND** each keeps `nosuid`, `nodev` and `noexec`

#### Scenario: Temporary executables are refused
- **WHEN** the mapped user copies an executable into `/tmp`, `/var/tmp`, `/run` or `/codex-home` outside persistent state and runs it directly
- **THEN** the mount policy prevents execution, and ordinary file writes remain possible

#### Scenario: Exhaust a bounded mount
- **WHEN** a write would exceed the available capacity of `/tmp`, `/var/tmp`, `/run` or the ephemeral home
- **THEN** the write fails instead of expanding that mount beyond its configured capacity
- **AND** persistent workspace and state mounts retain their existing capacities and access

#### Scenario: Var tmp contents are ephemeral
- **WHEN** a session writes files under `/var/tmp`, exits, and a new session starts
- **THEN** the previous files are absent and `/var/tmp` retains its 512 MiB capacity

## REMOVED Requirements

### Requirement: Explicit temporary storage capacities
**Reason**: The shared launcher core gives every wrapper one temporary-storage layout (contract U7): `/tmp` and the ephemeral home are no longer executable, and the home gets a 512 MiB cap.
**Migration**: See "Bounded noexec temporary storage". Executables belong in the workspace, the state directory or the toolchain library.

## MODIFIED Requirements

### Requirement: Writable ephemeral runtime locations
The wrapper SHALL provide writable temporary storage in `/tmp`, `/var/tmp` and, without a writable isolated home, an ephemeral tmpfs home at `/codex-home` for the mapped runtime user. `/run` SHALL be an ephemeral tmpfs that the mapped runtime user cannot write. It SHALL mount persistent `CODEX_HOME` within that home and SHALL discard ephemeral session writes when the container is removed.

#### Scenario: Temporary and home writes succeed
- **WHEN** the mapped user creates files in `/tmp`, `/var/tmp` and in `/codex-home` outside `.codex`
- **THEN** those writes succeed without changing the image filesystem
- **AND** those files are absent in a fresh session
- **AND** writes inside `.codex` remain persistent
- **AND** a write to `/run` fails

### Requirement: Private persistent state directory
Without `CODEX_CONTAINER_STATE_DIR`, the wrapper SHALL create missing `CODEX_HOME` privately, resolve its physical path, and require caller ownership, read/write/search access and no group/other permission bits. A set `CODEX_HOME` SHALL be an absolute path without colon, CR or LF, checked before any engine query. The default SHALL remain `${HOME}/.codex`, and validated state SHALL remain mounted read/write at `/codex-home/.codex` in Codex and shell modes. In restricted modes the validated state directory SHALL be declared writable to the protected-installation checks.

#### Scenario: Create private state
- **WHEN** the selected state directory is absent on a filesystem enforcing Unix permissions
- **THEN** the wrapper creates it with mode `0700` and validates its ownership and access before image inspection, building, or startup
- **AND** the state creation mask does not change subsequent workspace file creation policy

#### Scenario: Existing valid state through a symbolic path
- **WHEN** `CODEX_HOME` names an accessible caller-owned private directory through an absolute path containing a symbolic link
- **THEN** the wrapper uses the resolved physical absolute directory as the persistent bind source
- **AND** existing state contents remain available without copying or migration

#### Scenario: Relative or unsafe configuration path
- **WHEN** `CODEX_HOME` is relative or contains a colon, CR or LF
- **THEN** the launch stops before any engine query and names `CODEX_HOME`

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

### Requirement: Document temporary storage boundaries
Help, README and runtime guidance SHALL state the `/tmp`, `/var/tmp`, `/run` and ephemeral home capacities and that all four are `noexec`. The README SHALL explain that these are per-mount maxima, not reserved memory or an overall container memory limit.

#### Scenario: User plans temporary storage
- **WHEN** a user reads the storage guidance
- **THEN** they find all four mount capacities, the `noexec` policy, and the distinction from a total memory limit

### Requirement: Explicit isolated application home
A nonempty `CODEX_CONTAINER_STATE_DIR` SHALL select a dedicated writable home mounted at `/codex-home`, containing Codex state, caches and other home data, with `CODEX_HOME=/codex-home/.codex`. It SHALL be an absolute path without colon, CR or LF, checked before any engine query. The wrapper SHALL NOT mount the shared host `CODEX_HOME` in this mode. A simultaneous nonempty host `CODEX_HOME` SHALL fail with a conflict error before image operations or launch.

#### Scenario: Fresh isolated profile
- **WHEN** a dedicated state directory is selected and host `CODEX_HOME` is unset or empty
- **THEN** the container uses `HOME=/codex-home` and `CODEX_HOME=/codex-home/.codex`, with state persisted under the selected directory
- **AND** no shared host Codex state is mounted or imported

#### Scenario: Conflicting state controls
- **WHEN** dedicated state and a nonempty host `CODEX_HOME` are both selected
- **THEN** startup fails before image operations with instructions to select one state mode

#### Scenario: Relative state directory
- **WHEN** `CODEX_CONTAINER_STATE_DIR` is relative or contains a colon, CR or LF
- **THEN** the launch stops before any engine query and names the setting

#### Scenario: Isolated paths escape the home
- **WHEN** `.codex` or the CA mount parent inside the isolated home resolves outside it through a symlink
- **THEN** startup fails before image operations and nothing is created outside the home

#### Scenario: Qualification uses isolated state
- **WHEN** `--container-qualify` runs its phases
- **THEN** each phase uses its own disposable isolated state home and never reads or writes the user's `CODEX_HOME`

### Requirement: Isolated home privacy
The wrapper SHALL create the isolated home, its `.codex` directory and the CA mount parent privately, resolve the physical path, and require caller ownership, read/write/search access and no group/other permission bits on each. Every child SHALL stay inside the home. It SHALL NOT repair existing permissions recursively, and SHALL reject filesystems that do not enforce user-only modes.

#### Scenario: Unsafe isolated home
- **WHEN** the isolated home or its `.codex` has the wrong owner, lacks access or grants group/other access
- **THEN** startup fails with a path-specific error before image operations, without changing existing permissions

#### Scenario: Unsafe CA mount parent
- **WHEN** host CA trust is enabled and the CA mount parent in the isolated home grants group/other access
- **THEN** startup fails before image operations naming that path
