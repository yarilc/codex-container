# Tasks

## 1. Adopt `sandbox-ref-23`

- [x] 1.1 Commit this change directory on `main` and create `prepare-adopt-sandbox-ref-23`. From `sandbox-container`, run `python3 -I tools/propagate.py ../codex-container sandbox-ref-21 sandbox-ref-23` (dry run), then `--apply`. Add `launcher` to `CLOSED_DIRECTORIES` in `tests/test_reference_copy.py`. Verify that:
  - the plan lists exactly the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-23`.
- [x] 1.2 Fix the parity table in `docs/network-contract.md` by hand (design decision 7). Verify that:
  - the reference and Claude rows equal those in `sandbox-container` and `claude-container`;
  - the Antigravity, OpenCode and Pi rows equal their own repositories'.

## 2. Launcher on the shared core

- [ ] 2.1 Save the current `tests/test_wrapper.py` and `codex-container.sh` outside the repository as the old-test baseline. Write `agent/launcher.sh` (design decision 2) and replace `codex-container.sh` with the reference entry script. Verify that:
  - `python3 -m unittest tests.test_alignment tests.test_launcher` passes in the disposable test container;
  - `bash codex-container.sh --container-help` prints the provider disclosure with the `openai-account` and `openai-api` hosts and the `CODEX_YOLO` entry;
  - `diff <(sed s/sandbox-container/codex-container/g ../sandbox-container/sandbox-container.sh) codex-container.sh` is empty.
- [ ] 2.2 Run the saved `tests/test_wrapper.py` against the new entry script and core in the disposable test container. Adapt only its harness (design decision 4). Classify every failing case as (a) visible change, (b) lost behavior or (c) Codex-only behavior, and resolve the 72 "to verify at adoption" cases by name. Record the table in a scratch note for task 4.2. Verify that every failing case has exactly one outcome.
- [ ] 2.3 If task 2.2 found any (b), pause this change. Fix each behavior with a shared case in `sandbox-container` through its own reference change and tag, then rerun tasks 1.1 to 2.2 against the new tag. Update this change's artifacts to name that tag. Verify that a rerun of task 2.2 finds no (b). If task 2.2 found none, mark this task done with the note "no lost behavior".

## 3. Codex tests and documentation

- [ ] 3.1 Rewrite `tests/test_wrapper.py` with the shared `tests/fake_podman.py` and the real agent part (design decision 5). It covers:
  - the three hook cases;
  - the protected arguments in each mode;
  - `OPENAI_API_KEY` with each policy profile and mode, including a `CODEX_CONTAINER_ENV_VARS` attempt under `openai-account`;
  - the help;
  - every outcome (c) from task 2.2.

  Verify that `python3 -m unittest tests.test_wrapper` passes in the disposable test container.
- [ ] 3.2 Update the wrapper-owned runtime tests (design decision 6): `tests/run-runtime.sh`, `tests/test_runtime.py`, `tests/test_network_runtime.py`, `tests/test_setup_runtime.py` and `tests/test_setup_wrapper.py`. Verify that `python3 -m unittest tests.test_setup_wrapper` passes in the disposable test container and that `bash -n tests/run-runtime.sh` succeeds.
- [ ] 3.3 Update the README, `docs/setup.md`, `docs/network-contract.md` and `AGENTS.md` (design decision 7). Cover:
  - the provider default, without the migration history;
  - temporary storage, `noexec` and the tmpfs home;
  - signals and the 20 s deadline;
  - `CODEX_CONTAINER_ENV_VARS` and `CODEX_CONTAINER_READONLY_STATE`;
  - credentials per policy profile;
  - build-only and stale images;
  - the launcher core.

  Verify that `grep -rn "keeps the previous networking\|retain exec\|five seconds for completion\|first-signal" --exclude-dir=openspec --exclude=validation.md .` finds nothing stale.

## 4. Integration

- [ ] 4.1 Rebuild the Codex test image with `--container-build`. Run the temporary-storage check of design decision 3 in shell sessions with shared, isolated and read-only state. If Codex needs executable temporary storage, pause and ask the user before changing the profile, the specs or the runtime test. Then run:
  - the unit discovery in the disposable test container;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`, and the default mode;
  - `git diff --check`.

  Verify that all pass.
- [ ] 4.2 Add the `sandbox-ref-23` adoption section to `docs/validation.md`, starting from the tool's template. It holds every result, the temporary-storage evidence and the old-test classification table from task 2.2. Commit with the tool's message and merge into `main`. Verify that `tests/test_reference_copy.py` passes on `main` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.

## Workflow follow-up

- The operator pushes `main` and runs `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host, then checks a Codex session in provider mode.
- Archive this change with spec sync. This creates `openspec/specs/shared-launcher/spec.md` in this repository.
- Refresh the Codex row of the parity table in `sandbox-container` and `claude-container` to `sandbox-ref-23`.
- Antigravity and Pi adopt `sandbox-ref-23` in their own changes, and OpenCode after them.
