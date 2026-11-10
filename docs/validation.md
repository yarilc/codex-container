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

## Session hardening baseline (B01–B05): 2026-11-09

Change `harden-session-baseline` (Wave 2), ported from the `claude-container`
reference at tag `sandbox-ref-2`. Host: WSL2 x86_64, kernel
6.6.87.2-microsoft-standard-WSL2, rootless Podman 4.9.3 with cgroup v2. No
credentials or model requests were used.

Pre-change baseline with image `4a7d79663415` (Codex CLI 0.167.0, OpenSpec
1.16.0, unpinned): capability sets 0 except bounding `00000000800405fb`,
`NoNewPrivs` 0, `memory.max` `max`, `pids.max` 2048 (engine default),
`cpu.max` `max 100000`. Git, Bubblewrap, Codex's own Linux sandbox and the
delegated Podman client (rootless `podman info` and a child container) worked.

After the change, image `9f6940596ca5` built from the pinned recipe: base
`docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`
(the same digest as `sandbox-ref-2`), `codex --version` `codex-cli 0.167.0`,
`openspec --version` `1.16.0`.

| Check | Result |
| --- | --- |
| `tests/test_wrapper.py` | Initial run in a runner container: 13 failures. 12 came from an assertion expecting `--security-opt` as a separate argument; 1 from the existing root-prefix test, which launched from `/` and is now refused. The assertion was corrected and the prefix test sets the exact override. Rerun: passed, 52 tests |
| `tests/test_image_pins.py` | Passed: 2 tests, including mutated recipes (tag-only base, `@latest`, unversioned package, version range, missing package) |
| `bash tests/run-runtime.sh` | Passed on the first run: 14 tests |
| Effective hardening | All capability sets 0, `NoNewPrivs` 1, private cgroup namespace; `memory.max`, `pids.max` and `cpu.max` matched 4 GiB/512/2 CPUs and 1536 MiB/256/1.5 CPUs, with and without delegation; 80 children with a 32-process budget failed as expected |
| Tools under hardening | Codex's own Linux sandbox ran a command and denied a workspace write under its default read-only policy; Bubblewrap, Git, OpenSpec and a delegated child container worked. No capability was added |
| Lifetime | `CODEX_CONTAINER_RUN_TIMEOUT=3` stopped `sleep 60`; the client returned 255, the notice was printed and the owned container was removed. An early `exit 7` returned 7 without a notice |
| Refused workspace | A launch with the workspace equal to `HOME` exited 1 before any engine operation |
| `bash -n`, `git diff --check`, `openspec validate harden-session-baseline --strict` | Passed |

The unit suites were run in a container on the host (`--tmpfs /tmp:exec`)
because the agent sandbox mounts `/tmp` `noexec` and its v9fs workspace cannot
bind Unix sockets; both limitations belong to the test caller, not the wrapper.
Not covered by this change: Python budget normalization, setup questions and
qualification binding, which arrive with the Wave 3 network port.

## Network egress port (`add-network-egress`): 2026-11-09

Reference: `claude-container` tag `sandbox-ref-2` (commit
`56a6f03216c49c78426fc7e9ced96c9fecc12685`). Measurements use
`localhost/codex-cli:latest` with `codex-cli 0.167.0`, run with `--network=none`
and a disposable `CODEX_HOME`; no credentials and no model requests.

### OpenAI host inventory and authentication (task 2.1)

Sources: the official authentication page
(`https://developers.openai.com/codex/auth`, redirected to
`https://learn.chatgpt.com/docs/auth`, read 2026-11-09) and a static scan of the
URLs in the installed `@openai/codex` 0.167.0 Linux x86_64 binaries.

| Item | Result |
| --- | --- |
| API key | `OPENAI_API_KEY` (also `CODEX_API_KEY` in the binary); requests go to `https://api.openai.com/v1/responses` |
| ChatGPT sign-in | Browser callback on `localhost:1455` (unusable in the container); device code with `codex login --device-auth` (documented as beta; it must be enabled in the ChatGPT security settings or workspace permissions) |
| Account hosts (candidates) | `auth.openai.com` (`/oauth/token`, `/oauth/revoke`, `/api/accounts` with the `/deviceauth/usercode` and `/deviceauth/token` paths) and `chatgpt.com` (`/backend-api/codex` model requests with account credentials) |
| Optional hosts seen, not allowed | `ab.chatgpt.com` (OTLP metrics), `persistent.oaistatic.com`, `developers.openai.com`, `github.com`, `registry.npmjs.org`, CDNs and plugin/MCP sites |
| CA trust | `CODEX_CA_CERTIFICATE`, falling back to `SSL_CERT_FILE` (documented) |

The documentation lists no required hosts. The account hosts stay candidates,
marked unverified in the policy, until the operator-run sign-in, request and
refresh check.

### Optional-traffic controls (task 2.2)

Each key was written to a disposable `config.toml` and loaded with
`codex exec --strict-config`; Codex 0.167.0 rejects unknown keys with
`unknown configuration field` (checked with `bogus_key_xyz` and
`analytics.bogus`), and accepted every key below. The wrapper passes them as
`-c` overrides, which take precedence over the writable `config.toml`.

| Traffic | Control | Status |
| --- | --- | --- |
| Update check | `check_for_update_on_startup=false` | Supported |
| Analytics | `analytics.enabled=false` | Supported |
| Feedback upload | `feedback.enabled=false` | Supported |
| OTEL export | `otel.exporter="none"`, `otel.trace_exporter="none"`, `otel.metrics_exporter="none"` | Supported |
| Connectors and remote plugins | `features.apps=false`, `features.plugins=false`, `features.remote_plugin=false`, `features.plugin_discovery_prefetch=false` | Supported |
| Remote MCP servers configured by the user | None that removes entries from `config.toml` | Missing; the proxy denies them |
| Provider-hosted web search | `web_search="disabled"` is accepted but is not set: the search runs at the provider, outside the local boundary | Documented |

No environment variable controls these settings, so `--container-shell` gets
no overrides; any `codex` started from that shell is still limited by the guard
and the proxy.

### Protected `-c` precedence (task 5.5)

Measured with `codex features list` and `features.apps` (default `true`):
`-c features.apps=false` gives `false`; `-c features.apps=false -c
features.apps=true` gives `true` (the last `-c` wins); a `config.toml` setting
`apps = true` with `-c features.apps=false` gives `false`; `--enable apps` after
the override gives `true`. The protected overrides therefore beat the
agent-writable `config.toml`, while an operator `-c` or `--enable` placed after
them is an explicit operator choice and wins. A legacy `profile = "p"` key in
`config.toml` makes Codex refuse to load the configuration.

### Codex's own sandbox under the guard (task 2.3)

Measured through `codex-container.sh --container-shell` in `offline` mode, with
a disposable qualified installation, the production guard
(`abi3-seccomp-mux-v1`, ABI 3), no capabilities and no-new-privileges, in both
state modes:

| Path | Result |
| --- | --- |
| Default (`codex sandbox -- …`, Bubblewrap) | Fails before the command: `bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted` (the guard denies Netlink sockets) |
| `--enable use_legacy_landlock` | Fails before the command: `filesystem-restricted execution requires bubblewrap to isolate app-server sockets` |
| `bwrap --ro-bind / / --dev /dev true` directly | `Failed to make / slave: Operation not permitted` |

Neither inner path works, so design fallback 3 applies: in restricted modes
Codex runs with its own sandbox disabled (`--sandbox danger-full-access`,
`--yolo` or `CODEX_YOLO=1`) and the guard is the enforced boundary. The guard
was not changed. The baseline (unrestricted) measurement of 2026-11-09, where
Codex's sandbox works without the guard, still holds.
`test_codex_native_sandbox_fails_closed_under_the_guard` keeps this outcome as a
regression check.

### Executable temporary storage under the guard (task 2.4)

The guard validates that private `/tmp`, `/run` and `/var/tmp` are not host
binds; it does not require `noexec`. With Codex's layout (executable `/tmp` and
`/var/tmp` tmpfs, executable `/codex-home` tmpfs in shared mode or the bind of
`CODEX_CONTAINER_STATE_DIR` in isolated mode), the guard accepted the layout in
every restricted session of the runtime suites, and qualification passed in
both state modes. No shared file was changed.

### Shared copy and operator artifacts (tasks 1.1, 3.1–3.3, 4.1)

Environment: WSL2 `6.6.87.2-microsoft-standard-WSL2` x86_64, Landlock ABI 3,
Podman client 4.3.1 / server 4.9.3, Netavark, same-host Unix user service.

| Item | Result |
| --- | --- |
| Copy | `git archive sandbox-ref-2` of `network/`, `setup/diagnostics.py` and 21 shared tests; `diff -r` against the tag: no differences; 50 files in the `tests/test_reference_copy.py` manifest |
| `tests/test_reference_copy.py` | Passed: 5 tests, including an injected byte change, a missing and an extra file, and an injected `Codex` literal |
| `python3 -I network/agent_profile.py` queries | `CODEX_CONTAINER_NETWORK`, `io.codex-container.session` |
| Toolchain `localhost/codex-guard-toolchain:development` | Built from `network/guard-build.Containerfile`: ID `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`, the measured reference toolchain |
| Guard | SHA-256 `0c647dfea75667a46a8cd4cc4dfea4ee3d10363752ea7ce5957162bacd6d7ec9`, identical to the latest `claude-container` build |
| Proxy `localhost/codex-egress:local` | ID `13adbfafd7bdc49393c142ecb7ede21ae6e1a7e4c1d842b1518078cdb5590621` (base pulled by digest under maintenance) |
| Runtime image `localhost/codex-cli:latest` | ID `a7633287914e893f995c981968c8a76eac31e7b914b512554e25ca2f3fa01487`, `codex-cli 0.167.0`; `/opt/sandbox-egress/relay.py` and `mux.py` match `network/` by SHA-256 (mode `0777` from the build context, as in the reference image; the image root is read-only at runtime) |
| `tests/test_image_pins.py` | Passed: 3 tests, including an injected `CODEX_VERSION` divergence naming both versions |
| `bash tests/run-runtime.sh --shared` | Passed: 133 tests, 27 skipped (real-engine checks, run by the modes below) |
| `--network-policy` | Passed: 14 tests |
| `--mux` | Passed: 26 tests |
| `--network-feasibility` | Passed: 1 test |
| `--guard` | Passed: 19 tests, 1 skipped (the 305-second idle check), including the three guarded multiplex checks through the Codex `test_network_runtime.py` fixture |
| `--guard-idle` | Passed: 1 test (idle provider channel resumes after 305 seconds) |
| `--qualification` | Passed: 18 tests: installed offline and provider qualification, missing, stale and unsafe reports, cancelled gates, concurrent atomic reports and the fixed probe that cannot run an application |

### Wrapper integration (group 5)

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --wrapper` | Passed: 64 tests. The 52 existing tests passed unchanged after adding `CODEX_CONTAINER_NETWORK=unrestricted` and `CODEX_CONTAINER_MAINTENANCE=1`; 12 new tests cover missing and invalid modes, delegation rejection, the maintenance gate, proxy acquisition, isolated home privacy and escapes, CA modes, offline and provider order and arguments, protected overrides and the API key, failed qualification, interrupted helpers and the qualification entry points |
| `bash tests/run-runtime.sh` | Passed: 14 tests (unrestricted lifecycle, delegation, YOLO, budgets, workspace, build-context exclusion with the relay inputs) |

### Restricted runtime acceptance (group 6)

| Mode | Result |
| --- | --- |
| `--network` | Passed: 21 tests in both state modes: offline and provider hardening, delegation grid, real proxy with CONNECT/SNI binding and certificate verification, mismatched SNI and denied authorities, proxy death and exhaustion, budgets (64 verified TLS connections: `memory.peak` 41607168 of 268435456, `pids.current` 68 of 128), concurrent policies and owned cleanup, interrupted creation, readiness binding, arguments/stdin/status/TTY through the guard, bootstrap failure, Windows-path workspace, stalled proxy cleanup, CLI permission modes, the API key only for `openai-api`, tampered bootstrap, unsafe policy and missing proxy image |
| Codex through the relay | `codex exec` with a synthetic Responses API on `localhost.localdomain:8443` (custom provider, `wire_api="responses"`, CA via `CODEX_CONTAINER_TRUST_HOST_CA`): the Rust client used `HTTPS_PROXY`, loaded `SSL_CERT_FILE`, completed TLS 1.3 after a HelloRetryRequest, streamed the response, ran the fixture's shell tool call (Unix sockets denied inside the tool) and finished the turn |
| Fixture certificate | Codex's rustls verifier rejected the first fixture certificate, a self-signed CA (`CA:TRUE`) used as the server certificate, while curl and Python accepted it; the per-agent fixture now generates `CA:FALSE` with `serverAuth` |
| Optional traffic in shell mode | With no overrides, Codex at startup tried `chatgpt.com`, `github.com`, `api.github.com` (plugin sync) and `ab.chatgpt.com` (metrics); all were `policy-denied` |
| Concurrency (task 6.4) | Two concurrent Codex provider sessions (suite) while `claude-container`'s `test_concurrent_policies_and_signal_cleanup_are_owned` ran at the same time (passed, 1 test): distinct labels and resources; afterwards no `io.codex-container.*` container, network or volume remained |
| Residual containers | The first suite run, before the certificate fix, left two `io.codex-container.session` containers: the harness killed the wrapper with SIGKILL after its 45-second timeout, the documented case where owned cleanup cannot run. They were identified by label and test volume and removed |

### Authenticated checks (operator-run)

Unavailable: no real OpenAI credentials or model requests are used by the
automated suites. Before declaring a profile verified, the operator runs in
`provider` mode, with a qualified installation:

| Check | Profile | Status |
| --- | --- | --- |
| `codex login --device-auth`, then one request | `openai-account` | Unavailable (not run) |
| Token refresh after expiry with saved credentials | `openai-account` | Unavailable (not run) |
| Streaming request with `OPENAI_API_KEY` | `openai-api` | Unavailable (not run) |

Denials recorded during these checks (`denials.jsonl` in the session runtime
directory) revise the account inventory under a new policy revision; the
allowlist is never broadened with wildcards.

### Final verification (task 7.4)

| Check | Result |
| --- | --- |
| `bash -n codex-container.sh tests/run-runtime.sh` | Passed |
| ShellCheck (`koalaman/shellcheck:stable`) | Only SC2015, SC2054 and SC2329, the same informational classes as the previous wrapper |
| `bash tests/run-runtime.sh --wrapper` | 64 tests: one run had 1 failure in `test_lifetime_argument_and_notice`, which passed when rerun alone; this is the known whole-second `SECONDS` granularity of the lifetime notice, unchanged by this change and tracked separately |
| `--shared`, default runtime mode | Passed: 133 tests (27 skipped, run by the modes), 14 tests |
| All runtime modes | Passed; see the tables above |
| `openspec validate add-network-egress --strict` | Passed |
| `git diff --check` | Passed |
| markdownlint (`davidanson/markdownlint-cli2`) | Remaining findings are table and code lines over 80 columns and the existing duplicate "Archive disposition" headings, as in the previous documents |

## Guided setup and restricted sandbox override (`add-container-setup`): 2026-11-09

Reference: `claude-container` tag `sandbox-ref-2`. Environment as in the
network egress port above.

### `sandbox_mode` override (task 3.1)

Measured with `codex-cli 0.167.0`, a disposable `CODEX_HOME` and the startup
banner of `codex exec` (no credentials, no model request):

| Input | Effective sandbox |
| --- | --- |
| `config.toml` `sandbox_mode = "danger-full-access"` with `--strict-config` | `danger-full-access` (key and value accepted) |
| `config.toml` `sandbox_mode = "bogus"` | Rejected: ``unknown variant `bogus`, expected one of `read-only`, `workspace-write`, `danger-full-access` `` |
| `config.toml` `read-only` plus `-c sandbox_mode="danger-full-access"` | `danger-full-access` (the protected override beats the writable file) |
| `-c sandbox_mode="danger-full-access"` then `exec --sandbox workspace-write` | `workspace-write` (a later operator flag wins) |
| `-c sandbox_mode="danger-full-access"` then `-c sandbox_mode="read-only"` | `read-only` (the last `-c` wins) |

### Wrapper and shared setup suites (tasks 2.1–2.3, 3.2)

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --wrapper` | Passed: 66 tests, adding the setup entry point and help precedence, the diagnostics filter (restart line reclassified to `level=info`, real errors kept, status preserved, unchanged without the filter) and the restricted `sandbox_mode` override |
| `bash tests/run-runtime.sh --setup` (shared `test_setup.py`) | First run: 6 failures in `test_managed_real_wrapper_admits_saved_modes_and_preserves_network_overrides`, which expects the shared wrapper wording `cannot query Podman`; the Codex wrapper message was aligned (`cannot query Podman or invalid engine response; …`). Rerun: passed, 63 tests. No shared file changed |
| `test_alignment.py` | Passed: 9 tests (identifier scan, inventory, wrapper/profile consistency, helper calls, no inline lifecycle, neutral paths) |
| `tests/test_reference_copy.py` | Passed: 56 manifest entries, including `setup/` and the two new shared tests |

### Setup acceptance (tasks 4.1–4.2)

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests. Provider setup with CA trust, managed `--version` from a fresh environment through the guard (diagnostics filter applied), shell smoke, failed candidate update rolled back, offline rerun, relocated managed command, unrestricted setup and shell. Disposable `HOME`, installation and proxy image; no systemd change, credentials or model request |
| Provider setup transcript | Driven through a real pseudo-terminal with scripted answers (`tests/test_setup_runtime.py` harness), disposable `HOME`, account method, login declined. Observed: the residual-exfiltration notice naming `auth.openai.com`, `chatgpt.com` and `api.openai.com` with the required acknowledgement; the review of choices with protected profile `openai-account` and reused image IDs (runtime `a7633287…`, toolchain `0b69ba43…`, proxy `13adbfaf…`); the PATH note; the maintenance warning and authorization; guard packaging; `Sandbox qualification: locally-qualified`; `Sandbox: ready`; `Next authentication action: <command> login --device-auth`; `Authentication: pending` |
| Real systemd user-service activation, real login | Unavailable (not exercised) |

### Final verification (task 5.3)

| Check | Result |
| --- | --- |
| `bash -n`, ShellCheck | Passed; only the informational SC2015, SC2054 and SC2329 classes, as before |
| `--wrapper` | Passed: 67 tests |
| `--shared` (includes `test_alignment.py`, `test_reference_copy.py`) | Passed: 142 tests, 27 skipped (run by the modes) |
| `--setup` | Passed: 63 tests |
| `--setup-runtime` | Passed: 2 tests |
| `--qualification` | Passed: 18 tests |
| Default runtime mode | Passed: 14 tests |
| `--network` | Passed: 21 tests. The first full run had 1 failure: `test_guarded_arguments_stdin_status_and_tty_both_state_modes` expected the application argv without the new protected `sandbox_mode` override; the per-agent expectation was updated. The synthetic Responses API test now runs `codex exec` through the wrapper without `--sandbox`; the banner reports `sandbox: danger-full-access` and the tool writes its sentinel |
| `openspec validate add-container-setup --strict`, `git diff --check` | Passed |
| Parity row | Identical Codex row in this repository and in `claude-container/docs/network-contract.md` (uncommitted there until the archive step) |

## Adoption of `sandbox-ref-3`: 2026-11-10

The OpenCode port found that the shared guard test ran the agent with no
writable home. `claude-container` fixed `tests/test_guard.py` and tagged
`sandbox-ref-3` (commit `449ce60f956f0b51ff0e8818819c1377f7902a4d`). The test
is the only shared file that differs from `sandbox-ref-2`. It was copied here,
and the manifest, tag and commit in `tests/test_reference_copy.py` were
updated.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy`, with the sibling checkout at the tag | Passed: 5 tests |
| `bash tests/run-runtime.sh --shared` | Passed: 142 tests, 27 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 19 tests, 1 skipped |

## Adoption of `sandbox-ref-4`: 2026-11-10

`claude-container` tag `sandbox-ref-4` (commit
`49a871b6bee21926112c547bc3a97562c933e6bd`) differs from `sandbox-ref-3` only
in `tests/test_setup.py`, which now supports API-key-only profiles (OpenCode).
The Codex profile's first method is the `account` login method, so its checks
are unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy`, with the sibling checkout at the tag | Passed: 5 tests |
| `bash tests/run-runtime.sh --shared` | Passed: 142 tests, 27 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |

## Adoption of `sandbox-ref-5`: 2026-11-10

`claude-container` tag `sandbox-ref-5` (commit
`3388b6ee45a1b9943f8f4aed77c0b1740a9ab4f8`) adds two parent-directory
creations to `tests/test_setup.py`, for nested configuration homes such as
OpenCode's `.config/opencode`. Codex's `.codex` is unaffected.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy` | Passed: 5 tests |
| `bash tests/run-runtime.sh --shared` | Passed: 142 tests, 27 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |

## Adoption of `sandbox-ref-6`: 2026-11-10

`claude-container` `sandbox-ref-6` (commit `3150bfe`) adds the optional profile
field `install.files`: setup installs the declared agent files, the
qualification identity binds them, and the shared qualification test
installation copies them with `Containerfile` and `.containerignore`. This
repository declares none, so its installation is unchanged. The changed shared
files are copied unchanged and `tests/test_reference_copy.py` moves to the
tag. The first Codex qualification run had one transient failure in `test_concurrent_gates_publish_complete_atomic_reports`; two reruns passed.

| Check | Result |
| --- | --- |
| `--shared` (includes `test_reference_copy.py`) | Passed: 143 tests, 27 skipped (run by the modes) |
| `--setup` | Passed: 63 tests |
| `--qualification` | Passed: 18 tests |
