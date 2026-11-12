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
- `docs/network-contract.md` records the network mode contract, the shared
  reference and the intentional per-agent differences.
- `agent/profile.json` is the single source of Codex-specific values used by
  shared code; `agent/policies/default.json` holds the OpenAI provider profiles.
- `network/` holds the shared restricted-session implementation (guard, proxy,
  relay, policy, platform checks, qualification and the `session.py` helper);
  `setup/` holds the shared guided setup (`setup.py`, `common.py`, `launch.py`,
  `smoke.py`) and the `diagnostics.py` stderr filter; `docs/setup.md` documents
  it.

## Shared and agent-specific files

`network/`, `setup/` and the shared tests listed in `tests/test_alignment.py`
(`sandbox_profile.py`, `test_alignment.py`, `test_setup.py`,
`test_agent_profile.py`, `test_network_policy.py`, `test_mux.py`,
`test_tls_client_hello.py`, `test_tls_proxy.py`, `test_platform.py`,
`test_qualification.py`, `test_guard.py`, `test_session.py`,
`test_network_feasibility.py` and their fixtures) are copied unchanged from
`claude-container` at tag `sandbox-ref-12`. Never edit them here and never add an
agent identifier (`codex`, `openai`) to them: fix a defect in `claude-container`
first, then copy the files again and update the manifest in
`tests/test_reference_copy.py`. Codex values come only from `agent/`, the
wrapper, `Containerfile`, `.containerignore` and the per-agent tests
(`test_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`,
`network_tls_fixture.py`, `test_setup_runtime.py`, `test_image_pins.py`,
`test_reference_copy.py`, `run-runtime.sh`). `tests/test_alignment.py` enforces
the identifier scan and wrapper/profile consistency;
`tests/test_reference_copy.py` enforces byte identity with the tag. The wrapper
calls `network/session.py` (`prepare`, `start`, `agent-args`, `stop`) and never
re-implements the restricted lifecycle inline.

## Build, Test, and Development Commands

Run from the repository root:

```bash
bash ./codex-container.sh --container-setup  # Guided setup and managed launcher
export CODEX_CONTAINER_NETWORK=unrestricted   # direct launches: offline/provider/unrestricted
CODEX_CONTAINER_MAINTENANCE=1 ./codex-container.sh --container-build  # Build, then start
./codex-container.sh                    # Start in the current workspace
./codex-container.sh --container-shell # Open Bash in the runtime image
./codex-container.sh --container-help  # Show wrapper options
CODEX_CONTAINER_NETWORK=offline ./codex-container.sh --container-qualify  # Restricted gate
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

Reject Unix launch paths consisting only of slash characters before any Podman
query. Preserve response boundaries during verification: accept one launch
record or two delegated-socket records with zero or one final LF, rejecting
extra blank/nonblank records and CR characters before image operations.
Preserve the complete delegated host path, including spaces, and keep query
errors as failures even if their output looks valid. Normalize CODEX_YOLO
words case-insensitively: 1/true/yes enable, unset/empty/0/false/no disable,
and other values (including padded words) fail. Shell mode validates the value
without adding Codex arguments. The exact Podman opt-in and native arguments
remain independent.

Sessions reserve directory/index names atomically with create, using both
running and stopped names. Parse one to nine decimal digits in base ten,
propagate listing errors, and retry only confirmed collisions, at most 20 times.
Track the created full ID and use it exclusively for signals and cleanup;
never replace an existing container or clean up by a reusable name. Preserve
application exit statuses including 125. Forward TERM/INT/HUP and return
143/130/129 for wrapper interruptions. Reconcile pending creation before
cleanup: allow five seconds for completion, then TERM with five seconds before
KILL and one further second to observe client termination. Recover the full ID
from the private CID record after cancellation; without verified ownership
report unresolved creation and require explicit engine inspection. Cancellation
does not prove the engine request stopped. Preserve the first interruption
status and never renew deadlines for repeated signals. Report an unreapable
client's PID instead of waiting indefinitely. Interrupted creation has up to
17 seconds of separate phase budgets, excluding scheduling overhead.
Bound graceful shutdown to five seconds and engine control calls to five
seconds plus a one-second kill allowance. Local client cancellation allows
five seconds after TERM plus one second after KILL. Report cleanup failures
without overriding the primary status.
SIGKILL and engine loss can leave residual containers.
Allocate a TTY only when stdin and stdout are terminals, retaining redirected
stdin and EOF. `/tmp` and `/var/tmp` are capped at 512 MiB each and `/run` at
32 MiB, preserving permissions and executable temporary locations. These are per-mount maxima,
not reserved memory or a container memory limit; ephemeral home has no explicit
capacity. Build automatically only for image-existence status 1;
other inspection errors stop startup. The default-deny `.containerignore`
permits only the root Containerfile as an application input; future local
COPY/ADD sources need deliberate inclusion.

Setup is the first step for new users. Every ordinary launch requires a
nonempty `CODEX_CONTAINER_NETWORK`, explicit or from the managed launcher; an
unset or empty mode stops with `setup required:` guidance before engine queries
or state creation. Restricted Codex launches add a protected
`-c sandbox_mode="danger-full-access"` because Codex's own sandbox cannot start
under the guard; never weaken the guard to make it work. Every image build,
including the automatic build of a missing image, requires the exact
`CODEX_CONTAINER_MAINTENANCE=1`. `offline` and `provider` reject
`CODEX_CONTAINER_PODMAN=1`, require host Python 3, a same-host Unix rootless
Netavark service with Podman >= 4.9, Landlock ABI >= 3, a protected
installation with the guard in `network/bin`, and a current qualification
report; they run the image by its immutable ID and never fall back to
unrestricted networking. Provider sessions add protected `-c` overrides for
optional traffic before the user's arguments and forward `OPENAI_API_KEY` only
for the exact `openai-api` profile. `CODEX_CONTAINER_STATE_DIR` selects an
isolated `/codex-home` and conflicts with a nonempty `CODEX_HOME`; host CA
trust is opt-in and mounts one bundle read-only at `/codex-home/ca/bundle.pem`.

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
Run `bash tests/run-runtime.sh --wrapper` for the wrapper suite in a runner
container (the agent sandbox mounts `/tmp` noexec and cannot bind Unix sockets
on its workspace), `--shared` for the copied shared suites and
`tests/test_reference_copy.py`, and `--network-policy`, `--mux`,
`--network-feasibility`, `--qualification`, `--guard`, `--network`, `--setup`
(shared `test_setup.py`) and `--setup-runtime` for the
real rootless acceptance modes. `--guard` and `--network` need the toolchain
image `localhost/codex-guard-toolchain:development`; see `network/README.md`.
Standard-library Python tests live in `tests/`. Run wrapper checks with
`python3 -B -m unittest discover -s tests -p test_wrapper.py -v` and `test_image_pins.py`. Real runtime
checks require opt-in via `CODEX_RUNTIME_TESTS=1`, a built image, a same-host
rootless service, and private host-visible `CODEX_TEST_ROOT`, or use
`bash tests/run-runtime.sh` for disposable native Linux volume storage. Use a
pseudo-terminal for interactive checks and pipes/files for nonterminal checks.
Cover concurrent reservation, signals, owned cleanup, and exit 125. Record results and
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
bind mounts. Parent mounting is opt-in and exposes all contents read/write;
sensitive roots (`/`, system directories, `/tmp`, the physical home and
`/mnt/<letter>`) are refused unless exactly `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1`.
Do not broaden mounts beyond that documented behavior. Every session drops all
capabilities, sets no-new-privileges and has validated, inspected memory, CPU
and process budgets (`CODEX_CONTAINER_MEMORY_LIMIT`/`CPU_LIMIT`/`PIDS_LIMIT`,
defaults 4g/2/512) plus an optional `CODEX_CONTAINER_RUN_TIMEOUT`; never add
capabilities back or weaken a budget the engine can enforce to fix a tool. A
budget whose cgroup v2 controller the rootless engine does not delegate
(`Host.CgroupControllers`) is omitted, announced and bound into the
qualification identity; never require host changes to delegate it. Sessions
mask `/run/secrets` and `/dev/shm` with empty read-only tmpfs mounts and leave
`/dev` and its `devpts` to the engine (an explicit `devpts` gets
`ptmxmode=000`, so no pseudo-terminal can be opened); do not reintroduce
`--read-only-tmpfs=false` or a writable `/dev/shm`. The runtime recipe fetches
Debian packages over verified HTTPS only; the host CA reaches builds only as the
`build-ca` secret. Image inputs are pinned in
`Containerfile` and change only through the README update procedure.
