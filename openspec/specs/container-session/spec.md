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
- **WHEN** TERM, INT, or HUP arrives during creation and the reachable engine completes that creation successfully
- **THEN** the wrapper retains the created identity and cleans up that container without starting its application

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

The README and runtime guidance SHALL explain naming across running and stopped containers, bounded collision handling, signal and cleanup behavior, exit codes, and terminal selection. Help SHALL describe nonterminal support. Documentation SHALL distinguish wrapper transport from application terminal requirements and disclose cleanup limitations after unhandled termination or engine loss.

#### Scenario: User discovers nonterminal usage
- **WHEN** a user reads help and the README
- **THEN** they find terminal selection behavior and an example using redirected input
- **AND** the README explains owned cleanup, interruption statuses, naming, and unrecoverable cleanup limitations
