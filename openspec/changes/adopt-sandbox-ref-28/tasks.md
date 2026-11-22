# Tasks

## 1. Adopt `sandbox-ref-28`

- [x] 1.1 Commit this change directory on `main`. Then, from `sandbox-container`, run `python3 -I tools/propagate.py ../codex-container sandbox-ref-25 sandbox-ref-28` (dry run), then the same command with `--apply`. Verify:
  - the plan lists the files in design "Context";
  - the checklist includes `--guard`;
  - the tool switched to `adopt-sandbox-ref-28`.
- [x] 1.2 Restore the Antigravity, OpenCode and Pi rows of `docs/network-contract.md` from `main` (design decision 5). Verify:
  - those three rows equal the ones on `main`;
  - the reference and Claude rows equal the ones in `sandbox-container`.
- [x] 1.3 Copy `sandbox-container.ps1` to `codex-container.ps1` byte for byte, and copy `.gitattributes`. Commit both, then rewrite the working files with LF (design decision 2). Verify:
  - `git status` is clean after the renormalization;
  - with host Python next to the `sandbox-container` checkout, and the sibling check not skipped, `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes, including the entry, ASCII and line-ending tests.
- [x] 1.4 Add the reference header to `agent/launcher.sh` (design decision 3). Verify, from `sandbox-container`:
  - `bash tools/shellcheck.sh ../codex-container` reports no finding;
  - `bash tools/powershell.sh ../codex-container` passes the shim cases with no finding.

## 2. Codex's tests and documentation

- [x] 2.1 Adapt Codex's own tests (design decision 4):
  - copy Claude's `tests/test_setup_wrapper.py` byte for byte;
  - in `tests/test_runtime.py`, add `engine_budgets()`, make the budget assertions follow it, and change the process probe to a budget of 128 with 200 children, skipped when no mechanism applies.

  Verify: `bash tests/run-runtime.sh --wrapper` passes, and the default `bash tests/run-runtime.sh` passes `test_effective_hardening_and_budgets` and `test_tools_and_codex_sandbox_without_capabilities`.
- [x] 2.2 Run the unit discovery in the disposable test container, then `bash tests/run-runtime.sh` in each of these modes:
  - `--shared`, `--setup` and `--setup-runtime`;
  - `--qualification`, `--guard` and `--network`;
  - no mode.

  Use matching `setup-*` images and the guard toolchain as design decision 7 says, and record which. Fix in Codex's own tests any failure that a shared behavior change causes. Verify: every mode passes, apart from failures already recorded for this runner. A failure in shared code pauses the change.
- [x] 2.3 Adapt the documentation (design decision 6):
  - `README.md`:
    - the `## Windows with Podman machine` section, with host CA trust on Windows and the install as a command;
    - the Windows limits, including Bitdefender;
    - the cgroup managers, the rlimit fallback and the guard as init, in `### Session hardening, budgets and lifetime`;
    - the Windows sensitive folders;
  - `docs/setup.md`:
    - the Windows setup and the authentication steps from Windows;
    - setup without a launch service;
    - the carriage-return check;
    - candidate tags;
    - the service endpoint for restricted modes;
    - the budget plan;
  - `AGENTS.md`: `codex-container.ps1` and the Windows files.

  Verify:
  - the README names `codex-container.ps1`, `$env:OPENAI_API_KEY`, `codex-container.ps1 login --device-auth` and `podman machine set --import-native-ca`;
  - no `SANDBOX_CONTAINER_` or `CLAUDE_` name, and no reference-only or Claude-only statement, appears in the new text;
  - `git diff --check` passes.

## 3. Validation on Windows

- [x] 3.1 Prepare the operator bundle: snapshots of `codex-container` and `sandbox-container`, and a README with the steps of design decision 8. Verify:
  - the README lists each step, the summary copies and the data to send back;
  - the checksums match.
- [x] 3.2 Have the operator run design decision 8. Verify that `docs/validation.md` records:
  - the setup with the declined login and its Windows next step;
  - the device-code login;
  - the Codex session and Ctrl+C;
  - Codex's own sandbox in an unrestricted launch;
  - `windows-validate` on both editions, once with `-Install -StopMachine`;
  - the API key check, or that no key is available.

  No case may fail. If one does, the change pauses for a decision. For step 4, the decision is between a documented limit in the README's Windows limits and a fix.

## 4. Record, merge and parity

- [ ] 4.1 Add the `sandbox-ref-28` adoption section to `docs/validation.md`, from the tool's template, with every result of tasks 2.1, 2.2 and 3.2. Set Codex's parity row to "Adopted `sandbox-ref-28`". Commit with the tool's message and merge into `main`. Verify: `tests/test_reference_copy.py` passes on `main`.
- [ ] 4.2 Copy Codex's parity row into `sandbox-container`, `claude-container`, `antigravity-container`, `opencode-container` and `pi-container`, with one commit on `main` in each. Verify: the reference, Claude and Codex rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` in every touched repository. They also push `adopt-sandbox-ref-28` in `codex-container`.
- The operator reruns `--container-setup` for Codex on the Linux hosts and on Windows.
- Archive this change with spec sync.
