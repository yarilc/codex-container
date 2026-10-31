# Proposal

## Why

The current wrapper exposes only the launch directory, so linked Git worktrees cannot resolve shared metadata or sibling worktrees outside that directory. Add the same explicit parent-directory mount offered by `claude-container` so users can select a common parent while retaining the original working directory and host paths.

## What Changes

- Add the boolean wrapper option `--container-git-worktree`, consumed instead of forwarded to Codex.
- With the flag, replace the workspace bind mount with a read/write bind mount of the immediate parent of the physical launch directory at its identical absolute path.
- Keep the original launch directory as the container working directory and the source of container naming, in both Codex and shell modes.
- Retain the existing workspace-only mount when the flag is absent.
- Document usage from a worktree root, sibling-file exposure, and the limitation that Git metadata outside the selected parent remains unavailable.

## Capabilities

### New Capabilities

- `workspace-mounts`: Workspace mount selection, absolute-path preservation, and compatibility with working directories, argument forwarding, and child containers.

### Modified Capabilities

None. The project currently has no main capability specs.

## Impact

- `codex-container.sh`: Argument parsing, mount-source selection, and wrapper help.
- `README.md`: Supported wrapper flags, worktree examples, and mount/security documentation.
- No image or dependency changes are needed. The flag intentionally broadens writable access to the selected parent's entire contents; existing Codex configuration and Podman socket mounts retain their behavior.
- Reference verified at `yarilc/claude-container` commit `84f01d4e9d5d5d972b3f37ffc0275db995da3a98`: [wrapper](https://github.com/yarilc/claude-container/blob/84f01d4e9d5d5d972b3f37ffc0275db995da3a98/claude-container.sh) and [README](https://github.com/yarilc/claude-container/blob/84f01d4e9d5d5d972b3f37ffc0275db995da3a98/README.md). Only its worktree mount behavior is in scope.
