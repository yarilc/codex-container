# Tasks

## 1. Copy the shared setup components from `sandbox-ref-2`

- [x] 1.1 Create branch `add-container-setup` from `main`. Unpack `setup/` and `tests/test_setup.py` and `tests/test_alignment.py` with `git -C ../claude-container archive sandbox-ref-2`. Verify with `diff -r` against the tag: no differences in `network/`, `setup/` or any shared test.
- [x] 1.2 Extend the `tests/test_reference_copy.py` manifest with the new files. Verify that it passes, and that it fails on an injected byte change in `setup/common.py`.

## 2. Wrapper entry points

- [x] 2.1 Add `--container-setup` to `codex-container.sh`. It must be used alone, needs an interactive terminal and host Python 3, and runs `exec python3 -I setup/setup.py`. Help keeps precedence. Replace the missing-mode message with the `setup required:` form that names the absolute wrapper path. Verify with new `test_wrapper.py` cases and the help text.
- [x] 2.2 Pass the attached client's stderr through `setup/diagnostics.py` over a FIFO in the private session directory, when the filter and host Python exist. Reap the filter after the client within a one-second drain. Verify with `test_wrapper.py` cases:
  - the restart line is reclassified and real errors pass through;
  - the existing signal, TTY, pipe and exit-status cases still pass.
- [x] 2.3 Run `bash tests/run-runtime.sh --setup` (shared `test_setup.py`) and `test_alignment.py` in the runner. Both must pass without edits to shared files. If a failure comes from shared code, stop and fix it in `claude-container` first.

## 3. Restricted sandbox override

- [x] 3.1 Verify in Codex 0.167.0 that `sandbox_mode = "danger-full-access"` is accepted with `--strict-config` and overrides a `config.toml` value. Verify that a later `--sandbox` wins. Record the results in `docs/validation.md`.
- [x] 3.2 In `offline` and `provider` Codex launches, add `-c 'sandbox_mode="danger-full-access"'` first among the protected overrides. Do not add it in shell or `unrestricted`. Verify with `test_wrapper.py` argument tests for each mode, YOLO and shell.
- [x] 3.3 Update `test_network_runtime.py`:
  - the synthetic Responses API test runs `codex exec` without `--sandbox` and the tool writes its sentinel;
  - the startup banner shows `danger-full-access`;
  - `test_codex_native_sandbox_fails_closed_under_the_guard` keeps covering an explicit inner sandbox.
  Verify with `bash tests/run-runtime.sh --network`.

## 4. Setup runtime acceptance

- [x] 4.1 Port `tests/test_setup_runtime.py` with Codex names (`CODEX_CONTAINER_IMAGE`, `localhost/codex-cli:latest`, `codex-container`), and add the `--setup-runtime` mode to `tests/run-runtime.sh`. Verify with `bash tests/run-runtime.sh --setup-runtime`:
  - offline, provider and unrestricted installations;
  - the managed launcher from another workspace;
  - qualification and the smoke check;
  - no credentials and no systemd changes.
- [x] 4.2 Run the setup interactively once on the WSL target with a disposable `HOME`, in provider mode with the account method, declining login. Confirm:
  - the residual exfiltration acknowledgement;
  - the maintenance review;
  - "authentication pending" with the `codex login --device-auth` next step.
  Record the transcript summary in `docs/validation.md`.

## 5. Documentation and parity

- [x] 5.1 Add `docs/setup.md`, adapted from Claude: guided installation, maintenance consent, managed launcher, rollback, device-code login and the API-key alternative. Update:
  - the README: first-run section, migration, restricted sandbox override, verification modes;
  - the wrapper help;
  - `AGENTS.md`: shared-file list with `setup/`, `test_setup.py` and `test_alignment.py`, and the test commands.
  Verify with markdownlint on the changed files and `git diff --check`.
- [x] 5.2 Add the five-wrapper parity table to `docs/network-contract.md` and update the port status. Update the Codex row of the table in `claude-container/docs/network-contract.md` (documentation only, in that repository's working tree). Verify that both rows match and the links resolve.
- [x] 5.3 Final verification:
  - `bash -n` and ShellCheck;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--network`, `--qualification` and the default mode;
  - `openspec validate add-container-setup --strict`;
  - `git diff --check`.
  Record the results in `docs/validation.md`, and update `todo.md` items C09, C10, C11 and C12 and the N21 setup acknowledgement.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main` here, and commit the parity-row edit in `claude-container`. The user pushes.
- The operator-run authenticated checks (device-code login, refresh, API key) remain pending for both profiles.
- Next Wave 3 port: OpenCode (`add-network-egress`).
