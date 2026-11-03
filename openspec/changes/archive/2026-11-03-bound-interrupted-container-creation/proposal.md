# Proposal

## Why

The remaining task in `todo.md` identifies an unbounded interruption path: `wait_for_create` resumes waiting after TERM, INT, or HUP even if the Podman client never completes. This prevents shutdown and owned cleanup despite the finite limits already used for attached sessions.

## What Changes

- Give interrupted creation a finite completion period, followed by bounded local-client cancellation and reaping.
- Recover the full owned container ID from the invocation's private CID file after cancellation, including IDs published during cancellation, and attempt bounded removal without starting the application.
- Preserve the first interruption status (143/130/129), prevent subsequent signals from extending shutdown, and report unresolved creation when no trustworthy ID is available.
- Add deterministic regressions for permanently stalled creation, CID publication races, repeated signals, and failed or stalled cleanup.
- Update README, runtime guidance, and validation evidence to describe the phase limits and residual-container limitations.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-session`: Extend interruption guarantees to pending creation, require safe identity reconciliation and unresolved-outcome diagnostics, and document bounded creation shutdown.

## Impact

Implementation affects `codex-container.sh`, synthetic lifecycle fixtures and tests in `tests/test_wrapper.py`, README, `AGENTS.md` runtime guidance, and `docs/validation.md`. Existing opted-in Podman checks provide real-engine lifecycle regression coverage. No new dependencies, privileges, mounts, or public options are required. `todo.md` is closed only after implementation and verification; this proposal changes planning artifacts only.
