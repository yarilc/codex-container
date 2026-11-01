# Repository Guidelines

## Project Structure & Module Organization

- `codex-container.sh` handles wrapper arguments, workspace mounts, user mapping,
  container naming, and Podman socket validation.
- `Containerfile` defines the Codex runtime image and bundled tools.
- `README.md` documents setup, usage, and security considerations.
- `openspec/specs/` contains current behavior contracts; `openspec/changes/`
  holds active proposals and dated archives.
- There are no separate source, test, or asset directories.

## Build, Test, and Development Commands

Run from the repository root:

```bash
./codex-container.sh --container-build  # Build image, then start Codex
./codex-container.sh                    # Start in the current workspace
./codex-container.sh --container-shell # Open Bash in the runtime image
./codex-container.sh --container-help  # Show wrapper options
bash -n codex-container.sh              # Check Bash syntax
git diff --check                       # Check whitespace
openspec validate --specs --strict      # Validate main specifications
```

Host rootless Podman is required to build and launch the runtime. Only sessions
using `CODEX_CONTAINER_PODMAN=1` require the API socket; start it with
`podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock`.
The Podman command remains installed without the opt-in, but the wrapper omits
the socket mount and removes `CONTAINER_HOST` from the session environment.
Both Codex and shell modes use a read-only image root with writable workspace,
persistent `CODEX_HOME`, and ephemeral `/tmp`, `/var/tmp`, `/run`, and home.
Use `--container-git-worktree` from a worktree root to expose its immediate
physical parent while preserving the starting directory.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quoted variables, and command arrays for
user-controlled arguments. Follow the script's four-space indentation. Prefer
small functions, actionable errors, lowercase `snake_case` local variables,
and uppercase environment/configuration variables. Write documentation,
comments, help, and messages in English.

## Testing Guidelines

There is no test framework or coverage threshold. Every script change must
pass syntax and whitespace checks. Verify argument order and boundaries,
default/parent mounts, spaces, symlinks, and shell mode. With usable Podman,
check image build, Codex startup, isolated `CODEX_HOME` persistence, local Git
worktrees, and child-container bind mounts. Use disposable local repositories
and configuration; record unavailable checks separately from mock results.

## OpenSpec Workflow

For OpenSpec changes, keep proposal, delta specs, design, and tasks coherent.
Proposal work changes planning artifacts only; implement through the apply
workflow. Mark tasks complete after verification, synchronize delta specs into
main specs, and archive completed changes under dated directories.

## Commit & Pull Request Guidelines

Use concise imperative subjects, such as `Add Git worktree parent mount option`.
Keep commits focused. PRs should explain behavior changes, list verification,
identify security/mount changes, and update `README.md` when usage changes.

## Security & Configuration

Treat Codex configuration and the Podman socket as sensitive. Never embed
credentials or add `--privileged`. Preserve absolute workspace paths for child
bind mounts. Parent mounting is opt-in and exposes all contents read/write,
potentially including the home directory or `/`; do not broaden mounts beyond
that documented behavior.
