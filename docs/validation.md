# Validation record

## Environment

Checks for `align-container-sandbox-boundaries` on 2026-11-01 ran as UID/GID
1000:1000 inside the Codex container on Linux x86_64, WSL2 kernel
6.6.87.2-microsoft-standard-WSL2. Python was 3.11.2 and the installed Podman
client was 4.3.1. The checkout was on v9fs; wrapper test fixtures used private
`/tmp` storage backed by tmpfs. No real Codex credentials were used or read.

## Passed checks

- `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`:
  **21 tests passed**, including parameterized rejection matrices. These are
  wrapper checks against synthetic Podman, not real container execution.
- `bash -n codex-container.sh tests/run-runtime.sh`: passed.
- `git diff --check` and whitespace checks on the new text files: passed.
- `openspec validate align-container-sandbox-boundaries --strict`: passed.
- `openspec validate --specs --strict`: all three existing main specs passed.
- The runtime pseudo-terminal helper was exercised against real interactive
  Bash with synthetic output and exit code 23; both were preserved. This
  checks terminal plumbing only, not Podman attachment or filesystem isolation.

Wrapper coverage includes launch-engine failures before image operations,
local/explicit Unix contexts, unsupported connections, help without Podman or
state creation, explicit build/image selection, state creation and existing
state rejection, relative/symbolic paths and spaces, creation-mask scoping,
exact delegation opt-in and independent YOLO combinations, selected socket
precedence, service query errors, host-side path remapping, argument boundaries,
and preservation of workspace, read-only-root, identity, and temporary mounts.

Inaccessible state and socket paths were exercised with real Unix mode changes
as a non-root user. Wrong state ownership was simulated through a controlled
`stat` fixture; no real cross-user ownership check is claimed. A separate
metadata fixture simulated a filesystem reporting permissive modes after
creation; this verifies rejection logic, not behavior of every Windows mount.

## Runtime checks not completed

Without opt-in, `python3 -B -m unittest discover -s tests -p test_runtime.py -v`
reported five intentionally skipped tests. These are not passed runtime checks.

With `CODEX_RUNTIME_TESTS=1`, the suite failed in its prerequisite check before
running any test:

```text
Error: command required for rootless mode with multiple IDs: exec: "newuidmap": executable file not found in $PATH
```

A direct explicit query to `unix:///run/podman/podman.sock` also failed because
that socket is not exposed to this session. `CONTAINER_HOST` was unset. The
available local Podman client therefore cannot supply the required rootless
runtime, and a usable same-host rootless service must be exposed before
finishing integration verification. No image build/startup result is claimed.

The following implemented runtime checks remain unverified against a real
engine, leaving tasks 4.1 and 4.2 open:

- External-sentinel exclusion, actual read-only image enforcement, mapped file
  ownership, and native `codex --version` in the image.
- Persistent `.codex` and reset of `/tmp`, `/var/tmp`, `/run`, and home outside
  `.codex` after container recreation.
- Linked Git worktrees and host-side child-container workspace binds.
- A same-host containerized caller with a remapped socket and host-absolute
  workspace/state mounts.

The disposable-volume runner in `tests/run-runtime.sh` is provided for private
native Linux test storage and environments lacking host Python. It could not
be executed here without that service. Follow the README verification commands
once a usable same-host socket is available, then update this record with the
actual engine, image version, and results before completing the remaining tasks.
Do not interpret Antigravity's validation record as evidence for this wrapper.

Linux arm64, SELinux enforcing behavior, and Codex's internal command sandbox
were not verified. ShellCheck was not installed; Bash syntax checks passed.
No custom seccomp profile, added capability, privileged mode, or nested daemon
was used to bypass the environment limitation.

## Archive disposition

On 2026-11-01, after receiving the 12/14 completion report and runtime
limitations, the user requested specification synchronization, archiving,
and a commit. The change was archived with tasks 4.1 and 4.2 still unchecked;
this disposition does not convert unavailable runtime checks into passes.
The main specifications were synchronized with both deltas and validated.
The remaining real-engine verification can be resumed in a subsequent change
when a same-host rootless service is available.
