# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small, self-contained Podman wrapper for running
Codex CLI:

- `codex-container.sh` is the entry-point script and owns argument parsing,
  volume mounts, user mapping, and Podman socket validation.
- `Containerfile` defines the Codex runtime image and its shell/tooling
  baseline.
- `README.md` documents setup, usage, and security considerations.
- There are currently no separate source, test, or asset directories.

## Build, Test, and Development Commands

Run these commands from the repository root:

```bash
./codex-container.sh --container-build  # Build or refresh the local image
./codex-container.sh          # Start Codex in the current workspace
./codex-container.sh --container-shell  # Open a shell in the runtime image
bash -n codex-container.sh    # Validate Bash syntax
git diff --check              # Detect whitespace errors
```

The runtime requires a rootless Podman socket, for example:
`podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock`.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quote variables, and prefer explicit
arrays for commands with user-controlled arguments. Keep functions small and
fail with actionable messages. Use two- or four-space indentation consistently
within a block, lower-case `snake_case` for local shell variables, and
upper-case names for environment/configuration variables. Keep image and file
names descriptive and lowercase (`Containerfile`, `codex-container.sh`). Write
all documentation, code comments, help text, and user-facing messages in
English.

## Testing Guidelines

There is no test framework yet. Every script change must pass `bash -n` and
`git diff --check`; when Podman is available, verify `--container-help`, Codex
argument forwarding, image build, Codex startup, persistence of `~/.codex`,
and a child `podman run`. Avoid
embedding credentials or relying on a remote Git repository in tests.

## Commit & Pull Request Guidelines

The repository history is minimal, so use concise imperative commit subjects,
for example `Add Podman socket validation`. Keep each commit focused. Pull
requests should explain behavior changes, list verification commands, call out
security or mount changes, and update `README.md` when usage changes.

## Security & Configuration

Treat `~/.codex` and the Podman socket as sensitive. Do not copy credentials
into the image, broaden mounts unnecessarily, or add `--privileged`. Preserve
the host workspace's absolute path so containers launched by the host Podman
service can resolve child bind mounts correctly.
