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

For Codex and shell sessions, the wrapper SHALL handle TERM, INT, and HUP and forward the corresponding signal to its running container. It SHALL allow at most five seconds of graceful shutdown before attempting forced owned cleanup and SHALL bound cleanup and attached-client waits. Handled wrapper interruptions SHALL return 143, 130, and 129 respectively.

#### Scenario: Signal reaches the container
- **WHEN** the caller sends TERM, INT, or HUP to the wrapper during attachment
- **THEN** the corresponding signal is forwarded to the owned container and the wrapper returns the defined interruption status

#### Scenario: Application ignores the signal
- **WHEN** the owned application does not exit within five seconds after a handled interruption
- **THEN** the wrapper attempts forced removal and finishes its client handling without waiting indefinitely

#### Scenario: Signal before a container exists
- **WHEN** a handled interruption occurs before successful reservation
- **THEN** the wrapper does not start an application or signal or remove any unrelated container

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

The README and runtime guidance SHALL explain naming, collisions, exit codes, terminal selection, signals and cleanup, including interrupted-creation limits, first-signal status and unresolved creation. Help SHALL describe nonterminal support. Documentation SHALL distinguish transport from application terminal needs and disclose residual containers after cancellation, unhandled termination or engine loss. It SHALL also cover the required network mode, qualification and migration.

#### Scenario: User discovers nonterminal usage
- **WHEN** a user reads help and the README
- **THEN** they find terminal selection behavior and an example using redirected input
- **AND** the README explains owned cleanup, interruption statuses, naming, and unrecoverable cleanup limitations

#### Scenario: User discovers interrupted creation limits
- **WHEN** a user reads the README or repository runtime guidance
- **THEN** they find the separate completion, client cancellation, reaping, and removal limits
- **AND** they learn that cancellation does not prove engine-side creation stopped and an unresolved outcome requires explicit engine inspection

#### Scenario: Existing user migrates to explicit modes
- **WHEN** an existing user reads the help or the README
- **THEN** they learn that `CODEX_CONTAINER_NETWORK=unrestricted` keeps the previous networking, that builds need `CODEX_CONTAINER_MAINTENANCE=1`, and that restricted modes need `--container-qualify` first

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

For Codex and shell modes, interrupted creation SHALL allow at most five seconds for completion, then bounded client cancellation and reaping, followed by bounded owned cleanup. The first TERM/INT/HUP SHALL select status 143/130/129; later signals SHALL NOT extend deadlines or replace that status. The wrapper SHALL NOT start the application after interruption and SHALL report unresolved creation when no verified owned ID can be recovered.

#### Scenario: Creation never completes before publishing an ID
- **WHEN** a handled signal interrupts a creation client that never completes or publishes an owned ID
- **THEN** the wrapper allows at most five seconds for completion and then attempts client cancellation
- **AND** it allows at most five seconds after TERM before KILL and at most one further second to observe client termination
- **AND** it returns the selected interruption status without starting an application or removing any container
- **AND** it reports that creation is unresolved and engine inspection is required

#### Scenario: Creation stalls after publishing an owned ID
- **WHEN** a handled signal interrupts a creation client that has published a valid owned ID but never completes
- **THEN** the wrapper cancels the client within the defined limits and attempts removal using only that full ID
- **AND** removal has a five-second deadline plus a one-second forced termination allowance
- **AND** the wrapper returns the interruption status without starting the application

#### Scenario: ID appears during cancellation
- **WHEN** the creation client publishes its owned ID while being cancelled
- **THEN** the wrapper recovers that ID before discarding the private creation record and attempts bounded owned cleanup
- **AND** it preserves the interruption status even if the client exits unsuccessfully

#### Scenario: Repeated signals do not renew shutdown
- **WHEN** further TERM, INT, or HUP signals arrive after an interruption during creation
- **THEN** the first interruption status remains selected and the phase deadlines are not restarted

#### Scenario: Invalid identity cannot authorize removal
- **WHEN** interrupted creation leaves an empty or malformed private identity record and no verified owned ID
- **THEN** the wrapper does not remove a container by its candidate name or adopt another container with that name
- **AND** it reports unresolved creation while preserving the interruption status

#### Scenario: Cleanup fails or stalls after creation cancellation
- **WHEN** removal of the recovered owned container fails or never completes
- **THEN** the wrapper bounds the removal attempt, reports failure and the owned ID, and preserves the interruption status

#### Scenario: Client cannot be reaped within its limit
- **WHEN** a cancelled local creation client cannot be confirmed terminated within its cancellation and reaping limits
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
Ordinary Codex and shell launches SHALL require a nonempty effective `CODEX_CONTAINER_NETWORK`, explicit or from the managed launcher. An unset or empty mode SHALL exit with status 1 and a `setup required:` message naming `--container-setup` and the explicit-mode alternative, before runtime prerequisite checks, engine queries, state creation or image operations. It SHALL NOT prompt, run setup or start an application; help, setup and `--container-qualify` keep their own checks.

#### Scenario: Existing invocation without a mode
- **WHEN** a user runs `codex-container.sh` with no `CODEX_CONTAINER_NETWORK`, interactively or with redirected input
- **THEN** it exits with status 1 and the setup-required message before any engine call, without application output, state or runtime resources
- **AND** the message names `bash <wrapper> --container-setup` and states that an operator can set `CODEX_CONTAINER_NETWORK` explicitly

#### Scenario: Help without a mode
- **WHEN** `--container-help` runs with no mode
- **THEN** help succeeds without engine calls or state side effects

#### Scenario: Options and other settings do not imply setup
- **WHEN** an unconfigured launch uses shell, build, worktree or YOLO, `CODEX_CONTAINER_MAINTENANCE=1`, or state, image, endpoint, policy or delegation settings
- **THEN** it receives the same setup-required refusal before validating those settings
- **AND** files in the current directory never admit the launch

### Requirement: Restricted launches require current local qualification
Before ordinary offline or provider execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and help SHALL NOT require it.

#### Scenario: Changed environment or artifacts
- **WHEN** boot, engine version, backend or endpoint, effective security policy, guard or code, runtime or proxy image identity, hardening, gate revision or selected mode, profile or policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests `--container-qualify`
- **AND** changing environment variables never suppresses that failure

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
- the set of agent and proxy budgets actually enforced, as determined by the controllers the engine reports;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** an installation was qualified with default budgets and the operator launches with `CODEX_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and Codex does not start

#### Scenario: Matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

#### Scenario: Controller delegation changed after qualification
- **WHEN** an installation was qualified while `cpu` was not delegated and the engine later reports `cpu`
- **THEN** the qualification check reports mismatched evidence and requires requalification

### Requirement: First-user setup and migration guidance
README, wrapper help and setup guidance SHALL name `--container-setup` as the first step for new users, explain the managed launcher and the explicit operator alternative, state that offline sessions cannot reach the OpenAI API, and give the migration path for direct invocations from versions without network modes.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads the help or the README
- **THEN** they find how to run setup and then use its managed launcher
- **AND** they learn that offline cannot reach the OpenAI API and that no unrestricted fallback is automatic

#### Scenario: Operator migrates an existing direct invocation
- **WHEN** an operator reads the migration guidance
- **THEN** it explains that earlier versions needed no network mode, that `CODEX_CONTAINER_NETWORK=unrestricted` keeps the previous networking, and that builds need `CODEX_CONTAINER_MAINTENANCE=1`
- **AND** it does not imply that selecting a mode proves restricted readiness

### Requirement: Unenforced budgets are announced
Each launch SHALL print one notice per unenforced agent or proxy budget, naming the budget, its container and the missing cgroup controller, without asking for confirmation. When every budget is enforced, no notice SHALL be printed.

#### Scenario: CPU controller missing
- **WHEN** a session starts on an engine reporting only `memory` and `pids`
- **THEN** stderr shows a notice that the agent CPU budget is not enforced because the `cpu` controller is not delegated to the rootless engine
- **AND** the session starts without waiting for input

#### Scenario: All controllers delegated
- **WHEN** the engine reports `cpu`, `memory` and `pids`
- **THEN** no budget notice is printed
