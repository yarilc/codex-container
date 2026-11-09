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

## Runtime validation and temporary storage: 2026-11-01

The `tighten-runtime-validation-and-temp-storage` checks used a Podman 4.3.1
client and a Linux amd64 rootless Podman 4.9.3 service through an explicit
same-host Unix connection. The service reported rootless `true` and
service-remote `true`. Runtime fixtures used disposable native Linux volume
storage through `tests/run-runtime.sh`, preserving host absolute paths and
private test state. No actual Codex credentials were used or read.

Endpoint regressions verify that `unix://`, `unix:///`, longer slash-only
forms, and relative paths are rejected without any Podman call in Codex and
shell modes, including explicit builds. Valid absolute paths, including a
path with spaces and repeated leading slashes, remain supported. Existing
synthetic local-engine and explicit-Unix checks also pass.

Exact-byte response fixtures distinguish no final LF, one normal final LF,
and extra trailing blank records. Both verification endpoints reject extra
leading/interior/trailing records, invalid fields, CR characters, and failed
queries that emit valid-looking output before image operations or state
creation. The normal two-record delegated format and a host socket path
containing spaces are retained. Existing print-based fixtures remain covered.

YOLO regressions cover mixed-case enabled and disabled values, numeric values,
empty and unset behavior, invalid and whitespace-padded values, both entrypoint
modes, argument boundaries, explicit native `--yolo` with a disabled environment
switch, read-only/workspace mounts, and exact delegation opt-in independently
of YOLO normalization. Help, README, and repository guidance document these
values and the endpoint/response boundaries.

Synthetic creation arguments confirm `/var/tmp` uses
`rw,exec,nosuid,nodev,mode=1777,size=512m` across session, delegation, and YOLO
settings. Real statvfs and mode checks confirm its 536870912-byte capacity,
mode 1777, nosuid/nodev flags, and execution support. A temporary executable
runs successfully and disappears on the next session, where the capacity and
execution policy are checked again. Existing `/run` exhaustion, other temporary
locations, workspace, persistent state, and lifecycle checks continue to pass.
Documentation now states all three capacities: `/tmp` and `/var/tmp` at
512 MiB each and `/run` at 32 MiB. Ephemeral home has no explicit cap; the
capacities are not reserved memory or a total container memory limit.

Final results:

- `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`:
  **39 synthetic tests passed** in 98.648 seconds, including parameterized
  endpoint, response, YOLO, and mount cases.
- `bash tests/run-runtime.sh`: **10 real-engine tests passed** in 37.248
  seconds, including host service delegation, socket remapping, stdin/TTY
  behavior, concurrent names, signals, cleanup, worktrees, storage, and
  build-context filtering.
- `bash -n codex-container.sh tests/run-runtime.sh`, `git diff --check`, and
  strict validation of `tighten-runtime-validation-and-temp-storage`: passed.
- `openspec validate --specs --strict`: all five current main specs passed;
  synchronization of this change's three deltas remains a later workflow step.

Actual local-engine execution without a Unix service endpoint was not repeated
in this run; the real results cover explicit same-host Unix execution. Linux
arm64, SELinux enforcing behavior, and Codex's internal command sandbox remain
outside the verified coverage. A fresh production image build was unnecessary
because image packages and build inputs were unchanged. No runtime resource
limit was weakened to execute these tests.

### Archive disposition

On 2026-11-01, `tighten-runtime-validation-and-temp-storage` was synchronized
and archived at
`openspec/changes/archive/2026-11-01-tighten-runtime-validation-and-temp-storage/`
with all ten tasks complete. Synchronization added one YOLO requirement to
`container-session`, added two response/documentation requirements and updated
the Unix endpoint requirement in `podman-access`, and updated both temporary
storage capacity/documentation requirements in `runtime-filesystem`. Existing
unaffected requirements and scenarios were preserved. Every added or modified
block was compared with its delta, and all five main specs passed strict
validation before archival. `todo.md` remains excluded by `.gitignore`.

## Bounded interrupted creation (2026-11-01)

Change: `bound-interrupted-container-creation`.

Real-engine regression verification used `bash tests/run-runtime.sh` against
same-host Linux rootless Podman, with disposable native Linux volume storage,
private application state, and no Codex credentials. All 10 runtime tests passed
in 59.071 seconds. Coverage includes concurrent reservation alongside a stopped
container, signal delivery and owned cleanup, an application ignoring TERM,
exit 125, nonterminal input and PTY handling, persistent and ephemeral storage,
mount boundaries, linked worktrees, child-container binds, and a containerized
caller with a remapped service socket. The existing runtime image was reused;
the Containerfile and dependencies did not change. Build-context verification
ran through its disposable verification image as part of the runtime suite.

These are real-engine regression results, not an injected engine hang or outage.
Permanent creation stalls, late CID publication, invalid identities, and client
reaping failure are exercised separately with synthetic Podman responses and
fault injection. Cancellation of a local client cannot establish that an
engine-side create request stopped; unknown outcomes still require explicit
engine inspection.

Focused final checks passed for a stopped (SIGSTOP) creation client, complete
CID validation including NUL/CR/extra-record rejection, and failed or stalled
owned removal. The SIGSTOP regression confirms stopped children remain tracked
until cancellation instead of reaching an unconditional live-child wait.
A separate real-engine signal/owned-cleanup rerun passed after the final child
tracking change (1 test, 13.556 seconds). A shell fault-injection check exercises
the production reaping helper with a client still reported present after KILL;
it verifies the PID diagnostic and absence of an unconditional wait, without
creating a real uninterruptible process.

Final validation commands passed:

- `bash -n codex-container.sh`.
- `git diff --check`.
- `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`: all
  43 tests passed, including 18 permanent-stall signal/mode combinations,
  seven invalid-identity/control-failure cases, successful bounded creation
  reconciliation, repeated mixed signals, the stopped-client regression, and
  the unreapable-client fault injection. Permanent-stall fixtures never receive
  a release; tests assert elapsed bounds, client disappearance, no application
  start or retry, full-ID-only removal, and private bookkeeping cleanup.
- `openspec validate bound-interrupted-container-creation --strict`.
- `openspec validate --specs --strict`: all five main specifications passed.

The outstanding item in `todo.md` is closed.
There were no skipped or unavailable checks in the requested synthetic and
real-engine suites. No actual engine hang, outage, uninterruptible process,
SIGKILL recovery, or new production image build is claimed.

### Archive disposition

On 2026-11-03, `bound-interrupted-container-creation` was synchronized and
archived at
`openspec/changes/archive/2026-11-03-bound-interrupted-container-creation/`
with all nine tasks complete. The `container-session` main specification gained
one requirement for bounded interrupted creation and updated its owned-cleanup
and session-documentation requirements. All added and modified requirement
blocks were compared with the delta, preserving unaffected requirements and
existing scenarios. Strict change validation, all five main specifications,
Bash syntax, and whitespace checks passed before archival.

## Common specification names: 2026-11-09

The OpenSpec capabilities were renamed to the scheme shared by the five wrappers (Wave 1, `sandbox-ref-2`). Requirements and scenarios are unchanged; only directory names and spec titles changed. Earlier sections and archived changes keep the names that were current at the time.

| Previous name | Current name |
| --- | --- |
| `container-image` | `runtime-image` |
| `podman-access` | `container-podman-access` |
| `runtime-filesystem` | `container-isolation` |

`openspec validate --specs` passed: 5 specs, 0 failures.
