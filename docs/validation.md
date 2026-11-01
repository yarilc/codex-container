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

## Session lifecycle hardening: 2026-11-01

The `harden-container-session-lifecycle` verification used UID/GID 1000:1000,
a Podman 4.3.1 client, and a reachable Linux amd64 rootless Podman 4.9.3
service through an explicit same-host Unix `CONTAINER_HOST`. The service
reported rootless `true` and service-remote `true`. Unlike the earlier session
above, this session had the service socket exposed. Runtime state and projects
used a disposable native Linux Podman volume through `tests/run-runtime.sh`.
No actual Codex credentials were used or read.

The initial directly enabled runtime command used the checkout's default
`.test-state` and failed all ten tests in setup because that filesystem
reported mode 0777 instead of the requested 0700. No session behavior was
verified by that attempt. The documented native-volume runner resolved this
storage limitation without weakening state privacy checks.

The first native-volume run passed nine tests and exposed an additional
Podman stop grace period during forced cleanup of a TERM-ignoring application.
The wrapper now uses `rm --force --ignore --time 0` after its own grace period,
avoiding Podman's default ten-second stop wait. The focused real-engine signal
test then passed, including cleanup isolation and absence of residual session
containers.

Production image construction with the new `.containerignore` succeeded using
cached layers and a disposable validation tag, which was removed afterwards.
The resulting image ID was
`2a57f466c2effa654dcaafc516851072f4c8b36dadd2b07e90f095330b69c75f`.
This verifies the unchanged Containerfile still builds with the reduced context;
it does not claim a fresh package installation. The separate context regression
uses a no-cache disposable build with dummy root and nested sensitive files,
an unknown file, and a nested Containerfile, proving those inputs are excluded.

The synthetic wrapper suite covers checked all-container naming, decimal bounds
and leading zeroes, collision recovery and exhaustion, creation/inspection/build
errors, full-ID cleanup and diagnostics, pending creation signals, TERM/INT/HUP
in both entrypoint modes, ignored signals, failed/stalled control calls, bounded
client termination, application exit 125, all four stdin/stdout terminal
combinations, pipe/file input and EOF, exact tmpfs options, and the preexisting
engine, state, delegation, and workspace contracts.

The real-engine suite additionally checks competing wrapper starts with a
stopped `-08` container, distinct reserved names, actual TERM/INT/HUP delivery,
forced cleanup for a TERM-ignoring application, unrelated-container survival,
application exit 125, PTY and redirected input, tmpfs capacity and permission
inspection, executable temporary files, `/run` exhaustion, persistent state,
ephemeral reset, root filesystem protection, mapped ownership, real worktrees,
child binds, and a containerized caller with a remapped Unix socket.

Local engine execution without `CONTAINER_HOST` remains unavailable in this
container: `podman info` fails because `newuidmap` is not installed. The real
results cover explicit Unix service execution, not the local engine path.
Linux arm64, SELinux enforcing behavior, and Codex's internal command sandbox
remain unverified. SIGKILL, host failure, and service loss cannot guarantee
owned cleanup. Earlier archived task states are historical and are not changed
by this run.

Final checks after the forced-removal correction:

- `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`:
  **33 tests passed** in 62.802 seconds, using synthetic Podman responses.
- `bash tests/run-runtime.sh`: **10 real-engine tests passed** in 36.547
  seconds with disposable native Linux volume storage. The runner removed its
  volume, temporary context-test image, and fixture containers; no residual
  session-test containers or validation image tags were found afterwards.
- `bash -n codex-container.sh tests/run-runtime.sh`: passed.
- `git diff --check` and whitespace checks on new planning and ignore files:
  passed.
- `openspec validate harden-container-session-lifecycle --strict`: passed.
- `openspec validate --specs --strict`: all three existing main specs passed;
  delta synchronization is a later workflow action.

### Archive disposition

On 2026-11-01, the completed `harden-container-session-lifecycle` change was
synchronized and archived at
`openspec/changes/archive/2026-11-01-harden-container-session-lifecycle/`
with all 19 tasks complete. Synchronization created `container-image` with
four requirements and `container-session` with seven requirements, and added
two requirements to `runtime-filesystem`, preserving its existing requirements.
All five resulting main specs passed strict validation, and every added
requirement and scenario was compared with its delta before archival.
