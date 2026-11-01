# Design

## Context

See `proposal.md` for motivation. The wrapper currently launches one image with a writable root, mounts the workspace and host Codex directory read/write, and unconditionally checks and mounts the host rootless Podman socket. `Containerfile` already installs Podman and sets `HOME=/codex-home`. Both shell and Codex modes share the same run argument array. Existing `workspace-mounts` requirements explicitly preserve writable host binds, including a possible `/` parent mount.

## Goals / Non-Goals

**Goals:** Apply one filesystem policy to both entry modes, keep persistent state and temporary writes usable for the mapped user, and make the existing host service connection opt-in without changing the installed tools or image selection.

**Non-Goals:** Remove or disable the Podman executable, provide image variants, support a nested daemon, block all user-configured remote endpoints, change workspace selection, or turn existing writable host mounts into read-only mounts.

## Decisions

### Read-only root with explicit temporary filesystems

Add `--read-only` to the common runtime arguments. Explicitly configure writable tmpfs mounts at `/tmp`, `/var/tmp`, `/run`, and `/codex-home`; disable automatic read-only tmpfs additions if necessary to avoid duplicate mounts. Use permissions that let the keep-id user write, preserving the current writable-home behavior. Retain the more specific persistent bind at `/codex-home/.codex` and existing workspace bind. Keep standard engine-provided device and shared-memory mounts.

This keeps shell caches and temporary home files ephemeral without adding a new persistent host directory. Making all of HOME persistent would broaden the existing persistence contract; leaving HOME entirely read-only would needlessly break tools that write outside `.codex`. Verify nested mounts and socket target creation on the supported host Podman runtime. If mountpoints must be prepared in the image, change only directory preparation in `Containerfile` and retain its installed tools.

Temporary storage must allow the same useful operations as the previous runtime, including execution of temporary build artifacts where the host permits it. Tests must inspect effective tmpfs options instead of relying on undocumented engine defaults.

### Exact environment opt-in at the wrapper boundary

Evaluate `${CODEX_CONTAINER_PODMAN:-}` using an exact comparison with `1`; treat every other value as disabled. Unlike `CODEX_YOLO`, this variable has no truthy aliases. Do not forward it to Codex as an argument.

Keep the host Podman executable check, image build/existence logic, naming, and image override unchanged. Move host socket path validation, its bind argument, and the `CONTAINER_HOST` argument into the enabled branch. Use `--unsetenv CONTAINER_HOST` in the disabled branch to remove any image default as well as avoid forwarding the caller's value. Both modes share these arguments, so switching to Bash cannot bypass the policy.

Keep the client installed in the single runtime image. The disabled contract is the absence of the wrapper-provided host connection, without restricting commands a user might configure independently.

### Preserve existing writable bind scope

Do not alter workspace path selection, parent selection, working directory, state persistence, or argument boundaries. Update the existing child-container scenario to require the opt-in. The image root is read-only beneath explicit mounts; a broad workspace bind can mask image paths, especially when the selected parent is `/`. Document that existing writable host binds take precedence rather than claiming that read-only root makes those locations immutable.

### Document setup by access mode

Keep ordinary host rootless Podman setup required for all launches. Make API service setup and verification conditional on `CODEX_CONTAINER_PODMAN=1` in README and repository guidance. Help and README must show enabled Codex and shell examples, the exact accepted value, persistent and ephemeral writable paths, and migration for existing child-container users. Retain socket security and parent-mount scope explanations.

## Risks / Trade-offs

- Read-only root can expose tool writes to previously writable image paths → Verify Codex startup, OpenSpec availability, shell mode, temporary build execution, and state persistence using disposable directories; add only justified ephemeral paths if a concrete runtime need emerges.
- Mounting the persistent Codex directory or socket below tmpfs parents can fail with an incorrect mount layout → Verify both nested mounts with real Podman, not only captured command arguments.
- A write denied by ordinary user permissions can falsely appear to prove read-only protection → Inspect the root mount and test a disposable image path writable by the mapped user before read-only is applied.
- Missing socket exposure does not prevent a user from explicitly configuring another endpoint or exposing a socket through a broad workspace bind → Describe the actual wrapper boundary; retain existing workspace behavior and avoid a blanket claim that the Podman binary cannot execute.
- Existing documentation assumes the socket is mandatory → Update README, help, and `AGENTS.md` together and distinguish host startup requirements from in-container service access.

## Migration Plan

Implement and verify wrapper changes without introducing a new image tag. Rebuild only if directory preparation in `Containerfile` changes. Existing users needing host child containers set `CODEX_CONTAINER_PODMAN=1` and retain the documented socket setup. Default users no longer need an API service. To roll back, restore the prior wrapper and corresponding documentation; persistent workspace and Codex data formats are unchanged.
