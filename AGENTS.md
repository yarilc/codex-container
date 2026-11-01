# Repository Guidelines

## Project Structure & Module Organization

- `codex-container.sh` handles wrapper arguments, workspace mounts, user mapping,
  container naming, and Podman socket validation.
- `Containerfile` defines the Codex runtime image and bundled tools.
- `README.md` documents setup, usage, and security considerations.
- `openspec/specs/` contains current behavior contracts; `openspec/changes/`
  holds active proposals and dated archives.
- `tests/` contains synthetic wrapper tests and opted-in real Podman checks.
- `docs/validation.md` records verification results and environment limitations.

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

Host Linux rootless Podman is verified before image operations and startup,
independently of delegation, YOLO, shell mode, and explicit builds. Local Podman
needs no API service. Explicit absolute same-host Unix `CONTAINER_HOST` launch
connections require their own service even with delegation disabled; named,
TCP/SSH, implicit remote, and unverifiable contexts are rejected. Only sessions
using `CODEX_CONTAINER_PODMAN=1` require a delegation socket; start it with
`podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock`.
Enabled sessions select the first nonempty `CODEX_CONTAINER_PODMAN_SOCKET`,
Unix `CONTAINER_HOST` path, or `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`.
They explicitly query that socket and require `Host.Security.Rootless`
to report `true` before image inspection, building, or startup. The selected
socket must be absolute, readable, and writable. Use the service's absolute
`Host.RemoteSocket.Path` as the bind source, which may differ from the visible
socket in a containerized caller. Both engines and all absolute bind sources
must refer to the same host; forwarded cross-host sockets are unsupported. Rootful,
unreachable, or unverifiable services produce an actionable error in both
Codex and shell modes, including `--container-build`.
The Podman command remains installed without the opt-in, but the wrapper omits
the socket mount and removes `CONTAINER_HOST` from the session environment.
Both Codex and shell modes use a read-only image root with writable workspace,
persistent `CODEX_HOME`, and ephemeral `/tmp`, `/var/tmp`, `/run`, and home.
`CODEX_HOME` defaults to the caller's shared `~/.codex`; a separate directory
is explicit opt-in, not automatic per-project isolation. Before image
operations, missing state is created privately with a scoped umask, and its
resolved directory must be caller-owned, accessible, and deny group/other
permissions. Reject invalid state without automatic chmod/chown; suggest an
explicit correction or private native Linux storage when Unix modes are ignored.
State checks do not audit ancestors, ACLs, or every existing file.
Use `--container-git-worktree` from a worktree root to expose its immediate
physical parent while preserving the starting directory.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quoted variables, and command arrays for
user-controlled arguments. Follow the script's four-space indentation. Prefer
small functions, actionable errors, lowercase `snake_case` local variables,
and uppercase environment/configuration variables. Write documentation,
comments, help, and messages in English.

## Testing Guidelines

Tests use Python's standard-library `unittest`; there is no coverage threshold.
Every script change must
pass syntax and whitespace checks. Verify argument order and boundaries,
default/parent mounts, spaces, symlinks, and shell mode. With usable Podman,
check image build, Codex startup, isolated `CODEX_HOME` persistence, local Git
worktrees, and child-container bind mounts. Use disposable local repositories
and configuration; record unavailable checks separately from mock results.
Standard-library Python tests live in `tests/`. Run wrapper checks with
`python3 -B -m unittest discover -s tests -p test_wrapper.py -v`. Real runtime
checks require opt-in via `CODEX_RUNTIME_TESTS=1`, a built image, a same-host
rootless service, and private host-visible `CODEX_TEST_ROOT`, or use
`bash tests/run-runtime.sh` for disposable native Linux volume storage. Use a
pseudo-terminal for the wrapper's existing TTY behavior. Record results and
limitations in `docs/validation.md`; do not treat skipped or synthetic tests
as real engine verification, and do not use actual Codex credentials in tests.

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

Treat Codex configuration and the Podman socket as sensitive. Socket delegation
permits new host mounts outside the workspace with the service user's authority;
rootless operation does not retain project-only access. YOLO and delegation
are independent; disabled YOLO does not override native flags or settings. Never embed
credentials or add `--privileged`. Preserve absolute workspace paths for child
bind mounts. Parent mounting is opt-in and exposes all contents read/write,
potentially including the home directory or `/`; do not broaden mounts beyond
that documented behavior.
