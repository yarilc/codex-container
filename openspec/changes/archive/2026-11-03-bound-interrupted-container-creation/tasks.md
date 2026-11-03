# Tasks

## 1. Bound creation interruption and recover ownership

- [x] 1.1 Extend the fake Podman in `tests/test_wrapper.py` with readiness/PID markers and permanent stalls before and after CID publication, TERM resistance, and CID publication on TERM; verify fixtures stay stalled without a release and failure teardown can terminate their process group.
- [x] 1.2 Replace unlimited interrupted creation waits in `codex-container.sh` with explicit pending-creation handling and fixed completion/cancellation/reaping phases (5s, 5s, 1s); retain PID tracking through reconciliation and avoid waiting on a live child. Verify permanent-stall regressions finish within a conservative 25s outer bound and the recorded client PID is gone in ordinary killable fixtures.
- [x] 1.3 Recover the complete private CID after cancellation, reject malformed or multiple-record identities, and remove only the verified full ID with the existing 5s plus 1s control bound. Verify post-publication stalls and CID-on-TERM are cleaned, while missing/invalid IDs produce unresolved diagnostics and no removal or application start.
- [x] 1.4 Add TERM/INT/HUP creation tests in Codex and shell modes, repeated mixed signals, and completion within the reconciliation window. Verify statuses 143/130/129 follow the first signal, later signals do not renew deadlines, and no interrupted invocation starts or retries an application.
- [x] 1.5 Exercise failed and stalled removal after CID recovery, plus bounded client-reaping failure handling; verify status preservation, full-ID/PID diagnostics as applicable, finite exit, and private bookkeeping cleanup. Re-run existing attached-session signal and cleanup tests to validate shared reaping behavior.
- [x] 1.6 Update README, wrapper help where applicable, and `AGENTS.md` runtime guidance with the creation phase budgets and unknown engine-outcome limitation; verify their stated limits match the delta scenarios and implemented constants.

## 2. Validate integration and record evidence

- [x] 2.1 Run `bash -n codex-container.sh`, `git diff --check`, `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`, `openspec validate bound-interrupted-container-creation --strict`, and `openspec validate --specs --strict`; verify all required checks pass, including existing exit-125, argument, stream, naming, and mount regressions.
- [x] 2.2 Run the opted-in real Podman lifecycle checks with disposable private state and a same-host rootless service, using `bash tests/run-runtime.sh` when native Linux storage is needed. Record passed checks and unavailable checks separately in `docs/validation.md`, explicitly identifying synthetic permanent-stall results and avoiding any claim of an actual engine-hang test.
- [x] 2.3 Reconcile `todo.md` with the verified implementation and record final commands/results and limitations in `docs/validation.md`; verify the outstanding item is closed only when its bounded termination, ownership, status, and diagnostic criteria are demonstrated.

## Workflow follow-up

- Synchronize the `container-session` delta into the main specification after implementation and verification.
- Archive the completed change through the archive workflow and validate the synchronized specifications.
