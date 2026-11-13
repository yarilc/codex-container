# Tasks

## 1. Adopt sandbox-ref-14

- [x] 1.1 Save the wrapper port as a patch (design decision 1): stash
  everything, reproduce the tool's `sandbox-ref-12` → `sandbox-ref-13` output
  on a temporary branch and commit it there, restore the stash on top, and
  write the diff of the wrapper-owned files (`codex-container.sh`,
  `tests/test_wrapper.py`, `tests/test_runtime.py`,
  `tests/test_network_runtime.py`, `README.md`, `AGENTS.md`, `docs/setup.md`)
  to the scratchpad. Verify that the patch contains no tag reference (the
  only `sandbox-ref-` text is the change name in `docs/setup.md`, set to
  `adopt-sandbox-ref-14`) and no shared file.
- [x] 1.2 Stash the change directory, switch to `main`, delete the branches
  `adopt-sandbox-ref-13` and the temporary one, and run the dry run
  `python3 -I tools/propagate.py ../codex-container sandbox-ref-12
  sandbox-ref-14` from claude-container. Verify that `git status` is clean,
  and that the dry run lists six modified and two added shared files
  (`tests/test_qualification.py` among them), nothing removed or "not
  adopted", and `REFERENCE_COMMIT` `f06c885`.
- [x] 1.3 Run `--apply`, restore the stash on branch `adopt-sandbox-ref-14`,
  and apply the patch with `git apply --3way`. Verify:
  - the stash list is empty;
  - `git diff --name-only` lists the eight shared files,
    `tests/test_reference_copy.py`, `docs/network-contract.md` and the seven
    wrapper-owned files;
  - `python3 -m unittest tests.test_reference_copy tests.test_alignment
    tests.test_toolchains` passes on private temporary storage.

Tasks 2.1–4.1 were implemented on the discarded `sandbox-ref-13` branch. Task
1.3 restores them unchanged, and section 5 verifies them again.

## 2. Launcher, test first

- [x] 2.1 In `tests/test_wrapper.py`, port the reference cases with the fake
  engine (design decision 3):
  - `--container-toolchain` dispatch: first argument only, before the
    network mode, `launch-env` refused, no engine call;
  - private creation when the library is missing, and the
    `ro,nosuid,nodev` mount at `/toolchains`;
  - unsafe library (mode, overlap with the workspace, the installation and
    `CODEX_CONTAINER_STATE_DIR`) rejected before any engine operation;
  - `CODEX_CONTAINER_TOOLCHAINS` `0`/`false`/`no`, and an invalid value;
  - the default environment appended after the image `PATH`, and the single
    warning for a toolchain verified on another base;
  - `--mount-target /toolchains` in offline and provider modes;
  - an unsafe-workspace launch from the home stopping on the overlap, and
    passing with `CODEX_CONTAINER_TOOLCHAINS=0`.

  Verify that the new cases fail on the current launcher.
- [x] 2.2 Port design decision 2 to `codex-container.sh`, including the help
  text for `--container-toolchain`, `CODEX_CONTAINER_TOOLCHAINS` and
  `CODEX_CONTAINER_TOOLCHAINS_DIR`. Verify that `bash -n codex-container.sh`
  and `tests/test_wrapper.py` pass.
- [x] 2.3 Give `tests/run-runtime.sh` a private executable tmpfs at
  `/sandbox-test-tmp` (`0700`, `U=true`, 1 GiB) as `SANDBOX_TEST_TMPDIR`, and
  create the `tests/test_wrapper.py` temporary directory there when the
  variable is set (design decision 5). Verify that
  `bash tests/run-runtime.sh --wrapper` passes; it fails before the change.

## 3. Real-engine checks

- [x] 3.1 Port the reference runtime cases to `tests/test_runtime.py`
  (archive and `FROM scratch` image sources, failing check, read-only mount,
  `node` and `python3` not shadowed, disabled mount) and the live add during
  an offline session to `tests/test_network_runtime.py`. Pass
  `SANDBOX_TOOLCHAIN_EXAMPLES` through `tests/run-runtime.sh` only if a ported
  case uses it. Verify that `bash tests/run-runtime.sh` (the default mode,
  which runs `tests/test_runtime.py`) and the network runtime case pass with
  the current Codex runtime image. Existing runtime cases whose exposed
  parent or nested caller home met the library are adapted (`test_real_worktrees`,
  `test_containerized_caller_with_remapped_socket`).

## 4. Documentation

- [x] 4.1 Add a README "Toolchains" section adapted to Codex (design decision
  4): location and disable variable, live updates, the four commands and
  maintenance pulls, the recipe keys, protected variables, default
  environment and conflicts, writable locations (`/tmp` is executable in
  Codex), dependency downloads, the `AGENTS.md` instruction line, the link to
  claude-container's example recipes, and the untested SELinux and AppArmor
  note. Update the help-related README part, `AGENTS.md` (the shared module)
  and `docs/setup.md` (requalification). Verify that every
  `CODEX_CONTAINER_TOOLCHAINS*` variable and every `--container-toolchain`
  operation appears in both the help text and the README.

## 5. Validation and publication

- [x] 5.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun, which are recorded as such.
- [x] 5.2 Run `bash tests/run-runtime.sh` with every mode the tool listed
  (`--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--guard`,
  `--network`, `--wrapper`) and the default mode, with the new runner.
  Verify that each passes, `--qualification` included, or record it as
  unavailable.
- [x] 5.3 Fill in the tool's validation-record template in
  `docs/validation.md` with the results of 1.3–5.2, the requalification note,
  the operator checks as pending, and a note that the first adoption of
  `sandbox-ref-13` was discarded because of the shared fixture defect.
  Verify that the parity table hash matches claude-container's, `git diff --check` is clean and
  `openspec validate adopt-sandbox-ref-14 --strict` passes.
- [x] 5.4 Commit on `adopt-sandbox-ref-14` with the co-author trailer (the
  tool's message, extended with the launcher port), merge it into `main` with
  `--no-ff`, and verify that `git log --oneline -3` shows the merge.

## Workflow follow-up

- The operator pushes Codex `main` and reruns `--container-setup` on this
  host, the Rocky Linux 9 lab host and the newer WSL host, then checks
  `java -version` in a Codex session with the Temurin 21 toolchain and runs
  `--container-toolchain verify java21`. The results are added to
  `docs/validation.md`.
- Sync the delta spec and archive this change.
