# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Document session behavior

The README and runtime guidance SHALL explain naming, collision handling, exit codes, terminal selection, signals, and cleanup. They SHALL describe interrupted-creation phase limits, first-signal status preservation, and unresolved creation without a verified ID. Help SHALL describe nonterminal support. Documentation SHALL distinguish transport from application terminal requirements and disclose residual-container risks after cancellation, unhandled termination, or engine loss.

#### Scenario: User discovers nonterminal usage
- **WHEN** a user reads help and the README
- **THEN** they find terminal selection behavior and an example using redirected input
- **AND** the README explains owned cleanup, interruption statuses, naming, and unrecoverable cleanup limitations

#### Scenario: User discovers interrupted creation limits
- **WHEN** a user reads the README or repository runtime guidance
- **THEN** they find the separate completion, client cancellation, reaping, and removal limits
- **AND** they learn that cancellation does not prove engine-side creation stopped and an unresolved outcome requires explicit engine inspection
