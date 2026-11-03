# Design

## Context

See `proposal.md` for motivation and `specs/container-session/spec.md` for acceptance behavior. The wrapper tracks a background creation PID and a private `--cidfile`, but `wait_for_create` repeats an unlimited wait when a trap changes `signal_epoch`. The caller clears `client_pid` before reading the CID. EXIT cleanup only knows `container_id` and currently ends with an unconditional `wait` after KILL.

The synthetic creation fixture publishes the CID before its barrier; `test_signals_during_creation` releases that barrier after signalling. Existing bounded-control tests cover attachment rather than permanent creation stalls. The README explicitly assumes a responsive engine for reconciliation. Both referenced sibling wrappers are available: Antigravity uses bounded private-CID reconciliation; Claude additionally uses session labels and engine inspection.

## Goals / Non-Goals

**Goals:** Make interruption during creation enter a finite shutdown path, retain ownership evidence until reconciliation finishes, and keep the selected status independent of client and cleanup failures. Include a design because cancellation races affect both ownership safety and bounded termination.

**Non-Goals:** General startup timeouts, bounded preflight/build/listing or collision-query interruption, engine-wide recovery, session labels, cleanup by name, and recovery after SIGKILL. Normal uninterrupted creation remains allowed to take as long as needed.

## Decisions

### 1. Make pending creation explicit and freeze the first interruption

Track creation separately from attachment and retain the creation PID until it is confirmed reaped or explicitly reported unresolved. Record the first handled signal/status before transferring control to shutdown. A signal before PID assignment must still be honored immediately after assignment. Signals during shutdown cannot restart deadlines or replace the primary status; cleanup disables recursive signal handling.

Replace the unlimited interrupted `wait_for_create` loop with a transition into creation reconciliation. Keep normal wait status handling compatible with `set -Eeuo pipefail`. Merely adding a timeout to each repeated wait is rejected because repeated signals could renew the budget and a successful delayed fixture would still hide permanent stalls.

### 2. Use separate finite phases with no unconditional wait on a live child

On interruption, allow the pending creation client up to five seconds to finish. If still running, send TERM, allow at most five seconds, then send KILL and allow at most one further second to observe termination. Only call `wait` when Bash has confirmed that the child is no longer running; otherwise report the client PID and continue without an unlimited wait. Use Bash's child/job bookkeeping to avoid targeting a recycled PID. Apply the same safe reaping helper to the existing attached-client cleanup path where it is shared.

After reconciliation, removal retains `timeout --kill-after=1s 5s podman rm --force --ignore --time 0 <full-id>`. Interrupted creation therefore budgets at most 17 seconds across completion, cancellation/reaping, and removal phases, excluding ordinary scheduling overhead. Polling should use absolute phase deadlines and short sleeps. Tests use a conservative 25-second outer limit while asserting the individual control options and elapsed behavior. This follows the repository's phase-based shutdown contract without introducing a separate global watchdog or user configuration.

### 3. Reconcile the complete private CID after cancellation

Keep the private bookkeeping directory until client cancellation and identity recovery are complete. Read the entire CID record after the client finishes or its cancellation budget expires, allowing the conventional trailing newline but rejecting additional records or malformed IDs. Adopt only a full 64-character lowercase hexadecimal ID from this invocation's private CID file; that provenance is the ownership evidence. Keep a previously verified owned ID if one was already recorded.

This final read catches a CID published by a TERM handler or just before cancellation completes. A nonzero client exit cannot invalidate a trustworthy CID: still attempt removal. Do not inspect or remove the reusable candidate name to compensate for missing evidence. With no valid ID, emit an actionable unresolved-creation diagnostic and preserve the interruption status. Invalid CID diagnostics must not override that status.

Session labels and bounded engine discovery, as used by Claude, could recover identities absent from the CID file, but add queries and another verification protocol. The narrower Antigravity approach satisfies `todo.md`, which explicitly permits an unresolved result when ownership cannot be established.

### 4. Verify permanent stalls with deterministic publication barriers

Extend the existing fake Podman with modes that never complete: stall before CID publication, stall after publication, ignore TERM, and publish the CID when TERM arrives. Expose readiness and child PID markers so tests can synchronize signals and verify local-client termination rather than only wrapper exit. Keep a separate successful completion-during-reconciliation case.

Exercise TERM/INT/HUP in Codex and shell modes, repeated mixed signals, malformed/multiple CID records, and failed or stalled removal after a recovered CID. Assert no application start or retry, full-ID-only removal, the first status, diagnostics, private bookkeeping removal, and elapsed bounds. Never release a permanent-stall fixture to make the wrapper pass; process-group teardown is only test failure cleanup.

Run the existing real Podman lifecycle checks where available, using disposable state and no credentials. These establish regression behavior with an engine; injected synthetic stalls establish the cancellation branches and must be recorded separately. No actual engine outage or hang is required or claimed.

## Risks / Trade-offs

- Cancelling the local client does not cancel the engine request. Mitigation: attempt cleanup only with verified ownership and disclose that unknown or late engine outcomes can leave residual containers.
- An uninterruptible local process may survive KILL. Mitigation: stop waiting at the deadline and report the PID; do not claim successful reaping.
- CID publication races with cancellation. Mitigation: retain private state through cancellation and read the complete record afterward; missing or invalid evidence never authorizes removal.
- Timing tests can be noisy under load. Mitigation: use explicit readiness markers, production phase budgets, and a conservative outer deadline; do not replace hangs with finite successful delays.
- Shared reaping changes can regress attached sessions. Mitigation: retain existing signal, ignored-signal, cleanup-failure, exit-125, stdin, and TTY checks in the full wrapper suite.

## Migration Plan

Implement the lifecycle and regression changes through the apply workflow, then update README, help if needed, and `AGENTS.md` runtime guidance. Record actual checks and limitations in `docs/validation.md`; close the `todo.md` item only after verification. Synchronize the delta into the main spec and archive through their respective workflows after implementation is complete. No persisted-state migration or image dependency change is required. Rollback restores the prior wrapper and documentation; residual containers still require explicit engine inspection.
