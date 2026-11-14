# Tasks

## 1. Adopt sandbox-ref-16

- [x] 1.1 From claude-container, run `python3 -I tools/propagate.py
  ../codex-container sandbox-ref-14 sandbox-ref-16` (dry run). Verify that it
  lists `setup/toolchains.py` and `tests/test_toolchains.py` as modified,
  nothing added, removed or "not adopted", and commit `1fa091e`.
- [x] 1.2 Stash the change directory, run `--apply`, and restore the stash on
  branch `adopt-sandbox-ref-16`. Verify that:
  - the stash list is empty;
  - `git diff --name-only` lists only the two shared files,
    `tests/test_reference_copy.py` and the four documents;
  - `python3 -m unittest tests.test_reference_copy tests.test_alignment
    tests.test_toolchains` passes on private temporary storage.

## 2. Documentation

- [x] 2.1 Name `XDG_` variables in the README "Protected variables" bullet.
  Verify with `grep -n 'XDG_' README.md`.

## 3. Validation and publication

- [x] 3.1 Run the full unit discovery on private executable temporary
  storage. Then run `bash tests/run-runtime.sh` with the modes the tool lists
  (`--shared`, `--setup`, `--setup-runtime`), plus `--qualification` (a
  `SHARED_CODE` file changed), `--wrapper` and the default mode (the launcher
  runs `launch-env`). Use the current Codex setup image. Verify that each
  passes.
- [x] 3.2 Fill in the tool's validation-record template in
  `docs/validation.md` with the results, the requalification note and the
  operator setups as pending. Verify that:
  - the parity table rows match claude-container's;
  - `git diff --check` is clean;
  - `openspec validate adopt-sandbox-ref-16 --strict` passes.
- [x] 3.3 Commit on `adopt-sandbox-ref-16` with the tool's message and the
  co-author trailer, merge into `main` with `--no-ff`, and verify that
  `git log --oneline -3` shows the merge.

## Workflow follow-up

- The operator pushes Codex `main` and reruns `--container-setup` on the
  three hosts. The results are added to `docs/validation.md`.
- Sync the delta spec and archive this change.
