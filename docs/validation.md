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

## Adoption of `sandbox-ref-7`: 2026-11-10

`claude-container` `sandbox-ref-7` (commit `d52a031`) adds the optional profile
field `install.runtime_build`. With `wrapper`, setup builds the runtime image
through the installed wrapper's build-only `--container-build`; the default
`recipe` keeps the direct `podman build`. This repository declares nothing, so
its setup is unchanged. The changed shared files are copied unchanged and
`tests/test_reference_copy.py` moves to the tag.

| Check | Result |
| --- | --- |
| `--shared` (includes `test_reference_copy.py`) | Passed: 144 tests, 27 skipped (run by the modes) |
| `--setup` | Passed: 64 tests |
| `--qualification` | Passed: 18 tests |

## Adoption of `sandbox-ref-8`: 2026-11-10

`claude-container` `sandbox-ref-8` (commit `12cffab`) changes only the shared
`tests/test_setup.py`: the runtime build test patches the dispatch point
`build_runtime`, so it also holds for profiles that build through the wrapper.

| Check | Result |
| --- | --- |
| `--shared` (includes `test_reference_copy.py`) | Passed: 144 tests, 27 skipped (run by the modes) |
| `--setup` | Passed: 64 tests |

## Adoption of `sandbox-ref-9`: 2026-11-10

`claude-container` tag `sandbox-ref-9` (commit `8b191e5`) lets an account method
declare empty `login_args`, so setup can offer sign-in inside the interactive
agent (needed by Antigravity, whose CLI has no login command). The changed
shared files `network/agent_profile.py`, `setup/setup.py`,
`tests/test_agent_profile.py` and `tests/test_setup.py` were copied unchanged;
the `tests/test_reference_copy.py` manifest moved to the tag. This profile is
unaffected: its methods keep their current setup behavior.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --shared` | Passed: 145 tests, 27 skipped (run by the modes) |
| `bash tests/run-runtime.sh --setup` | Passed: 65 tests |

## OpenAI documentation MCP extension profiles (`add-openai-docs-profile`): 2026-11-10

An operator test in provider mode showed the OpenAI documentation MCP server
(`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`)
failing with `error sending request for url
(https://developers.openai.com/mcp?source=codex)`: the host is in no profile,
so the proxy denied it. The operator chose to allow it explicitly. Base
profiles are exact in the shared policy code, so the host is in two new
extension profiles, `openai-api-docs` and `openai-account-docs`, under policy
revision `openai-2026-11-10-v1`.

The same test showed `Running without the shared background server:
command-line configuration overrides (-c, --enable, --disable, or --search)
requires embedded mode.` This is expected: the protected `-c` overrides select
embedded mode, and the shared background server needs a Unix listener that the
guard denies. It is now documented in the README.

### Measurement (Codex 0.167.0, logging CONNECT proxy, dummy key)

| Check | Result |
| --- | --- |
| MCP client and `HTTPS_PROXY` | Honored: every MCP connection used the proxy |
| CONNECT authorities for the MCP server | Only `developers.openai.com:443` (5 tunnels for `codex mcp list` plus `codex exec`; 2 for `codex mcp list` alone) |
| Other hosts seen, denied, not needed by the MCP | `api.openai.com` (model, dummy key), `chatgpt.com`, `github.com`, `api.github.com` |
| Real check through the production proxy (`SANDBOX_EXTERNAL_TESTS=1`, no credentials) | `openai-account-docs`: `codex mcp list` reached the server (auth status `Unsupported`, no denial). `openai-account`: auth status `Unknown` and a sanitized `policy-denied` entry for `developers.openai.com` |

### Verification

| Check | Result |
| --- | --- |
| Policy against the profile rules, `--network-policy`, `test_agent_profile` | Passed (14 policy tests) |
| `--wrapper` | Passed: 68 tests, including key forwarding for every `api` profile and the help text |
| `--shared` | Passed: 145 tests, 27 skipped |
| `--network` targeted: controlled `-docs` profiles bind and deny correctly | Passed: 2 tests (documentation host allowed only under `-docs`; `mcp.example.com` and `ab.chatgpt.com` still denied) |
| ShellCheck | 11 findings, all present before this change; none new |
| `--network` (full) | Passed: 23 tests, 1 skipped (the opt-in real MCP check, run separately above) |
| markdownlint | Only MD013 on table rows, as in the existing tables |
| `openspec validate add-openai-docs-profile --strict`, `git diff --check` | Valid, clean |

## Quiet restricted defaults (`quiet-codex-defaults`): 2026-11-11

The operator asked for a quiet, useful default restricted session. Restricted
launches now pass a protected `--no-daemon` before the protected `-c`
overrides, and `openai-account` includes `developers.openai.com:443` for the
OpenAI documentation MCP. `openai-account-docs` is removed; `openai-api` and
`openai-api-docs` are unchanged. Policy revision `openai-2026-11-11-v1`;
existing provider installations requalify once.

### Measurement (Codex 0.167.0, PTY, `--network=none`, dummy key)

| Check | Result |
| --- | --- |
| TUI with the protected `-c` overrides, without `--no-daemon` | F2 panel: `Warnings · 1 of 1 · Startup: Running without the shared background server…` |
| Same, with `--no-daemon` | F2 panel: `No warnings` |
| `--no-daemon` before `exec`, `login --help`, `mcp list` | Accepted (exit 0) |
| Offline TUI through the qualified wrapper (disposable state, synthetic `auth.json`) | Codex started; F2 panel `No warnings`; no notice in the output |
| `codex mcp list` through the wrapper (offline) | Exit 0, no notice |

### Verification

| Check | Result |
| --- | --- |
| `--wrapper` | Passed: 68 tests (`--no-daemon` first protected argument, absent in shell and `unrestricted`; key forwarding per policy `authentication`) |
| `--shared` | Passed: 145 tests, 27 skipped |
| `--network-policy` | Passed: 14 tests |
| `--network` with `SANDBOX_EXTERNAL_TESTS=1` | Passed: 23 tests. Real check: `openai-account` reached the documentation MCP (auth status `Unsupported`, no denial); `openai-api` denied `developers.openai.com` (`policy-denied`) |
| `bash -n`, ShellCheck | Clean syntax; same findings as before the change, none new |
| markdownlint, `git diff --check` | Only MD013 on table rows, as in the existing tables; clean |
| `openspec validate quiet-codex-defaults --strict` | Valid |

A repeated `--network` run under load once failed the lifetime test
(`test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy`, exit 255
without the lifetime notice); it passed in the full runs before and after.

## Adoption of `sandbox-ref-10`: 2026-11-11

Copied from `claude-container` tag `sandbox-ref-10` (commit `0f6585f`):

- `network/agent_profile.py`, `setup/common.py`, `setup/setup.py`;
- `tests/test_agent_profile.py`, `tests/test_setup.py`.

The `tests/test_reference_copy.py` manifest moved to the tag. Codex has no
shared directories, so the profile keeps the default
`native.private_shared_dirs: false`. A failed setup smoke launch now shows the
wrapper's sanitized stderr.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --shared` | Passed: 146 tests, 27 skipped (run by the modes) |
| `bash tests/run-runtime.sh --setup` | Passed: 68 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --wrapper` | 68 tests; 66 passed. `test_permanently_stalled_creation_signal_matrix` failed in 2 subtests on `elapsed > 3` (2.6 to 2.9 s), also when run alone and on `main` without this adoption. The wrapper and `test_wrapper.py` are unchanged; this is recorded as an environment timing issue after the host crash, not a regression |

A first run of all wrappers' suites was interrupted by a host crash. Its
leftover test containers were removed before this run.

## Operator authenticated session: 2026-11-11

The operator ran an authenticated Codex session in provider mode with the
setup-default profile `openai-account`. In the TUI, they asked the model to confirm
that it could use the harness tools and to report the sandbox's access limits.
The model did both, and the operator found the result correct.

Earlier the same day, after the documentation-MCP change, the operator had already confirmed that Codex works with authentication. That confirmation was not recorded at the time, and this section records it.

This covers an authenticated model request with tool use through the sandbox.
Token refresh and the `openai-api` key checks remain pending. Full profile verification under the readiness checklist is not
claimed. The checklist also covers streaming and long-lived requests,
WebSockets, sign-in, token reuse and refresh, CA behavior and shell mode.

## Adoption of `sandbox-ref-11` and lab-host fixes (`adopt-lab-host-fixes`): 2026-11-11

Copied from `claude-container` tag `sandbox-ref-11` (commit `d17e865`):

- `network/.containerignore`, `network/README.md`, `network/agent_budgets.py`;
- `network/control.py`, `network/guard-build.Containerfile`, `network/guard.c`;
- `network/proxy.py`, `network/proxy_hardening.py`;
- `network/qualification_peer.py`, `network/qualification_probe.py`,
  `network/qualification_records.py`, `network/qualification_runtime.py`;
- `network/qualify.py`, `network/session.py`;
- `setup/setup.py`, `setup/smoke.py`;
- `tests/test_guard.py`, `tests/test_network_policy.py`,
  `tests/test_qualification.py`, `tests/test_session.py`, `tests/test_setup.py`.

The `tests/test_reference_copy.py` manifest moved to the tag.

The same change ports the reference's lab-host launcher and recipe
adaptations to Codex:

- the `unix://` host socket path from Podman 5 is reduced to its path;
- each budget is requested only when the engine reports its cgroup
  controller. An unenforced budget gets a notice, and the created
  configuration must carry every enforced budget and no unenforced one;
- `/run/secrets` is masked with an empty read-only tmpfs;
- `--read-only-tmpfs=false` is replaced by a `noexec` 64 MiB `/dev`,
  `devpts` and an empty read-only `/dev/shm`. Codex `/tmp`, `/var/tmp` and
  `/run` are unchanged;
- the opted-in host CA is passed to both build paths as the `build-ca`
  secret, and `.containerignore` admits `podman-build-secret*`;
- Debian packages are fetched over verified HTTPS, bootstrapped from the
  base image's Node.js roots.

The wrapper test fixture now copies `network/agent_budgets.py` and answers the
controller query. Without that fixture, 21 wrapper tests fail on the shared
files alone.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 348 tests, 68 skipped. `test_permanently_stalled_creation_signal_matrix` failed once on timing (`stall-owned`, SIGHUP) and passed twice when rerun; this is the known timing-sensitive test |
| `python3 -m unittest discover -s tests -p test_wrapper.py` | Passed: 74 tests, 1 skipped. New cases: Podman 5 socket URL and invalid `unix://` values; every subset of delegated controllers, with arguments, notices and inspection; unverifiable controller lists rejected before state creation; unenforced budget present or enforced budget missing; device and secrets mounts in every unrestricted mode, offline and provider; proxy secrets mask and budgets; build secret with and without trust, for `--container-build` and for a missing image |
| `python3 -m unittest tests.test_image_pins` | Passed: 6 tests. New checks: HTTPS-only Debian sources, no disabled verification, an optional `build-ca` secret, bootstrap removal, and the toolchain recipe |
| `bash tests/run-runtime.sh --shared` | Passed: 158 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 26 tests. Uses `localhost/codex-guard-toolchain:development` (`215f5ffc1023`), built from the copied recipe |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped (the 305-second idle check, `--guard-idle`) |
| `bash tests/run-runtime.sh --network` | Passed: 23 tests, 1 skipped (`developers.openai.com`, external) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 14 tests. Includes the tmpfs capacities and execution, and Bubblewrap and `codex sandbox` without capabilities under the new `/dev` |
| Runtime image `localhost/codex-cli:adopt-ref-11` | Built with the wrapper's build arguments (`podman build --tag ... --file Containerfile .`), because this session has no host-visible private state for a wrapper run. Image `8ae054805108`. Debian sources `https://`, no `/tmp/apt-bootstrap-ca.pem`, `ca-certificates` installed, `codex-cli 0.167.0`, OpenSpec `1.16.0` |
| `bash -n codex-container.sh`, `git diff --check`, `openspec validate adopt-lab-host-fixes --strict` | Passed, clean, valid |
| Parity table | SHA-256 `893682205ada6457060a60b3a7cacc48ec8fbc8c78db8422a38344846047cf86`, identical to claude-container |
| Operator `--container-setup` (refresh approved) and a session on this host, the Rocky Linux 9 lab host and the newer WSL host | Pending: the operator runs them after the push |

Every restricted installation must rebuild and rerun setup or qualification.
The qualification identity, the shared code digests and the runtime image
identity all change.

### Image working directory fix (`adopt-lab-host-fixes`, tasks 7.x): 2026-11-12

The operator's `--container-setup` on the Rocky Linux 9 lab host, on the
adoption above, failed in the qualification gate with
`chowning container ... workdir to container root: potentially insufficient
UIDs or GIDs available in user namespace (requested 31600276:31600276 for
.../merged/workspace)`. The cause is in the recipe:

- `WORKDIR /workspace` was the recipe's last step before `ENTRYPOINT`, so the
  directory was in no image layer;
- the shared gate containers pass no `--workdir`, so Podman created the
  directory at every start and chowned it;
- under `--userns=keep-id`, that chown fails for the operator's domain UID.

The fix creates `/workspace` in the package step
(`mkdir -p /codex-home /workspace`). `tests/test_image_pins.py` now rejects a
`WORKDIR` that no earlier `RUN` step creates.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_image_pins` | Passed: 7 tests, including the new workdir check and its mutated recipe |
| Runtime image `localhost/codex-cli:adopt-ref-11` rebuilt | Image `1ba1ef985c20`. `podman export` of a fresh container lists `workspace/` (root, 755, build time 07:10). A `--userns=keep-id` container without `--workdir`, started at 07:12, shows the unchanged build time, so the engine did not create the directory |
| `bash tests/run-runtime.sh --qualification` with that image | Passed: 26 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) with that image | Passed: 14 tests |
| Operator `--container-setup` on the Rocky Linux 9 lab host | Passed (operator-reported, 2026-11-12): setup completed on the image with the fix, and the operator's own tests on that host passed |

Follow-up, not in this change: the shared gate containers in
`network/qualify.py` should pass `--workdir /`, so they never depend on an
image workdir. This needs a claude-container change and tag `sandbox-ref-12`.

## Adoption of `sandbox-ref-12`: 2026-11-12

Copied from `claude-container` tag `sandbox-ref-12` (commit `fd196c9`): `network/qualification_records.py`, `network/qualify.py`, `tests/test_qualification.py`, `tests/test_setup.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

The gate containers and the security-identity probe now pass `--workdir /`.
The shared runtime-build test pins `runtime_build: recipe`. Codex already
creates `/workspace` in its image, so no observed behavior changes. The
shared code digests change, so restricted installations rerun qualification.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 350 tests, 68 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 159 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 27 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped (the 305-second idle check) |
| `bash tests/run-runtime.sh --network` | Passed: 23 tests, 1 skipped (`developers.openai.com`, external) |
| Runtime image used | `localhost/codex-cli:adopt-ref-11` (`1ba1ef985c20`), the current recipe |
| Operator `--container-setup` on the hosts in use | Pending |

## Engine-provided `/dev` for pseudo-terminals: 2026-11-12

Change `use-engine-dev-for-pseudo-terminals`, launcher only, as in the Claude
reference (claude-container `docs/validation.md`, same title). No shared file
changes.

Codex and shell containers no longer mount their own `/dev` tmpfs or
`devpts`. The explicit `devpts` from `sandbox-ref-11` took the kernel
defaults `mode=600,ptmxmode=000`, so no process in a session could open a
pseudo-terminal ("out of pty devices"). The terminal itself attached,
because the engine allocates the console outside that `devpts`. The engine's
`devpts` is `mode=620,ptmxmode=666`. On Podman 5, `/dev` is now the engine's
writable tmpfs without `noexec`. Codex's `/tmp` and `/var/tmp` were already
executable. The requirement "Terminal-compatible device mounts" is replaced
by "Engine-provided device mounts allow pseudo-terminals".

| Check | Result |
| --- | --- |
| Codex image `localhost/codex-cli:adopt-ref-11` (`1ba1ef985c20`) with the previous `/dev` arguments | `pty.openpty()`: "out of pty devices" |
| `test_pseudo_terminals_and_device_masks` (new) with the previous launcher | Failed: "out of pty devices" |
| `test_pseudo_terminals_and_device_masks` with the fix | Passed |
| `tests/test_wrapper.py` | Passed: 74 tests, 1 skipped. With the previous launcher, the updated assertions fail (15 failures) |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 351 tests, 69 skipped (the runtime tests are opt-in) |
| `bash tests/run-runtime.sh` (`test_runtime.py`, image `1ba1ef985c20`) | Passed: 15 tests, including `test_pseudo_terminals_and_device_masks`, `test_tmpfs_capacities_execution_and_exhaustion` and `test_tools_and_codex_sandbox_without_capabilities` |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-12) on all three hosts |

Qualification digests the launcher, so restricted installations rerun
`--container-setup`. The runtime image is unchanged.

## Adoption of `sandbox-ref-14` and the toolchain library (`adopt-sandbox-ref-14`): 2026-11-13

Copied from `claude-container` tag `sandbox-ref-14` (commit `f06c885`):
`network/agent_profile.py`, `network/control.py`,
`network/qualification_records.py`, `setup/common.py`,
`tests/test_alignment.py`, `tests/test_qualification.py`,
`setup/toolchains.py`, `tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

Wrapper port of the reference toolchain library (claude-container
`add-toolchain-library`, commit `e45957f`):
- `--container-toolchain add|list|remove|verify`, dispatched before the
  network mode;
- `CODEX_CONTAINER_TOOLCHAINS` and `CODEX_CONTAINER_TOOLCHAINS_DIR`;
- the read-only `/toolchains` mount (`ro,nosuid,nodev`), with
  `--mount-target /toolchains` in restricted modes;
- default toolchain `PATH` entries appended after the image `PATH`.

The README has a "Toolchains" section with the `AGENTS.md` instruction line;
the example recipes are linked in claude-container.

The first apply of this change adopted `sandbox-ref-13`. It was discarded
before any commit: with that tag the shared `QualificationRuntime` fixture did
not install `setup/`, and six `--qualification` tests failed. The reference
fixed it in `sandbox-ref-14`. The wrapper port was carried over unchanged as a
patch.

`tests/run-runtime.sh` now mounts a private executable tmpfs at
`/sandbox-test-tmp` as `SANDBOX_TEST_TMPDIR`, and `tests/test_wrapper.py`
creates its fixtures there. Before, `--wrapper` failed (291 failures) because
the image's world-writable `/tmp` is refused as an ancestor of the toolchain
library.

Fixture adaptations required by the new mount:
- `tests/test_wrapper.py`:
  - fixtures use a synthetic `HOME`;
  - the root and home-workspace cases set `CODEX_CONTAINER_TOOLCHAINS=0`, or
    expect the overlap stop;
  - the volume list includes the library;
  - the `readlink` resolver case omits the library.
- `tests/test_runtime.py`: `test_real_worktrees` exposes a parent without the
  synthetic home, and the nested caller passes `HOME`.

| Check | Result |
| --- | --- |
| New `tests/test_wrapper.py` cases with the previous launcher | Failed as intended (dispatch, mount, private creation, unsafe library, disabled mount, appended `PATH`, restricted `--mount-target`, home workspace overlap) |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_toolchains` (private tmpfs) | Passed |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 382 tests, 72 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 160 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | Passed: 24 tests, 1 skipped, including a toolchain added on the host during an offline session, which became usable without direct network |
| `bash tests/run-runtime.sh --wrapper` | Passed: 80 tests (291 failures before the runner change) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests, including archive and image sources, a failing check, the read-only mount, the image's `node` and `python3` kept first, and the omitted mount |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-14`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host, `java -version` with the Temurin 21 toolchain, and `--container-toolchain verify java21` | Passed (operator-reported, 2026-11-13); `main` pushed |

Runtime image: `localhost/codex-cli:setup-930356c8…` (the Containerfile is
unchanged). Qualification digests the launcher and `setup/toolchains.py`, so
restricted installations rerun `--container-setup`.

## Adoption of `sandbox-ref-16`: 2026-11-14

Copied from `claude-container` tag `sandbox-ref-16` (commit `1fa091e`):
`setup/toolchains.py`, `tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

- `sandbox-ref-15` protects every `XDG_` variable from toolchains, both in
  `add` and in `launch-env`. Codex sets none, but the shared rule applies to
  every wrapper.
- `sandbox-ref-16` makes a comment agent-neutral.

The README "Protected variables" bullet now names `XDG_` variables. The
launcher and the wrapper tests are unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_toolchains` (private tmpfs) | Passed |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 383 tests, 72 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 160 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 80 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-16`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-14); `main` pushed |

Runtime image: `localhost/codex-cli:setup-930356c8…`. `setup/toolchains.py`
is qualified code, so restricted installations rerun `--container-setup`.

## Adoption of `sandbox-ref-17`: 2026-11-14

Copied from `claude-container` tag `sandbox-ref-17` (commit `a23f155`):
`setup/toolchains.py`, `tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

`sandbox-ref-17` splits the protected toolchain variables into two groups:

- **Neutral:** the same in every wrapper, now including
  `DBUS_SESSION_BUS_ADDRESS`. `add` rejects them, and `launch-env` fails on
  them.
- **Profile:** Codex's own prefix, configuration, approval and credential
  variables. `add` rejects them. When another wrapper's toolchain in the
  shared index sets one, `launch-env` leaves it out of the session and prints
  one warning naming the toolchain.

The README "Protected variables" bullet describes both groups. The launcher
reads only the standard output of `launch-env`, and the warnings go to
standard error, so the launcher and the wrapper tests are unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_toolchains` (private tmpfs) | Passed: 38 tests, 1 skipped |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 385 tests, 72 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 160 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 80 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests. The first run in the sequence stopped without output during `test_concurrent_reservation_with_stopped_container` (exit 1, no failure reported); a rerun on its own passed |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-17`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-14); `main` pushed |

Runtime image: `localhost/codex-cli:setup-930356c8…`. `setup/toolchains.py`
is qualified code, so restricted installations rerun `--container-setup`.

## Adoption of `sandbox-ref-18`: 2026-11-15

Copied from `claude-container` tag `sandbox-ref-18` (commit `958465b`):
`network/agent_profile.py`, `setup/common.py`, `setup/toolchains.py`,
`tests/test_agent_profile.py`, `tests/test_alignment.py`, `tests/test_setup.py`,
`tests/test_toolchains.py`.
The `tests/test_reference_copy.py` manifest moved to the tag.

`sandbox-ref-18` adds the optional profile field `native.protected_env`, runs
the toolchain check in `/`, refuses an isolated state directory that overlaps
the workspace on managed launches, and makes the alignment test check the
launcher's code and its help text separately. No Codex fixture needed
adapting.

Codex changes, from the cross-wrapper review of 2026-11-14:

- **Agent variables:** `agent/profile.json` declares `CODEX_` and `OPENAI_`.
  A default toolchain could previously set `OPENAI_BASE_URL` in Codex
  sessions; `launch-env` now leaves it out with a warning.
- **Name collisions (M2):** after a failed create without an ID, an existing
  container with the candidate name is a collision only when its session
  label differs. This session's own container is reported as the creation
  failure and removed in cleanup, instead of being left behind while the
  wrapper tried the next name.
- **Label recovery (M2):** when creation was interrupted or failed without a
  published ID, cleanup looks up the session label (`ps --all --no-trunc
  --filter label=…`), confirms exactly one ID by inspecting its label, and
  removes it. A failed lookup, several IDs or an unconfirmed label keep the
  "Creation outcome unresolved" report.
- **State inside the workspace (M3):** direct launches refuse a
  `CODEX_CONTAINER_STATE_DIR` that is, contains or lies inside the workspace
  (the parent in worktree mode), before any engine call. The usage text and
  the README document it.

The fake engine in `tests/test_wrapper.py` now answers the session-label
lookup and label inspection. The new tests (`test_toolchain_cannot_set_codex_variables`,
`test_owned_name_is_not_a_collision`, `test_interrupted_creation_is_recovered_by_label`,
`test_state_overlapping_the_workspace_fails_without_engine`) fail on `main`
and pass on the branch.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 393 tests, 73 skipped |
| `bash tests/run-runtime.sh --shared` | Passed: 161 tests, 28 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 72 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` (not in the tool's checklist; shared `setup/` modules are qualified code) | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 84 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests |
| Five-wrapper parity table | Identical to claude-container's (`sandbox-ref-18`) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (2026-11-15, reported by the operator after the push) |

Runtime image: setup image `04133a4bc2e7`
(`localhost/codex-cli:setup-930356c8…`), tagged `localhost/codex-cli:latest`
only for the runs and untagged by name afterwards. Shared qualified code
changes, so restricted installations rerun `--container-setup`.

## Adoption of `sandbox-ref-20`: 2026-11-16

`sandbox-container` is now the reference (it replaced `claude-container`).
Copied from `sandbox-container` tag `sandbox-ref-20` (commit `d4fd4ca`) with
`tools/propagate.py`: `network/README.md`, `network/agent_profile.py`,
`network/policy.py`, `network/qualification_records.py`, `network/qualify.py`,
`network/session.py`, `setup/common.py`, `setup/setup.py`, `setup/toolchains.py`,
`tests/sandbox_profile.py`, `tests/test_agent_profile.py`, `tests/test_alignment.py`,
`tests/test_guard.py`, `tests/test_qualification.py`, `tests/test_session.py`,
`tests/test_setup.py` and the fixture profiles in `tests/fixtures/`. The
`tests/test_reference_copy.py` manifest moved to the tag and names
`sandbox-container` as its sibling. Per-agent: `tests/test_setup_wrapper.py`
(copied from Claude), the lifetime notice measured with `EPOCHREALTIME` plus a
boundary test (failed with the old launcher), documents pointing at
`sandbox-container`, parity table fixed by hand.

Runtime image: `localhost/codex-cli:setup-12c915b01d424f1391f37bdda7c344a7`
(`04133a4bc2e7`); WSL2 6.6.87.2, Podman 4.9.3. The host crashed during the first
run; the suite was rerun from the start.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 411 tests, 71 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 66 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | 24 tests, 1 skipped: `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy` failed once (lifetime notice missing after a real 4 s expiry, status 255); passed in 2 of 2 isolated reruns. Recorded as a timing flake of the real-expiry notice |
| `bash tests/run-runtime.sh --network-policy` | Passed: 15 tests |
| `bash tests/run-runtime.sh --network-feasibility` | Passed: 1 test |
| `bash tests/run-runtime.sh --wrapper` | Passed: 85 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests |
| `git diff --check`, `bash -n codex-container.sh` | Passed |
| Operator `--container-setup` on the three hosts (`sandbox-ref-21`) | Passed (operator, 2026-11-16) |

## Lifetime notice clock (2026-11-16)

The real-expiry lifetime notice was intermittently missing: about one run in ten
of `test_session_lifetime_limit_and_early_exit` in `antigravity-container`, and
once in the Codex `--network` suite, with exit status 255 but no notice. Bash
`EPOCHREALTIME` follows the wall clock, and WSL2 steps it backwards to
resynchronise with the host: in 30 raw `podman create --timeout 3` plus
`podman start --attach` runs, the monotonic clock always measured at least
3.9 s, while the wall clock measured 2.15 s once (a 1.84 s backward step).

The launcher now measures the session from just before `podman create` with
`/proc/uptime` (monotonic, centiseconds since boot), falling back to `SECONDS`
only if `/proc/uptime` cannot be read. The threshold is unchanged: the notice
appears when a failing session has lasted at least the limit.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_wrapper -k lifetime -k boundary -k timeout` (disposable container), 5 runs | Passed 5 of 5 |
| `antigravity-container`: `bash tests/run-runtime.sh -k test_session_lifetime_limit_and_early_exit`, 10 runs | Passed 10 of 10 (before the fix: failed 2 of 10) |
| `bash -n` on the launcher | Passed |

No installed code, image or profile changes: installations need no new setup.

## Adoption of `sandbox-ref-21`: 2026-11-16

Copied from `sandbox-container` tag `sandbox-ref-21` (commit `4b25eae`) with
`tools/propagate.py`: `tests/sandbox_profile.py`, `tests/test_guard.py`. The
`tests/test_reference_copy.py` manifest moved to the tag; parity table fixed by
hand. The shared guard runtime test now mounts the image's own native home
(`AGENT_HOME`) instead of the fixture profile's home.

Runtime image: `localhost/codex-cli:setup-12c915b01d424f1391f37bdda7c344a7`; WSL2 6.6.87.2, Podman 4.9.3.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 411 tests, 71 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `git diff --check` | Passed |
| Operator `--container-setup` on the three hosts (`sandbox-ref-21`) | Passed (operator, 2026-11-16) |

Only shared test files changed: installations need no new setup for this tag.

## Adoption of `sandbox-ref-23` and `sandbox-ref-24`: 2026-11-17

Change `adopt-sandbox-ref-23`. Copied with `tools/propagate.py` from
`sandbox-container` tag `sandbox-ref-23` (commit `7d14706`): `launcher/core.sh`,
`tests/test_launcher.py`, `tests/fake_podman.py`,
`tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh`,
`network/README.md`, `network/agent_profile.py`, `network/control.py`,
`network/qualification_records.py`, `network/qualify.py`, `setup/common.py`,
`setup/launch.py`, `setup/setup.py`, `tests/fixtures/agent/profile.json`,
`tests/sandbox_profile.py`, `tests/test_agent_profile.py`,
`tests/test_alignment.py`, `tests/test_network_policy.py`,
`tests/test_qualification.py`, `tests/test_setup.py`. Then from tag
`sandbox-ref-24` (commit `dd5d82e`): `launcher/core.sh`, `tests/test_launcher.py`.
The `tests/test_reference_copy.py` manifest moved to `sandbox-ref-24`, with
`launcher/` as a closed shared directory; the parity table was fixed by hand.

- **Launcher:** `codex-container.sh` is the reference's thin entry script;
  `agent/launcher.sh` holds Codex's profile values, `AGENT_CREDENTIALS`
  (`openai-api` and `openai-api-docs` with `OPENAI_API_KEY`, `openai-account`
  without) and three hooks: `agent_command_args` (protected
  `--no-daemon -c sandbox_mode="danger-full-access"` in restricted sessions and
  the ten provider-only `-c` overrides), `agent_approval_bypass` (`--yolo`) and
  `agent_help` (documents `CODEX_YOLO` and `OPENAI_API_KEY`).
- **Reference defect, fixed as `sandbox-ref-24`:** an inaccessible state
  directory stopped with a raw `cd: ...: Permission denied` (change
  `fix-inaccessible-state-diagnostic` in `sandbox-container`).
- **Temporary storage (design decision 3):** Codex declares no executable
  temporary storage. With the rebuilt image, shell sessions with shared,
  isolated and read-only state ran `codex --version`, `codex exec --help`,
  `codex login status` (not logged in) and a failing `codex exec`; Codex wrote
  no executable under `/tmp`, `/var/tmp`, `/run` or the home outside `.codex`
  (only Node's compile cache in `/tmp`, data files, and the image's own
  `/codex-home/.npm` copied into the tmpfs). With read-only state Codex warns
  that it cannot create its PATH aliases in `.codex` and proceeds; that is a
  read-only state limit, not `noexec`. The real network suite's actual Codex
  shell tool (synthetic Responses API) passed with `noexec` temporary storage.
- **`/run` (user, 2026-11-17: visible change):** the old launcher mounted `/run`
  with mode 1777; the core, like the reference and Claude (contract L7), does
  not, so the session user cannot write there. Two runtime cases that wrote to
  `/run` now assert that it is not writable.

Old tests gate (design decision 4): the `sandbox-ref-21` `tests/test_wrapper.py`
(85 cases) ran against the new entry script and core, with only its harness
adapted (the fake engine answers the `build-inputs-hash` label and the core's
one-line socket query; synthetic installations copy the core, the agent part
and the build inputs; the controlled `readlink` resolver answers only socket
paths; the isolated-home privacy case expects the core's wording). Against
`sandbox-ref-23`: 54 passed, 31 failed, with one lost behavior. Against
`sandbox-ref-24`: 57 passed, 28 failed, the same failing subtests minus
`test_inaccessible_state`; no lost behavior remains.

| Old case | Outcome | Maps to |
| --- | --- | --- |
| `test_api_key_follows_the_policy_authentication_method` | visible change | U10 (source inspection of the old launcher; rewritten in tests/test_wrapper.py) |
| `test_unreapable_client_reports_without_waiting` | visible change | source inspection of the old helper; the core reports "local client ... did not terminate within the deadline" (U9) |
| `test_verification_normal_terminators_and_socket_spaces` (build=True only) | visible change | U3/U16 build-only: no session after `--container-build` |
| `test_all_names_decimal_bounds_and_listing_error` | visible change | wording ("cannot list Podman containers") |
| `test_application_status_and_cleanup_failure` | visible change | wording; status preserved (U9 cleanup report "cleanup rm failed or timed out") |
| `test_budget_mismatch_and_inspection_failure_stop_before_start` | visible change | equivalent removal arguments (`rm --force --time 0 --ignore <id>`); start still refused |
| `test_creation_and_collision_query_failures` (exists=125) | visible change | phase 6: collisions confirmed by ownership label, not `container exists`; create diagnostics kept |
| `test_device_and_secret_mounts_in_every_unrestricted_mode` | visible change | U7 noexec tmpfs |
| `test_existing_state_relative_symlink_and_spaces` (relative path) | visible change | M14: CODEX_HOME must be absolute |
| `test_explicit_build_and_image_override` | visible change | U8/U12 build arguments (`--pull=never --format docker --label build-inputs-hash`) |
| `test_help_documents_hardening` | visible change | help text from the core (line break inside "drops all capabilities") |
| `test_help_documents_modes_migration_and_provider_limits` | visible change | U1: no migration text |
| `test_setup_entry_point_is_dedicated_and_help_takes_precedence` | visible change | U1 help text |
| `test_image_and_build_status_matrix` | visible change | U3 build-only inspects the image; a failed image inspection exits 1 with a diagnostic instead of the engine status (user, 2026-11-17: visible change) |
| `test_maintenance_gates_every_build` | visible change | same as above |
| `test_inaccessible_state` (mode=0) | lost behavior, fixed in `sandbox-ref-24` | against `sandbox-ref-23` the core stopped with a raw `cd: ...: Permission denied`; fixed in the reference by `fix-inaccessible-state-diagnostic` (`sandbox-ref-24`, shared case `test_inaccessible_state_and_ignored_permissions`); passes on `sandbox-ref-24` |
| `test_interrupted_creation_invalid_identity_and_control_failures` | visible change | wording of the core's cleanup reports (validated CID record, U9) |
| `test_interrupted_creation_is_recovered_by_label` | visible change | wording of the core's cleanup reports |
| `test_invalid_state_before_image_operations` | visible change | U16 build-only does not create or check state |
| `test_missing_mode_stops_before_engine_state_and_other_checks` | visible change | U1 provider default (to verify at adoption: verified) |
| `test_mode_and_delegation_rejections_precede_engine` | visible change | phase 1-2 union: setup guidance before mode-specific settings |
| `test_non_enforcing_modes_controlled_fixture` | visible change | wording ("use native Linux storage if permissions are not enforced") |
| `test_offline_order_arguments_and_status` | visible change | U8 label inspection adds one image query; qualification check after the name listing, before create |
| `test_permanently_stalled_creation_signal_matrix` | visible change | U9 immediate shutdown |
| `test_permissions_independent_and_exact_opt_in` | visible change | phase 5 union: `--unsetenv CONTAINER_CONNECTION` always; U14 shell receives its arguments |
| `test_provider_order_protected_overrides_and_api_key` | visible change | U7 noexec tmpfs; protected overrides and key otherwise as before |
| `test_socket_fallbacks_and_symlink` (default path) | visible change | fixture limit: the core checks the default socket before resolving it; the message names /run/user/<uid>/podman/podman.sock, the expected fallback |
| `test_stubborn_application_and_stalled_cleanup_are_bounded` | visible change | U9 rewrite; wording |
| `test_tmpfs_capacities_and_options` | visible change | U7/L7 noexec, /run noexec |

The other "to verify at adoption" cases passed against the core. The hook
cases (`test_yolo_case_insensitive_and_delegation_independent`,
`test_permissions_independent_and_exact_opt_in`,
`test_unrestricted_codex_keeps_its_own_sandbox`) and the Codex-only protected
arguments and API key are rewritten in the reduced `tests/test_wrapper.py`.

Environment: WSL2 6.6.87.2, Podman server 4.9.3 (client 4.3.1); image rebuilt
through the build-only path: `localhost/codex-cli:latest` `f96d5e50eef8`,
`build-inputs-hash`
`b57f58660850a52dce9c832e0dcaa2cc2d7b92b4a3f768a861a499a9eeb0d3af`.

| Check | Result |
| --- | --- |
| `--container-build` alone (real engine, maintenance) | Passed: built, labeled, no session container |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 450 tests, 72 skipped |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment` (host Python, siblings present) | Passed: 22 tests |
| Mutated `agent/launcher.sh` (no bypass flag, no `--no-daemon`, one provider override and the `openai-api-docs` credential removed), `tests.test_wrapper` | Failed as expected: 22 failures; restored |
| `bash tests/run-runtime.sh --wrapper` | Passed: 118 tests (`test_launcher.py`, `test_wrapper.py`) |
| `bash tests/run-runtime.sh --shared` | Passed: 287 tests, 29 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 29 tests |
| `bash tests/run-runtime.sh --network` | Passed: 24 tests, 1 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | First run failed: 2 tests wrote to `/run`; after the `/run` update passed: 17 tests |
| `git diff --check`, `bash -n` on the entry script, core and agent part | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator, 2026-11-17) |

The installed and qualified code changes (entry script, core, agent part):
installations rerun `--container-setup`.

## Adoption of `sandbox-ref-25`: 2026-11-18

Change `adopt-sandbox-ref-25`. Copied from `sandbox-container` tag `sandbox-ref-25`
(commit `6bed770`): `launcher/core.sh`, `setup/setup.py`, `tests/test_launcher.py`,
`tests/test_setup.py`. The `tests/test_reference_copy.py` manifest moved to the
tag; the parity rows were checked by hand.

With delegation enabled, the launcher and guided setup now refuse a reported host
socket path made only of slashes, and one that exists in the wrapper's namespace
as a non-socket (change `verify-delegated-socket-path` in `sandbox-container`). A
path the wrapper cannot see is still accepted as the remapped socket of a
containerized wrapper. No Codex file changed; the Codex tests ran unchanged. The
`network-egress` scenario for `--container-qualify` without a mode now states the
provider default.

Environment: WSL2 6.6.87.2, Podman server 4.9.3; image `localhost/codex-cli:latest`
`23c66b6f1bf8`, rebuilt through the build-only path (`build-inputs-hash`
`b57f58660850a52dce9c832e0dcaa2cc2d7b92b4a3f768a861a499a9eeb0d3af`, unchanged).

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_reference_copy tests.test_alignment` (host Python, siblings present) | Passed: 22 tests, no skips |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 451 tests, 72 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 119 tests |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests |
| `git diff --check` | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator, 2026-11-18) |

The installed launcher core and setup change: installations rerun `--container-setup`.

## Codex 0.169.0 and OpenSpec 2.0.0 image pins (2026-11-18)

The change `pin-codex-0-169-0` uses the newest stable npm releases at least
72 hours old at the 2026-11-18 freeze. Codex 0.169.0 was published on November 13
and OpenSpec 2.0.0 on November 11. Codex 0.169.1 and 0.170.0 were still within
the 72-hour window. The base remains
`node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`.

| Image | Image ID | Reported Codex | Reported OpenSpec |
| --- | --- | --- | --- |
| Baseline | `23c66b6f1bf838d378db421693480058ab6b987dddcb78d0a444c0ac0ccfb732` | 0.167.0 | 1.16.0 |
| Updated | `7c185bec05cea191b92dca0a374c49c69b3d2abdd70a15b28294f27074dca11b` | 0.169.0 | 2.0.0 |

The maintenance build fetched Debian packages over HTTPS. Its build-inputs
hash is `cb457cf0ca22ae4419f38e5ab91ec4229d0deede6e390d4d886f85d3267d25eb`.
The updated image reports Node.js 22.23.4 and Python 3.11.2. Validation used
WSL2 6.6.87.2 x86_64, Podman client 4.3.1, rootless server 4.9.3 and Netavark.

### Endpoint inventory and native controls

The offline scan compared literal HTTPS URLs in the installed Linux x64
`codex`, `codex-code-mode-host` and `codex-voice-host` binaries. It also found
the same API-key names, CA environment variables, OAuth exchange and revocation
paths, device-code paths, and Responses API and ChatGPT route fragments.

| Host | Comparison with 0.167.0 |
| --- | --- |
| `api.openai.com` | Retained the Responses API route. The synthetic provider test exercised it with a dummy key. |
| `auth.openai.com` | Retained the OAuth and device-code routes. Both versions attempted only this host for `login --device-auth` through a reject-all loopback proxy with external networking disabled. |
| `chatgpt.com` | Retained `/backend-api/codex` for account requests. |
| `developers.openai.com` | Retained documentation URLs. The user-configured MCP server used this host through the production proxy. |
| `auth.api.openai.org`, `api.openai.org` | Additional staging references for identity and the decisions service in the tagged sources. |
| `codex-cloud-backend.chatgpt.com`, `codex-portals.api.openai.com` | Additional references for Cloud and the TCP tunnel feature in the tagged sources. |
| Other references | Both binaries reference `ab.chatgpt.com` and `persistent.oaistatic.com`. New literals include `registry.npmjs.org` and `rootnet.in`. |

The required hosts for `openai-api`, `openai-account` and `openai-api-docs`
match the previous inventory. The policy revision is `openai-2026-11-11-v1`.
The staging and feature classifications come from the
[tagged upstream sources](https://github.com/openai/codex/tree/rust-v0.169.0).

Codex accepted `--no-daemon`, `-c sandbox_mode="danger-full-access"`, and
`--yolo`. `exec --strict-config` rejected an unknown key. In both state modes
under the production guard, the Bubblewrap path failed to create the Netlink
route socket (exit 1). The legacy Landlock path required Bubblewrap (exit 101).
Both paths stopped before starting their commands.

### Documentation MCP and workspace trust

In a locally qualified session with the shipped `openai-api-docs` profile,
`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`
wrote user-level configuration under a disposable `CODEX_HOME`. The real
server reported `enabled` and auth status `Unsupported` in `codex mcp list`,
matching the 0.167.0 measurement on the same profile.

The controlled provider fixture used the same destination set with local TLS
endpoints for the documentation MCP and Responses API. The workspace was
explicitly untrusted and had a project-level MCP entry for `mcp.example.com`.
The user-level server appeared in `mcp list`. `codex exec --strict-config`
initialized it and requested `tools/list` without `--trust`, then completed a
synthetic shell-tool exchange under the guard. The project entry generated no
CONNECT attempt. A separate explicit probe of `mcp.example.com:443` was denied.

| Invocation | Logged CONNECT attempts |
| --- | --- |
| `codex mcp list` | `developers.openai.com:443` (2) |
| `codex exec` | `api.openai.com:443` (9), `developers.openai.com:443` (1) |

The runs used a dummy API key and disposable configuration. The synthetic
Responses exchange stayed within the fixture.

### Offline OpenSpec round trip

OpenSpec 1.16.0 populated `.config/openspec/config.json` in disposable isolated
state. OpenSpec 2.0.0 read the same profile in the qualified offline shell with
guard `abi3-seccomp-mux-v1`. The temporary project passed `init --tools none`,
`new change`, `validate --all --strict --json`, and `list --json`. The
temporary change used `skip_specs: true`. The configuration files and their
checksums matched before and after.

### Acceptance checks

Both recipes passed the seven pin tests. Credential-free unit discovery ran
451 cases with the same 72 skips and matching case-by-case results on both
images. The reference-copy test verified byte identity with `sandbox-ref-25`
using the sibling checkout.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --wrapper` | Passed all 119 tests. |
| `bash tests/run-runtime.sh --shared` | Ran 288 cases with 29 skips. The separate unit discovery covered the reference checkout comparison. |
| `bash tests/run-runtime.sh --setup` | Passed all 67 tests. |
| `bash tests/run-runtime.sh --setup-runtime` | Passed both tests. |
| `bash tests/run-runtime.sh` | Passed all 17 default runtime tests. |
| `bash tests/run-runtime.sh --qualification` | Passed all 29 tests. |
| `SANDBOX_EXTERNAL_TESTS=1 bash tests/run-runtime.sh --network` | 23 passed in the full run. The remaining live MCP test passed on an isolated rerun. |
| `bash tests/run-runtime.sh --guard` | Ran 20 cases with the opt-in idle check skipped. All other cases passed. |
| `bash tests/run-runtime.sh --guard-idle` | Passed. The guarded provider channel resumed after 305 seconds of inactivity. |
| `bash tests/run-runtime.sh --network-feasibility` | Passed the topology harness, including its expected unguarded Unix socket control. |
| `bash tests/run-runtime.sh --network-policy` | Passed all 15 tests. |
| `bash tests/run-runtime.sh --mux` | Passed all 26 tests. |

The full network run recorded one `tls-malformed` diagnostic for
`developers.openai.com`, which triggered the live MCP assertion under
`openai-account`. The rerun passed with auth status `Unsupported` in
`openai-account` and `policy-denied` in `openai-api`. Three additional
`mcp list` probes on each version returned `Unsupported` under the account
profile with clean host diagnostics. An unauthenticated MCP `initialize`
request returned a server identity and protocol version through the production
proxy on both images.

The guard suites used the prepared toolchain image
`a33a4e7a708555af127d04f788dc341decf4402077064deb64bb345720365654`.

`bash ../sandbox-container/tools/shellcheck.sh .` produced identical output
before and after. Its 98 existing findings comprise one SC2148, one SC2154 and
25 SC2034 findings in the agent launcher, plus 71 in the shared core and
fixtures. `git diff --check` and strict change validation passed. The local
OpenSpec 1.16.0 and the image's OpenSpec 2.0.0 both validated the change.
