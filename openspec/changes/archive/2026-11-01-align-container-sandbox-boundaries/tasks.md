# Tasks

## 1. Launch-engine preconditions

- [x] 1.1 Add independent launch-engine and connection validation before image operations in `codex-container.sh`; verify Linux/rootless and recognized service-remote responses, rejection of unsupported contexts, and unchanged help behavior with focused fake-Podman tests in `tests/test_wrapper.py`.
- [x] 1.2 Test invalid/missing/query-failed engine responses in Codex and shell modes, with and without delegation, YOLO, and `--container-build`; verify no image inspection, build, or run occurs and a valid delegated endpoint cannot bypass a bad launch engine.
- [x] 1.3 Update README/help/AGENTS engine guidance in this group; verify examples distinguish local operation without an API service from same-host Unix-connected launch operation, and run `bash -n codex-container.sh` and `git diff --check`.

## 2. Private persistent state

- [x] 2.1 Add scoped private creation, physical-path resolution, owner/mode/access checks, and path-specific errors for `CODEX_HOME` before image operations; verify with wrapper tests for new and existing state, files, spaces, relative paths, symlinks, incorrect modes, and failed resolution without changing existing data or permissions.
- [x] 2.2 Cover wrong-owner, inaccessible-state, and non-enforcing filesystem cases using controlled fixtures or real suitable storage; record unavailable privilege-dependent cases explicitly and verify the creation umask does not leak to subsequent operations.
- [x] 2.3 Document state remediation and separate Linux `CODEX_HOME` examples in README/AGENTS; verify the default and nested persistent mount remain unchanged, help creates no state, and guidance does not imply recursive auditing, encryption, or automatic migration.

## 3. Delegation socket selection and remapping

- [x] 3.1 Add `CODEX_CONTAINER_PODMAN_SOCKET` selection and validation, explicit endpoint verification, and host-side source resolution using `Host.RemoteSocket.Path`; verify precedence and a remapped source with fake-Podman tests returning distinct client/host paths.
- [x] 3.2 Add regression cases for invalid selected sockets, query errors, rootful/indeterminate services, empty/relative host-side paths, and different launch/delegation endpoints; verify failure precedes every image operation in both session modes including explicit build.
- [x] 3.3 Verify exact `1` activation, disabled invalid overrides being ignored, no delegated socket queries/mounts when disabled, and `--unsetenv CONTAINER_HOST`; test all YOLO/delegation combinations and argument boundaries without changing existing YOLO parsing or workspace semantics.
- [x] 3.4 Update README/help/AGENTS with socket precedence and override examples, same-host path requirements, four permission combinations, and access beyond the workspace; verify no privileged mode, extra host mounts, or seccomp workaround is introduced.

## 4. Real boundary integration and validation evidence

- [ ] 4.1 Add an explicitly opted-in standard-library Python runtime suite in `tests/test_runtime.py` using disposable repositories and private state plus a pseudo-terminal for the unchanged wrapper; verify external sentinels are inaccessible, image paths reject writes, host file ownership matches the caller, `.codex` persists, and `/tmp`, `/var/tmp`, `/run`, and home outside `.codex` reset between sessions.
- [ ] 4.2 Exercise real linked worktrees and child-container workspace binds, then a same-host containerized caller with a remapped service socket and host-absolute workspace/state paths; verify actual files and ownership rather than relying only on command exit codes or mock arguments.
- [x] 4.3 Document runnable wrapper/runtime test commands and prerequisites alongside the new tests; run the complete wrapper suite and available opted-in integration cases, recording exact environment and separate pass/fail/skip results in `docs/validation.md` without accessing real Codex credentials or claiming Antigravity results as Codex evidence.
- [x] 4.4 Run `bash -n codex-container.sh`, `git diff --check`, `openspec validate align-container-sandbox-boundaries --strict`, and `openspec validate --specs --strict`; verify implementation matches both deltas and record any unavailable architecture or SELinux checks separately.

## Workflow follow-up

- Synchronize the verified delta specifications into the main specifications through the OpenSpec completion workflow.
- Archive the completed change after review, preserving any explicitly accepted unavailable verification in the validation record.
