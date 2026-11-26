# container-isolation Specification

## Purpose

Protect the runtime image from session writes while retaining writable project files, persistent Codex state, and temporary storage.

## Requirements

### Requirement: Read-only image filesystem in all session modes
The wrapper SHALL launch Codex and shell sessions with the image root filesystem mounted read-only, independently of the session container engine and `CODEX_YOLO`. Explicit workspace and state mounts and temporary filesystems SHALL be writable exceptions.

#### Scenario: Image files cannot be modified
- **WHEN** a session starts in either Codex or shell mode, with or without a session container engine
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

### Requirement: Document temporary storage boundaries
Help, README and runtime guidance SHALL state the `/tmp`, `/var/tmp`, `/run` and ephemeral home capacities and that all four are `noexec`. The README SHALL explain that these are per-mount maxima, not reserved memory or an overall container memory limit.

#### Scenario: User plans temporary storage
- **WHEN** a user reads the storage guidance
- **THEN** they find all four mount capacities, the `noexec` policy, and the distinction from a total memory limit

### Requirement: Sessions have explicit resource budgets
Every Codex and shell container SHALL be created with a memory limit, a CPU limit and a process limit for each budget whose cgroup v2 controller (`memory`, `cpu`, `pids`) the verified rootless engine delegates. The defaults SHALL be 4 GiB memory, 2 CPUs and 512 processes. `CODEX_CONTAINER_MEMORY_LIMIT`, `CODEX_CONTAINER_CPU_LIMIT` and `CODEX_CONTAINER_PIDS_LIMIT` SHALL override them. Only an unset variable SHALL select its default; no value SHALL disable a budget, and only a missing controller SHALL leave it unenforced.

#### Scenario: Accepted formats
- **WHEN** the operator sets a budget variable
- **THEN** memory accepts a positive integer with unit `k`, `m` or `g`, CPU accepts a positive decimal with at most three fractional digits up to 1024, and the process limit accepts an integer from 1 to 4194304

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set on an engine delegating the `cpu`, `memory` and `pids` controllers
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `CODEX_CONTAINER_MEMORY_LIMIT=8g`, `CODEX_CONTAINER_CPU_LIMIT=1.5` and `CODEX_CONTAINER_PIDS_LIMIT=1024` on an engine delegating all three controllers
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is set but empty or whitespace, zero, negative, `-1`, `max`, non-numeric, out of range, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

#### Scenario: Controller not delegated
- **WHEN** the verified engine does not delegate the `cpu` controller
- **THEN** the container is created without a CPU limit, while the memory and process limits are still applied when their controllers are delegated
- **AND** the session continues and prints a notice naming the unenforced CPU budget and why it is unenforced

#### Scenario: Process controller not delegated
- **WHEN** the verified engine does not delegate the `pids` controller
- **THEN** the container is created with an explicitly unlimited cgroup process setting, so no engine default requests the missing controller
- **AND** the process budget follows the process rlimit fallback

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created container and require each cgroup-enforced budget to equal its selected value and each budget whose controller is not delegated to have no cgroup limit. A mismatch or missing enforced limit SHALL stop startup with an actionable diagnostic, without a retry using weaker limits. Runtime verification SHALL measure the effective cgroup v2 limits inside the session in the same way.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for a budget whose controller the engine delegates
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation and the controllers the engine reported

#### Scenario: Unenforced budget unexpectedly present
- **WHEN** the created container reports a cgroup limit for a budget whose controller the engine does not delegate
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts

#### Scenario: Effective limits are measured
- **WHEN** the real-engine runtime checks run a session with default and overridden budgets
- **THEN** the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` match the selected budgets for every delegated controller, and are absent or unlimited for the others
- **AND** on the process rlimit fallback, the session's soft and hard process rlimit equal the selected process budget
- **AND** a process count beyond the process limit fails inside the session, unless the process budget is unenforced

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document the budget variables with defaults and accepted formats, the lifetime variable, the unsafe-workspace override with the refused directories, and that capabilities are dropped in every mode. They SHALL document the process rlimit fallback, its per-session scope, the condition under which it applies, and that memory and CPU have no fallback. They SHALL state that budgets and tmpfs sizes do not bound workspace or state storage growth. Help SHALL remain free of engine queries and state creation.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `CODEX_CONTAINER_MEMORY_LIMIT`, `CODEX_CONTAINER_CPU_LIMIT`, `CODEX_CONTAINER_PIDS_LIMIT`, `CODEX_CONTAINER_RUN_TIMEOUT` and `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** it states that capabilities are dropped and budgets do not limit persistent storage
- **AND** no engine query or state creation occurs

#### Scenario: Operator reads about the process rlimit fallback
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that, without the `pids` controller, the process budget is enforced through the process rlimit per session when the host counts it per container
- **AND** it states that the usable process count is slightly below the budget because of container startup tasks

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

### Requirement: Engine default secrets mount is masked
Every Codex and shell container SHALL be created with an empty read-only tmpfs at `/run/secrets`, in every network mode and with or without a session container engine. An engine default mount there, such as RHEL subscription secrets from `mounts.conf`, SHALL then be neither visible nor writable. No host configuration change SHALL be required.

#### Scenario: Host with a default secrets mount
- **WHEN** the engine's `mounts.conf` maps `/usr/share/rhel/secrets` to `/run/secrets`
- **THEN** the session has exactly one mount at `/run/secrets`, an empty tmpfs mounted read-only
- **AND** no host subscription file is readable inside the session

#### Scenario: Host without a default secrets mount
- **WHEN** the engine adds no mount at `/run/secrets`
- **THEN** the session still has the empty read-only tmpfs there and behaves as before

### Requirement: Engine-provided device mounts allow pseudo-terminals
Every Codex and shell container SHALL keep automatic read-only tmpfs provisioning enabled and SHALL NOT mount its own `/dev` or `devpts`, so that the engine provides `/dev` and a `devpts` that allows pseudo-terminals. It SHALL mask `/dev/shm` with an empty read-only tmpfs. Automatic provisioning SHALL add no writable path beyond the explicit temporary mounts and the engine's `/dev`.

#### Scenario: Terminal attaches on an engine that mounts /dev read-only
- **WHEN** an interactive session starts with a terminal on Podman 5 with crun 1.27
- **THEN** the terminal attaches and Codex starts without any host configuration change
- **AND** `/dev/pts` is present and `/dev/shm` is read-only and empty

#### Scenario: Pseudo-terminals are available to tools
- **WHEN** a process inside the session opens a pseudo-terminal, as an interactive tool run by Codex or in the shell does
- **THEN** the allocation succeeds through `/dev/ptmx` and returns a terminal under `/dev/pts`

#### Scenario: Device masks stay empty and read-only
- **WHEN** a process inside the session lists or writes `/dev/shm` or `/run/secrets`
- **THEN** both are empty and the write fails

#### Scenario: Temporary mounts keep their Codex policy
- **WHEN** a session starts
- **THEN** `/tmp` and `/var/tmp` keep their 512 MiB executable policy and `/run` its 32 MiB capacity
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic provisioning

### Requirement: Isolated state does not overlap the workspace
The wrapper SHALL refuse an isolated state directory that is the workspace mount, contains it, or lies inside it, comparing resolved physical paths. The check SHALL run before image or engine operations, on direct and managed launches, and in worktree mode SHALL use the parent directory that is mounted.

#### Scenario: State directory inside the workspace
- **WHEN** `CODEX_CONTAINER_STATE_DIR` names the workspace or a directory below it
- **THEN** startup fails before engine operations, naming the state directory

#### Scenario: State directory containing the workspace
- **WHEN** the workspace lies below the selected state directory
- **THEN** startup fails with the same error

#### Scenario: Symlinked state directory
- **WHEN** the selected state path is a symlink that resolves inside the workspace
- **THEN** startup fails with the same error

### Requirement: Read-only state
`CODEX_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the Codex configuration directory read-only below the ephemeral home. The directory is taken from shared state or from the isolated home, and SHALL already exist. The launcher SHALL NOT create it, SHALL NOT check its owner or privacy, and SHALL NOT pass it to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `CODEX_CONTAINER_READONLY_STATE=1` is set and `~/.codex` exists
- **THEN** the session sees `/codex-home/.codex` read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and the configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory

### Requirement: Bounded noexec temporary storage
In Codex and shell sessions, the wrapper SHALL cap the `/tmp` and `/var/tmp` tmpfs mounts at 512 MiB each, `/run` at 32 MiB and the ephemeral home at 512 MiB, independently of YOLO and of the session container engine. All four SHALL be writable with `nosuid`, `nodev` and `noexec`, and `/tmp`, `/var/tmp` and the ephemeral home SHALL have mode 1777. The Codex profile SHALL NOT declare executable temporary storage (`native.exec_tmp`). These caps SHALL NOT change persistent bind mounts.

#### Scenario: Finite capacities in either session mode
- **WHEN** a Codex or shell session starts with either YOLO setting, with or without a session container engine
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

### Requirement: Only the systemd cgroup manager delegates controllers
A reported cgroup v2 controller SHALL count as delegated only when the verified rootless engine also reports the `systemd` cgroup manager. With `cgroupfs` or any other manager, no controller SHALL count as delegated, whatever the engine reports. An unverifiable cgroup manager response SHALL stop startup before image operations.

#### Scenario: cgroupfs engine reporting every controller
- **WHEN** a session starts on a rootless engine with the `cgroupfs` manager that reports `cpu`, `memory` and `pids`
- **THEN** the container is created without memory, CPU or cgroup process limits
- **AND** the session prints notices that the memory and CPU budgets are not enforced, naming the `cgroupfs` cgroup manager
- **AND** the process budget follows the process rlimit fallback

#### Scenario: systemd engine
- **WHEN** a session starts on a rootless engine with the `systemd` manager that reports `cpu`, `memory` and `pids`
- **THEN** the memory, CPU and cgroup process limits are applied as before

#### Scenario: Unverifiable cgroup manager
- **WHEN** the engine's cgroup manager response is empty, malformed or has more than one record
- **THEN** the wrapper exits non-zero before image operations or container creation

### Requirement: Process budget falls back to the process rlimit
When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, the agent container's first process SHALL set its soft and hard process rlimit to the selected process budget before the container's program runs. The engine SHALL apply no process rlimit for the budget: one applied at creation counts every container of the user. Otherwise the process budget SHALL stay unenforced. Memory and CPU SHALL have no fallback.

#### Scenario: Process controller missing on a per-container host
- **WHEN** a session starts with the default budgets on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the container's first process sets a soft and hard process rlimit of 512 before the application, or the guard in restricted modes, runs
- **AND** the container is created without a cgroup process limit and without a process rlimit requested from the engine
- **AND** the memory and CPU limits are applied as before

#### Scenario: Process controller delegated
- **WHEN** the engine delegates the `pids` controller
- **THEN** the process budget is enforced only by the cgroup process limit
- **AND** the wrapper sets no process rlimit

#### Scenario: Per-container counting not established
- **WHEN** the engine does not delegate `pids` and the host is not known to count the process rlimit per container
- **THEN** the wrapper requests neither a cgroup process limit nor a process rlimit for the container
- **AND** the session continues with a notice that names the unenforced process budget and why the fallback was not applied

#### Scenario: Memory controller missing
- **WHEN** the engine does not delegate the `memory` controller
- **THEN** the memory budget stays unenforced and no substitute memory limit is set

#### Scenario: The session cannot raise its process rlimit
- **WHEN** a process in a session on the fallback tries to raise its soft or hard process rlimit above the selected budget
- **THEN** the attempt fails, because the session has no capabilities and no-new-privileges is set

#### Scenario: Concurrent sessions have independent limits
- **WHEN** two sessions on the fallback run at the same time and the first holds processes up to its limit
- **THEN** the second session can still create processes up to its own limit

#### Scenario: Other containers do not consume the session's budget
- **WHEN** other containers of the same user, such as proxies, engines or their nested containers, together hold more processes than the session's budget
- **THEN** the session starts, and can create processes up to its own budget

#### Scenario: The limit cannot be set
- **WHEN** the container's first process cannot set the process rlimit to the selected budget
- **THEN** the container stops before the application or the guard runs, and the launch exits non-zero

### Requirement: Process rlimit fallback is verified
When the process budget uses the rlimit fallback, each launch SHALL require the created agent container to start with the step that sets the selected budget, and to carry no process rlimit requested by the wrapper. Setup smoke and restricted qualification SHALL measure the effective limit inside the agent container. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine drops the process rlimit
- **WHEN** the created container does not start with the step that sets the selected budget, for example because the engine dropped or replaced its entry command, or the step sets another value, or the container carries a process rlimit requested by the wrapper
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names the process rlimit fallback

#### Scenario: Effective rlimit is measured
- **WHEN** setup smoke or the restricted qualification probe runs inside an agent container on the fallback
- **THEN** it reads the effective soft and hard process rlimit and requires both to equal the selected budget
- **AND** it requires the cgroup process interface to be absent or unlimited

### Requirement: Sessions drop all capabilities and privilege gains
Every Codex and shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in all network modes, independently of `CODEX_YOLO`, and when the session has a container engine. The wrapper SHALL NOT add a capability back or disable no-new-privileges to resolve an incompatibility; such a limitation SHALL be documented instead.

#### Scenario: Codex or shell session starts
- **WHEN** a Codex or shell session starts, with or without a session container engine
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Codex, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Codex command sandbox works without capabilities
- **WHEN** Codex runs a command through its own Linux sandbox inside the session
- **THEN** the command executes without capabilities in the container and without disabling no-new-privileges
- **AND** if the sandbox cannot work, the wrapper adds no capability and the limitation and the required Codex sandbox configuration are recorded in the validation record

#### Scenario: Engine client works without capabilities
- **WHEN** a session with a container engine runs `podman info` and creates a child container through its `CONTAINER_HOST`
- **THEN** the client succeeds without capabilities in the session container
- **AND** the documentation states the engine container's own hardening exceptions

### Requirement: Sessions receive no Podman socket
No Podman API socket SHALL be mounted into a Codex or shell session, in any network mode and with any state, YOLO or worktree setting. A session's Podman command SHALL reach only the session's own container engine, and only when the session has one.

#### Scenario: Session without library images
- **WHEN** a session starts while the toolchain library holds no image
- **THEN** `/run/podman/podman.sock` is absent and `CONTAINER_HOST` and `DOCKER_HOST` are unset

#### Scenario: Session with library images
- **WHEN** a session starts while the toolchain library holds an image
- **THEN** `CONTAINER_HOST` names the session's engine at `tcp://127.0.0.1:2375`, and no host Podman socket is mounted
- **AND** a host path outside the session's mounts stays inaccessible, also through containers started by the engine
