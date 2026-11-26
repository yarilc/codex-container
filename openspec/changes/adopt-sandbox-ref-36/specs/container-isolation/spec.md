# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Read-only image filesystem in all session modes
The wrapper SHALL launch Codex and shell sessions with the image root filesystem mounted read-only, independently of the session container engine and `CODEX_YOLO`. Explicit workspace and state mounts and temporary filesystems SHALL be writable exceptions.

#### Scenario: Image files cannot be modified
- **WHEN** a session starts in either Codex or shell mode, with or without a session container engine
- **THEN** the container root mount is read-only
- **AND** attempts to modify image files outside writable mounts fail because the filesystem is read-only

#### Scenario: YOLO retains filesystem protection
- **WHEN** the wrapper starts Codex with `CODEX_YOLO=1`
- **THEN** the root filesystem remains read-only

### Requirement: Engine default secrets mount is masked
Every Codex and shell container SHALL be created with an empty read-only tmpfs at `/run/secrets`, in every network mode and with or without a session container engine. An engine default mount there, such as RHEL subscription secrets from `mounts.conf`, SHALL then be neither visible nor writable. No host configuration change SHALL be required.

#### Scenario: Host with a default secrets mount
- **WHEN** the engine's `mounts.conf` maps `/usr/share/rhel/secrets` to `/run/secrets`
- **THEN** the session has exactly one mount at `/run/secrets`, an empty tmpfs mounted read-only
- **AND** no host subscription file is readable inside the session

#### Scenario: Host without a default secrets mount
- **WHEN** the engine adds no mount at `/run/secrets`
- **THEN** the session still has the empty read-only tmpfs there and behaves as before

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

## REMOVED Requirements

### Requirement: Every session drops capabilities and privilege gains
**Reason**: Its delegated-client scenario no longer applies: host Podman delegation is removed.
**Migration**: Restated without delegation as "Sessions drop all capabilities and privilege gains"; the session's engine client is covered there.
