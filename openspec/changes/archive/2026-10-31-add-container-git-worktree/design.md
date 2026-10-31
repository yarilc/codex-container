# Design

## Context

See `proposal.md` for motivation and the pinned upstream reference. The local wrapper sets `WORKSPACE` using `pwd -P`, derives container names from it, passes it to `--workdir`, and mounts it directly. Argument parsing already separates wrapper flags from the array forwarded to Codex. Git, Bash, and `dirname` are available; no image additions are necessary. There are no existing main specs or test framework.

A design document is included because parent mounts change the writable host scope. The behavior contract is in `specs/workspace-mounts/spec.md`.

## Goals / Non-Goals

**Goals:**
- Keep working-directory identity independent of workspace mount selection.
- Match the inspected upstream worktree flag with a small change to the existing wrapper.
- Make the expanded writable scope explicit and preserve host paths for child containers.

**Non-Goals:**
- Discover Git roots, create/remove worktrees, rewrite `.git` files, or guarantee every worktree layout works.
- Import upstream read-only filesystem settings, CA trust, configuration mounts, or other unrelated features.
- Add new dependencies, a test framework, or interactive mount approval.

## Decisions

### Keep `WORKSPACE` and select a separate mount source

Add a `git_worktree=0` switch to the existing parser. After parsing, initialize `workspace_mount` from `WORKSPACE`; when enabled, select `dirname -- "$WORKSPACE"`. Use the selected path for both source and destination in the single workspace volume argument, retaining quotes and the existing command arrays.

Keep `WORKSPACE` for working directory and container prefix. Changing `WORKSPACE` itself would also move the starting directory and change names. Adding a second, overlapping workspace mount would be redundant; replace the existing one instead.

### Mirror the immediate physical parent without Git discovery

The user requested the upstream behavior, which uses the parent of `pwd -P`. A nested launch directory therefore selects its immediate parent, and a symlink resolves before selection. No Git check or metadata-path inspection is added. Automatic root discovery or extra mounts would introduce different semantics and potentially expose additional directories. At `/`, the selected parent is still `/`, matching upstream.

### Preserve wrapper composition

Consume the new boolean flag wherever the current parser handles wrapper options. Repeated occurrences simply set the same switch. Keep build selection, shell entrypoint, Codex arguments, `CODEX_YOLO`, identity, configuration persistence, and socket handling on their existing paths. Help must remain available without Podman setup.

### Document the full mount boundary

Update help and README together. Use `/path/to/root/main` as the launch example and show `/path/to/root` as the selected mount. Explain that metadata and siblings are accessible only if already beneath the selected parent, that nested launches do not search upward, and that all parent contents are writable. Explicitly mention parents such as the home directory and `/`. The existing configuration and socket mounts remain separate exceptions to the workspace boundary.

### Verify arguments separately from runtime behavior

Use a disposable local verification harness to capture Podman arguments, with isolated Codex configuration and mocked external prerequisites where needed; do not change the host socket or use real credentials. Cover mount selection, argument boundaries, naming, shell/build composition, repeated flags, symlinks, spaces, and root-path selection. A mock can establish command construction but cannot establish Git or child-container behavior.

When a usable rootless Podman runtime is available, use a temporary local Git repository and a sibling linked worktree under a common parent. Verify `git status` and `git worktree list` from the container, the preserved working directory, write access to a disposable sibling marker, and a child container bind mount using the same absolute path. Include the required image-build, Codex-startup, and configuration-persistence smoke checks with isolated configuration. Record runtime limitations explicitly if the environment cannot perform these checks.

## Risks / Trade-offs

- [The parent exposes unrelated files, potentially a whole home directory or `/`] → Keep access opt-in and describe the exact writable boundary in help and README; choose a disposable parent for verification.
- [Shared Git metadata is outside the selected parent] → Document supported layouts and invocation from the worktree root; add no automatic broader mounts.
- [Mocks conceal runtime Git or socket failures] → Distinguish captured arguments from real Podman verification and report unavailable checks.
- [Paths containing spaces are split accidentally] → Retain quoted array arguments and include a spaced-path case in verification.

## Migration Plan

No image rebuild or configuration migration is required for this feature. Update the wrapper and README together; existing invocations retain the current-directory mount. Users enable the new behavior by adding `--container-git-worktree`. Roll back usage by omitting the flag, or revert the wrapper and documentation change.
