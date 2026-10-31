# Tasks

## 1. Implement and document workspace mount selection

- [x] 1.1 Add the boolean `--container-git-worktree` parser switch and separate `workspace_mount` selection in `codex-container.sh`; use it for the workspace volume while retaining `WORKSPACE` for working directory and naming. Verify `bash -n codex-container.sh` passes and inspect captured Podman arguments for default and parent mounts.
- [x] 1.2 Update wrapper help and `README.md` with the new option, Codex/shell examples from a worktree root, physical immediate-parent semantics, nested-directory behavior, sibling write access, home/root exposure, and unavailable external Git metadata. Verify `--container-help` works without Podman prerequisites and the documented example paths match `specs/workspace-mounts/spec.md`.
- [x] 1.3 Use a disposable argument-capture harness with isolated configuration and mocked external prerequisites to exercise default/flagged mounts, nested and non-Git directories, symlinks, spaces, root selection, repeated flags, build/shell composition, naming, Codex argument boundaries, and `CODEX_YOLO`. Verify captured commands retain the expected workdir, configuration/socket mounts, user mapping, and argument order; record results without altering the real socket or mounting the host root in a real container.
- [x] 1.4 Run `bash -n codex-container.sh` and `git diff --check` on the completed script/documentation change, and verify the diff introduces no image changes or unrelated upstream features.

## 2. Verify runtime integration

- [x] 2.1 When rootless Podman is usable, create a temporary local repository and sibling linked worktree beneath a disposable common parent, then run shell mode from the worktree with the flag. Verify `pwd`, `git status`, `git worktree list`, and a write to a disposable sibling marker; confirm a child `podman run` reads a marker through an identical absolute-path bind mount. Record commands/results, or explicitly record why runtime verification is unavailable.
- [x] 2.2 When rootless Podman is usable, verify image build, Codex startup, and configuration persistence across sessions using isolated `CODEX_HOME` without real credentials; smoke-check the default mount without the flag. Record successful observations and any environment or authentication limitations separately from mock results.

## Verification results

- `bash -n codex-container.sh`, `git diff --check`, and `openspec validate add-container-git-worktree --strict` passed.
- A disposable argument-capture harness passed 11 scenarios covering default and parent mounts, non-Git/nested directories, symlinks, spaces, filesystem root, repeated flags, shell/build composition, container naming, argument boundaries, and `CODEX_YOLO`. Only the socket assignment in the temporary script copy was redirected to a disposable Unix socket; the repository script was unchanged for this prerequisite simulation.
- The original script's `--container-help` passed with Podman absent from `PATH`.
- Real runtime checks used the unmodified wrapper, a temporary local Git repository with a sibling linked worktree, and an isolated `CODEX_HOME`. A dedicated launcher container exposed the host socket at `/run/user/1000/podman/podman.sock`, the path expected by the wrapper; the current session exposes it at `/run/podman/podman.sock`. No real credentials or remote Git repositories were used.
- `--container-git-worktree --container-shell` passed working-directory checks, `git status --porcelain`, `git worktree list`, a sibling-file write, and a child `podman run` reading a marker through an identical absolute-path bind mount.
- A second `--container-shell` session without the flag confirmed the sibling marker was unavailable and the isolated Codex configuration marker persisted across sessions.
- `--container-git-worktree --version` passed. `--container-git-worktree --container-build --version` rebuilt `localhost/codex-cli:latest` and successfully started Codex from the rebuilt image. Interactive authentication was not exercised.
- Temporary workspaces and containers were removed after verification. `Containerfile` was not modified.
