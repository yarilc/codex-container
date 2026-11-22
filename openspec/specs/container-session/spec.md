# container-session Specification

## Purpose

Provide reliable container sessions under concurrent starts, redirected input, application failures, and caller interruptions while restricting cleanup to the invocation's own container.

## Requirements

### Requirement: Allocate directory-based names from all containers

The wrapper SHALL derive the name prefix from the physical launch directory using its existing sanitization and fallback. It SHALL list running and stopped containers successfully before selecting the next index. Matching suffixes of one to nine decimal digits SHALL be interpreted in base ten; all other suffixes SHALL be ignored.

#### Scenario: Stopped containers and leading zeroes
- **WHEN** matching names include a stopped `project-08` and a running `project-2`
- **THEN** the first candidate is `project-9`

#### Scenario: Ignore invalid suffixes
- **WHEN** the listing contains unrelated prefixes, nonnumeric suffixes, or suffixes longer than nine digits
- **THEN** those names do not affect the initial index and do not cause arithmetic errors

#### Scenario: No matching names
- **WHEN** no supported numeric suffix matches the sanitized prefix
- **THEN** the first candidate uses index zero

#### Scenario: Listing fails
- **WHEN** container enumeration fails
- **THEN** the wrapper exits nonzero with an actionable error without creating or starting a session

### Requirement: Reserve session names atomically

The wrapper SHALL reserve each candidate atomically before starting the application. It SHALL attempt at most 20 candidates, increasing the index only for a confirmed name collision. Other creation or collision-verification errors SHALL stop startup with a diagnostic. Existing containers SHALL NOT be replaced or removed to obtain a name.

#### Scenario: Concurrent starts
- **WHEN** two invocations select the same available candidate and both can reach the engine
- **THEN** at most one reserves that candidate and the other can retry the next index
- **AND** each successful invocation starts only its own reserved container

#### Scenario: Exhaust collision retries
- **WHEN** all 20 creation attempts encounter confirmed name collisions
- **THEN** startup fails with an actionable exhaustion error and no existing container is removed

#### Scenario: Failure is not a collision
- **WHEN** creation fails and the engine confirms that the candidate name does not exist
- **THEN** the wrapper reports the creation failure without retrying another name

#### Scenario: Collision cannot be verified
- **WHEN** checking the candidate after a creation failure itself encounters an engine error
- **THEN** the wrapper fails without treating that error as a confirmed collision

### Requirement: Restrict cleanup to the owned container

After creation, the wrapper SHALL retain the identity of its container and attempt its removal on normal exit, startup failure, or handled interruption. Cleanup SHALL be safe to repeat and SHALL NOT target containers by a reusable name alone. Failure to clean up SHALL be reported without replacing the primary exit status.

#### Scenario: Unrelated container survives cleanup
- **WHEN** the invocation exits while other containers share its name prefix
- **THEN** only the container created by this invocation is eligible for removal

#### Scenario: Container already removed
- **WHEN** the owned container has already disappeared before cleanup
- **THEN** cleanup completes without changing the primary exit status or removing another container

#### Scenario: Interrupted creation completes
- **WHEN** TERM, INT, or HUP arrives during creation and the reachable engine completes that creation within the bounded reconciliation period
- **THEN** the wrapper retains the created identity and attempts bounded cleanup of that container without starting its application

#### Scenario: Cleanup fails
- **WHEN** the engine rejects removal of the owned container
- **THEN** the wrapper reports the cleanup failure and owned identity while preserving the primary exit status

### Requirement: Forward handled signals with bounded shutdown
For Codex and shell sessions, the wrapper SHALL handle TERM, INT and HUP by starting shutdown at once and forwarding the signal to its running container. Shutdown SHALL finish within one 20-second deadline shared by the container, proxy containers, transport endpoints and local clients. It SHALL allow at most five seconds of graceful exit before forced removal of the owned container. Each shutdown engine call SHALL be bounded within the deadline. Handled interruptions SHALL return 143, 130 and 129.

#### Scenario: Signal reaches the container
- **WHEN** the caller sends TERM, INT or HUP to the wrapper during attachment
- **THEN** the signal is forwarded once to the owned container and the wrapper returns the defined interruption status

#### Scenario: Application ignores the signal
- **WHEN** the owned application does not exit within five seconds after a handled interruption
- **THEN** the wrapper attempts forced removal and returns within the 20-second deadline

#### Scenario: Signal before a container exists
- **WHEN** a handled interruption occurs before successful reservation
- **THEN** the wrapper does not start an application or signal or remove any unrelated container

#### Scenario: Repeated signals do not extend shutdown
- **WHEN** further TERM, INT or HUP signals arrive after shutdown has started
- **THEN** they do not restart the deadline, and the first signal determines the exit status

### Requirement: Preserve session exit status

For an uninterrupted attached session, the wrapper SHALL return the application exit status, including 125. A session or attach failure SHALL NOT trigger name allocation retries or a second application execution. Cleanup SHALL preserve the status selected for the session or interruption.

#### Scenario: Application exits with 125
- **WHEN** the successfully started application exits with status 125
- **THEN** the wrapper returns 125, attempts owned cleanup, and does not create another container

#### Scenario: Attachment fails
- **WHEN** attachment or startup fails after successful reservation
- **THEN** the wrapper exits nonzero and attempts owned cleanup without creating a replacement session

### Requirement: Select terminal mode from caller streams

In Codex and shell modes the wrapper SHALL request a TTY if and only if both stdin and stdout are terminals. It SHALL forward stdin through attachment when either stream is redirected, preserve output and application arguments, and avoid requiring a terminal for commands that support nonterminal execution.

#### Scenario: Interactive terminal
- **WHEN** stdin and stdout are terminals
- **THEN** the session receives a TTY and interactive input remains available

#### Scenario: Redirected streams
- **WHEN** stdin is a pipe or file, stdout is redirected, or both are redirected
- **THEN** no TTY is requested and supplied stdin remains available to the application

#### Scenario: End of redirected input
- **WHEN** a nonterminal application reads redirected stdin to end of file
- **THEN** it observes that input and EOF without the wrapper substituting an empty input stream

### Requirement: Document session behavior
The README and runtime guidance SHALL explain naming, collisions, exit codes, terminal selection, signals and cleanup, including the shared shutdown deadline and unresolved creation. Help SHALL describe nonterminal support. Documentation SHALL distinguish transport from application terminal needs and disclose residual containers after cancellation, unhandled termination or engine loss. It SHALL also cover the provider default mode and qualification.

#### Scenario: User discovers nonterminal usage
- **WHEN** a user reads help and the README
- **THEN** they find terminal selection behavior and an example using redirected input
- **AND** the README explains owned cleanup, interruption statuses, naming, and unrecoverable cleanup limitations

#### Scenario: User discovers interrupted creation limits
- **WHEN** a user reads the README or repository runtime guidance
- **THEN** they find the shared 20-second shutdown deadline
- **AND** they learn that cancellation does not prove engine-side creation stopped and an unresolved outcome requires explicit engine inspection

#### Scenario: Existing user migrates to explicit modes
- **WHEN** an existing user reads the help or the README
- **THEN** they learn that an unset `CODEX_CONTAINER_NETWORK` selects provider, that `unrestricted` must be chosen explicitly, and that restricted modes need `--container-qualify` first

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
- **THEN** only exactly `1` enables delegation, independently of the YOLO value
- **AND** YOLO normalization does not change workspace mounts or the read-only image filesystem

### Requirement: Bound interrupted container creation
For Codex and shell modes, a TERM, INT or HUP during creation SHALL start shutdown at once, within the shared 20-second deadline. The wrapper SHALL cancel the creation client and recover the owned container from the validated creation record, the create output, then the ownership label. It SHALL remove only that container. The first signal SHALL select status 143, 130 or 129. The wrapper SHALL NOT start the application after interruption and SHALL report unresolved creation when no verified owned ID can be recovered.

#### Scenario: Creation never completes before publishing an ID
- **WHEN** a handled signal interrupts a creation client that never completes or publishes an owned ID
- **THEN** the wrapper cancels the client and returns the selected interruption status within the deadline, without starting an application or removing any unrelated container
- **AND** it reports that creation is unresolved when no owned container can be found by its label

#### Scenario: Creation stalls after publishing an owned ID
- **WHEN** a handled signal interrupts a creation client that has published a valid owned ID but never completes
- **THEN** the wrapper attempts bounded removal using only that full ID and returns the interruption status without starting the application

#### Scenario: ID appears during cancellation
- **WHEN** the creation client publishes its owned ID while being cancelled
- **THEN** the wrapper recovers that ID before discarding the private creation record and attempts bounded owned cleanup
- **AND** it preserves the interruption status even if the client exits unsuccessfully

#### Scenario: Repeated signals do not renew shutdown
- **WHEN** further TERM, INT or HUP signals arrive after an interruption during creation
- **THEN** the first interruption status remains selected and the deadline is not restarted

#### Scenario: Invalid identity cannot authorize removal
- **WHEN** interrupted creation leaves an empty, malformed, multi-record or NUL-containing creation record and no verified owned ID
- **THEN** the wrapper does not remove a container by its candidate name or adopt another container with that name
- **AND** it preserves the interruption status

#### Scenario: Cleanup fails or stalls after creation cancellation
- **WHEN** removal of the recovered owned container fails or never completes
- **THEN** the wrapper bounds the removal attempt, reports failure and the owned ID, and preserves the interruption status

#### Scenario: Client cannot be reaped within its limit
- **WHEN** a cancelled local creation client cannot be confirmed terminated within the shutdown deadline
- **THEN** the wrapper reports the client handling failure and does not wait indefinitely
- **AND** it attempts bounded cleanup of any verified owned ID and preserves the interruption status

### Requirement: Optional session lifetime limit
`CODEX_CONTAINER_RUN_TIMEOUT` SHALL set the native engine lifetime of the session container in whole seconds. When it is unset, empty or `0`, no lifetime limit SHALL apply. Any other value that is not a positive decimal integer of at most ten digits SHALL fail with status 1 before engine queries. The limit SHALL be independent of the wrapper's interruption and cleanup deadlines.

#### Scenario: Lifetime disabled by default
- **WHEN** `CODEX_CONTAINER_RUN_TIMEOUT` is unset
- **THEN** the session container is created without a lifetime limit

#### Scenario: Lifetime expires
- **WHEN** `CODEX_CONTAINER_RUN_TIMEOUT=60` is set and the application is still running after 60 seconds
- **THEN** the engine stops the session container
- **AND** the wrapper prints a stderr notice that the session lifetime limit was reached
- **AND** the wrapper exits with the engine client's status and removes only its owned container

#### Scenario: Session ends before the limit
- **WHEN** the application exits before the limit
- **THEN** the wrapper propagates the application exit status unchanged and prints no lifetime notice

#### Scenario: Invalid lifetime value
- **WHEN** `CODEX_CONTAINER_RUN_TIMEOUT` is negative, fractional or non-numeric
- **THEN** the wrapper exits with status 1 and names the variable before any engine query or state creation

### Requirement: Explicit network mode admission
Ordinary Codex and shell launches SHALL use the effective `CODEX_CONTAINER_NETWORK`, explicit or from the managed launcher. An unset or empty mode SHALL select `provider`. A provider launch without its protected installation or provider settings SHALL exit with status 1 and a `setup required:` message. The message SHALL name `--container-setup` and the explicit-mode alternative. The refusal SHALL come before engine queries, state creation or image operations. It SHALL NOT prompt, run setup or start an application. Help, setup and `--container-qualify` keep their own checks.

#### Scenario: Existing invocation without a mode
- **WHEN** a user runs `codex-container.sh` with no `CODEX_CONTAINER_NETWORK` and no provider settings, interactively or with redirected input
- **THEN** it exits with status 1 and the setup-required message before any engine call, without application output, state or runtime resources
- **AND** the message names `bash <wrapper> --container-setup` and states that an operator can set `CODEX_CONTAINER_NETWORK` explicitly

#### Scenario: Empty mode with provider settings
- **WHEN** `CODEX_CONTAINER_NETWORK` is empty and the provider settings select a protected installation
- **THEN** the launch runs in provider mode

#### Scenario: Help without a mode
- **WHEN** `--container-help` runs with no mode
- **THEN** help succeeds without engine calls or state side effects

#### Scenario: Options and other settings do not imply setup
- **WHEN** an unconfigured launch uses shell, build, worktree or YOLO, `CODEX_CONTAINER_MAINTENANCE=1`, or state, image, endpoint, policy or delegation settings
- **THEN** it receives the same setup-required refusal
- **AND** files in the current directory never admit the launch

### Requirement: Restricted launches require current local qualification
Before ordinary offline or provider execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs. The check SHALL use the mode the launcher resolved, including the provider default. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and help SHALL NOT require it.

#### Scenario: Changed environment or artifacts
- **WHEN** boot, engine version, backend or endpoint, effective security policy, guard or code, launcher core or agent part, runtime or proxy image identity, hardening, gate revision or selected mode, profile or policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests `--container-qualify`
- **AND** changing environment variables never suppresses that failure

#### Scenario: Default mode is qualified as provider
- **WHEN** `CODEX_CONTAINER_NETWORK` is unset and the provider settings are present
- **THEN** the launcher and every Python helper check the provider report

#### Scenario: Matching evidence
- **WHEN** a trusted complete report matches the effective restricted workflow and all per-launch checks pass
- **THEN** Codex starts with its existing argument, stdin, terminal and exit-status semantics
- **AND** a locally qualified combination without release acceptance is visibly identified as not release-measured

#### Scenario: Explicit qualification operation
- **WHEN** the operator runs `--container-qualify` without a current report
- **THEN** only the protected gate fixtures run through normal confinement and resource preparation
- **AND** no supplied application command or writable fixture can execute through the report-check exception

### Requirement: Consistent restricted prerequisite decisions
Restricted startup and qualification SHALL use the same protected platform eligibility rules and diagnostic categories. Malformed or unavailable engine or platform evidence SHALL fail closed. The rules SHALL keep launch endpoint verification and SHALL NOT reject SELinux or AppArmor merely for being enabled.

#### Scenario: Qualification and startup receive the same evidence
- **WHEN** qualification and direct restricted startup inspect equivalent host and engine evidence
- **THEN** they agree on eligibility and identify the same failed prerequisite

### Requirement: Qualification binds agent hardening settings
The qualification identity of a restricted installation SHALL include:
- the agent capability and no-new-privileges settings;
- the selected memory, CPU and process budgets;
- the set of agent and proxy budgets actually enforced, as determined by the controllers the engine delegates;
- the mechanism enforcing each agent and proxy process budget: cgroup controller, process rlimit, or none;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** an installation was qualified with default budgets and the operator launches with `CODEX_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and Codex does not start

#### Scenario: Matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

#### Scenario: Controller delegation changed after qualification
- **WHEN** an installation was qualified while `cpu` was not delegated and the engine later delegates `cpu`
- **THEN** the qualification check reports mismatched evidence and requires requalification

#### Scenario: Process budget mechanism changed after qualification
- **WHEN** an installation was qualified with the agent process budget on the process rlimit fallback and the engine later delegates `pids`
- **THEN** the qualification check reports mismatched evidence and requires requalification

### Requirement: Unenforced budgets are announced
Each launch SHALL print one notice per unenforced agent or proxy budget, naming the budget, its container and the reason: the missing cgroup controller, or a cgroup manager that applies no cgroup limits. A process budget enforced through the process rlimit fallback SHALL get one notice naming the budget, its container and the rlimit mechanism instead. Notices SHALL NOT ask for confirmation. When every budget is enforced by its cgroup controller, no notice SHALL be printed.

#### Scenario: CPU controller missing
- **WHEN** a session starts on an engine delegating only `memory` and `pids`
- **THEN** stderr shows a notice that the agent CPU budget is not enforced because the `cpu` controller is not delegated to the rootless engine
- **AND** the session starts without waiting for input

#### Scenario: All controllers delegated
- **WHEN** the engine delegates `cpu`, `memory` and `pids`
- **THEN** no budget notice is printed

#### Scenario: Engine with the cgroupfs manager
- **WHEN** a session starts on a rootless engine with the `cgroupfs` cgroup manager that reports `cpu`, `memory` and `pids`
- **THEN** stderr shows notices that the agent memory and CPU budgets are not enforced because the rootless engine uses the `cgroupfs` cgroup manager, which applies no cgroup limits
- **AND** the process budget notice names the process rlimit fallback, or the reason it was not applied

#### Scenario: Process budget on the rlimit fallback
- **WHEN** a session starts on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** stderr shows a notice that the agent process budget is enforced through the process rlimit because the `pids` controller is not delegated
- **AND** the notice states that the limit counts the session user's tasks, threads included
- **AND** no notice reports the agent process budget as unenforced

#### Scenario: Process rlimit fallback not applied
- **WHEN** a session starts without the `pids` controller on a host where per-container counting is not established
- **THEN** stderr shows a notice that the agent process budget is not enforced, naming the missing `pids` controller and why the rlimit fallback was not applied

### Requirement: Name collisions are confirmed by ownership
When container creation fails without returning an ID and a container with the candidate name exists, the wrapper SHALL treat it as another session's container only when its session ownership label differs from this session's token. A container carrying this session's label SHALL be reconciled and removed as this session's own, never skipped.

#### Scenario: Another session holds the name
- **WHEN** creation fails, no ID was returned, and the existing container with that name carries another session's label
- **THEN** the wrapper retries the next numeric name without touching that container

#### Scenario: The engine created this session's container
- **WHEN** creation fails without returning an ID, and the container with that name carries this session's label
- **THEN** the wrapper reports the original creation failure, does not retry, and removes that container during bounded cleanup

### Requirement: Interrupted creation is recovered by ownership label
When creation is interrupted or fails and no valid ID was published, cleanup SHALL look up containers carrying this session's ownership label, within the shutdown budget, and remove the one it confirms as owned. It SHALL report unresolved creation only when that lookup fails or finds no confirmed owned container.

#### Scenario: Engine created the container before the client was cancelled
- **WHEN** a handled signal interrupts creation, the client publishes no ID, and the engine has created this session's container
- **THEN** cleanup finds it by the session label, confirms the label, removes it, and the wrapper returns the interruption status

#### Scenario: Nothing was created
- **WHEN** creation is interrupted and no container carries this session's label
- **THEN** the wrapper removes nothing and returns the interruption status

#### Scenario: Lookup unavailable
- **WHEN** the label lookup fails or times out
- **THEN** the wrapper reports that creation is unresolved and that engine inspection is required, without removing any container

### Requirement: Extra variables forwarded by name
`CODEX_CONTAINER_ENV_VARS` SHALL list host variable names, separated by whitespace, to forward into the session by name, never by value. An invalid name SHALL stop the launch before any engine or state operation. Unset or empty variables SHALL NOT be forwarded. Reserved names SHALL be skipped with one notice each.

#### Scenario: Listed variable reaches the session
- **WHEN** `CODEX_CONTAINER_ENV_VARS="GH_TOKEN"` is set and `GH_TOKEN` has a value
- **THEN** the session receives `GH_TOKEN` by name and the value is absent from engine arguments

#### Scenario: Names reserved by mode
- **WHEN** the list names a variable the launcher or agent part sets, a proxy or CA setting in a restricted mode, or `OPENAI_API_KEY` in a provider session using the `openai-account` profile
- **THEN** that name is skipped with a notice and the session starts

#### Scenario: Invalid name
- **WHEN** the list contains a name such as `1BAD`
- **THEN** the launch stops before any engine query

### Requirement: Session environment is fixed by the launcher
Every Codex and shell session SHALL receive `TERM`, `COLORTERM`, `LANG` and `LC_ALL` when the host sets them, and SHALL set `USER` to the caller's name and `EDITOR` and `VISUAL` to `nano`. Unrestricted sessions SHALL also forward the host proxy variables in both cases. Restricted sessions SHALL NOT forward proxy variables. No session SHALL receive a credential except as the network-egress credential rules allow.

#### Scenario: Unrestricted environment
- **WHEN** an unrestricted session starts with `TERM`, `LANG` and `HTTPS_PROXY` set on the host
- **THEN** the session receives `TERM`, `LANG` and `HTTPS_PROXY`, `USER` with the caller's name, and `EDITOR=nano`

#### Scenario: Restricted environment
- **WHEN** an offline or provider session starts with `HTTPS_PROXY` set on the host
- **THEN** the session receives `TERM` when set, `USER` and `EDITOR=nano`, but not the host `HTTPS_PROXY`

### Requirement: Shell mode passes its arguments
`--container-shell` SHALL start `/bin/bash` with the remaining arguments in every network mode. It SHALL never add Codex arguments, the approval bypass or the protected `-c` overrides.

#### Scenario: Shell command
- **WHEN** `--container-shell -c "echo ok"` runs in offline, provider or unrestricted mode
- **THEN** Bash runs `-c` and `echo ok` as two arguments and prints `ok`

### Requirement: Session name and init process
Each create attempt SHALL set `CONTAINER_NAME` to the reserved container name and run with stdin from `/dev/null`. Unrestricted sessions SHALL run with `--init`. A failed create whose name holds this session's own container SHALL never count as a collision: that container SHALL be removed, or reported as unresolved.

#### Scenario: Session name inside the container
- **WHEN** an unrestricted session starts as `<prefix>-3`
- **THEN** it runs with `--init` and `CONTAINER_NAME=<prefix>-3`

#### Scenario: Own container behind a failed create
- **WHEN** create fails without publishing an ID and the engine reports this session's ownership label for the name
- **THEN** the wrapper returns the create status without retrying and removes that container

### Requirement: Read-only engine queries are bounded
Every read-only engine query (`info`, `version`, `ps`, image and container existence and inspection, the delegation socket query) SHALL be bounded by a timeout. A response with a carriage return or extra records SHALL be refused. `create`, `start`, `build` and `pull` SHALL NOT be bounded.

#### Scenario: Stalled engine query
- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container

### Requirement: First-user setup guidance
README, wrapper help and setup guidance SHALL name `--container-setup` as the first step for new users. They SHALL explain the managed launcher and the explicit operator alternative. They SHALL state that provider is the default mode, and that offline sessions cannot reach the OpenAI API.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads the help or the README
- **THEN** they find how to run setup and then use its managed launcher
- **AND** they learn that offline cannot reach the OpenAI API and that no unrestricted fallback is automatic

#### Scenario: Operator chooses a mode explicitly
- **WHEN** an operator reads the guidance
- **THEN** it explains that `CODEX_CONTAINER_NETWORK` selects offline, provider or unrestricted, that builds need `CODEX_CONTAINER_MAINTENANCE=1`, and that selecting a mode does not prove restricted readiness
