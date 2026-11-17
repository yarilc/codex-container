## ADDED Requirements

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

## REMOVED Requirements

### Requirement: First-user setup and migration guidance
**Reason**: The project has no release, so the migration path from versions without network modes no longer applies, and a missing mode now selects provider.
**Migration**: Use "First-user setup guidance".

## MODIFIED Requirements

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
