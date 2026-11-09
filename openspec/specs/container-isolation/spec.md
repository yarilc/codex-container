# container-isolation Specification

## Purpose

Protect the runtime image from session writes while retaining writable project files, persistent Codex state, and temporary storage.

## Requirements

### Requirement: Read-only image filesystem in all session modes

The wrapper SHALL launch Codex and shell sessions with the image root filesystem mounted read-only, independently of Podman access and `CODEX_YOLO`. Explicit workspace and state mounts and temporary filesystems SHALL be writable exceptions.

#### Scenario: Image files cannot be modified
- **WHEN** a session starts in either Codex or shell mode with either Podman access setting
- **THEN** the container root mount is read-only
- **AND** attempts to modify image files outside writable mounts fail because the filesystem is read-only

#### Scenario: YOLO retains filesystem protection
- **WHEN** the wrapper starts Codex with `CODEX_YOLO=1`
- **THEN** the root filesystem remains read-only

### Requirement: Preserve writable persistent mounts

The wrapper SHALL retain the existing writable workspace selection and the host `CODEX_HOME` bind mounted at `/codex-home/.codex`. Their contents SHALL persist across sessions, and workspace paths and working directory SHALL retain their existing semantics.

#### Scenario: Workspace and state persist
- **WHEN** a session writes files in the workspace and in `/codex-home/.codex` and exits
- **THEN** a later session with the same host directories can read those files

#### Scenario: Parent workspace remains writable
- **WHEN** a session starts with `--container-git-worktree`
- **THEN** the existing immediate-parent workspace bind remains read/write at its identical absolute path

### Requirement: Writable ephemeral runtime locations

The wrapper SHALL provide writable temporary storage in `/tmp`, `/var/tmp`, `/run`, and the non-persistent portion of `/codex-home` for the mapped runtime user. It SHALL retain persistent `CODEX_HOME` within that home and SHALL discard ephemeral session writes when the container is removed.

#### Scenario: Temporary and home writes succeed
- **WHEN** the mapped user creates files in the temporary locations and in `/codex-home` outside `.codex`
- **THEN** those writes succeed without changing the image filesystem
- **AND** those files are absent in a fresh session
- **AND** writes inside `.codex` remain persistent

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

### Requirement: Explicit temporary storage capacities

In Codex and shell sessions, the wrapper SHALL cap the `/tmp` and `/var/tmp` tmpfs mounts at 512 MiB each and `/run` at 32 MiB, independently of delegation and YOLO. All three SHALL remain writable with mode 1777, nosuid, and nodev. `/tmp` and `/var/tmp` SHALL retain exec; existing execution options for `/run` and `/codex-home` SHALL be preserved. These caps SHALL NOT change persistent bind mounts.

#### Scenario: Finite capacities in either session mode
- **WHEN** a Codex or shell session starts with any supported delegation and YOLO combination
- **THEN** `/tmp` and `/var/tmp` each have a 536870912-byte tmpfs capacity and `/run` has a 33554432-byte tmpfs capacity
- **AND** their existing access and protective mount options remain in effect

#### Scenario: Temporary executables remain usable
- **WHEN** the mapped user creates and runs an executable in `/tmp`, `/var/tmp`, or `/codex-home` outside persistent state
- **THEN** execution remains possible without modifying the read-only image filesystem

#### Scenario: Exhaust a bounded mount
- **WHEN** a write would exceed the available capacity of `/tmp`, `/var/tmp`, or `/run`
- **THEN** the write fails instead of expanding that mount beyond its configured capacity
- **AND** persistent workspace and state mounts retain their existing capacities and access

#### Scenario: Var tmp contents are ephemeral
- **WHEN** a session writes an executable and other files under `/var/tmp`, exits, and a new session starts
- **THEN** the previous files are absent and `/var/tmp` retains its 512 MiB capacity and executable writable policy

### Requirement: Document temporary storage boundaries

Help, README, and runtime guidance SHALL state the `/tmp`, `/var/tmp`, and `/run` capacities. The README SHALL explain that these are per-mount maxima, not reserved memory or an overall container memory limit, and that ephemeral home has no explicit capacity imposed by this policy.

#### Scenario: User plans temporary storage
- **WHEN** a user reads the storage guidance
- **THEN** they find all three mount capacities, retained executable temporary locations, and the distinction from a total memory limit

### Requirement: Every session drops capabilities and privilege gains
Every Codex and shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, with or without Podman delegation and independently of `CODEX_YOLO`. The wrapper SHALL NOT add a capability back or disable no-new-privileges to resolve an incompatibility; such a limitation SHALL be documented instead.

#### Scenario: Codex or shell session starts
- **WHEN** a Codex or shell session starts with either Podman access setting
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Codex, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Codex command sandbox works without capabilities
- **WHEN** Codex runs a command through its own Linux sandbox inside the session
- **THEN** the command executes without capabilities in the container and without disabling no-new-privileges
- **AND** if the sandbox cannot work, the wrapper adds no capability and the limitation and the required Codex sandbox configuration are recorded in the validation record

#### Scenario: Delegated Podman client works without capabilities
- **WHEN** a session with exact `CODEX_CONTAINER_PODMAN=1` runs `podman info` and creates a child container through the mounted socket
- **THEN** the client succeeds without capabilities in the session container
- **AND** the documentation states that the socket still grants host engine authority beyond these limits

### Requirement: Sessions have explicit resource budgets
Every Codex and shell container SHALL be created with a memory limit, a CPU limit and a process limit. The defaults SHALL be 4 GiB memory, 2 CPUs and 512 processes. `CODEX_CONTAINER_MEMORY_LIMIT`, `CODEX_CONTAINER_CPU_LIMIT` and `CODEX_CONTAINER_PIDS_LIMIT` SHALL override them. Only an unset variable SHALL select its default; no value SHALL disable a budget.

#### Scenario: Accepted formats
- **WHEN** the operator sets a budget variable
- **THEN** memory accepts a positive integer with unit `k`, `m` or `g`, CPU accepts a positive decimal with at most three fractional digits up to 1024, and the process limit accepts an integer from 1 to 4194304

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `CODEX_CONTAINER_MEMORY_LIMIT=8g`, `CODEX_CONTAINER_CPU_LIMIT=1.5` and `CODEX_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is set but empty or whitespace, zero, negative, `-1`, `max`, non-numeric, out of range, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created container and require its configured memory, CPU and process limits to equal the selected budgets. A mismatch or missing limit SHALL stop startup with an actionable diagnostic, without a retry using weaker limits. Runtime verification SHALL measure the effective cgroup v2 limits inside the session.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for memory, CPU or processes
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation

#### Scenario: Effective limits are measured
- **WHEN** the real-engine runtime checks run a session with default and overridden budgets
- **THEN** the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` match the selected budgets
- **AND** a process count beyond the process limit fails inside the session

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document the budget variables with defaults and accepted formats, the lifetime variable, the unsafe-workspace override with the refused directories, and that capabilities are dropped in every mode. They SHALL state that budgets and tmpfs sizes do not bound workspace or state storage growth. Help SHALL remain free of engine queries and state creation.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `CODEX_CONTAINER_MEMORY_LIMIT`, `CODEX_CONTAINER_CPU_LIMIT`, `CODEX_CONTAINER_PIDS_LIMIT`, `CODEX_CONTAINER_RUN_TIMEOUT` and `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** it states that capabilities are dropped and budgets do not limit persistent storage
- **AND** no engine query or state creation occurs

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
