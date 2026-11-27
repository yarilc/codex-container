# Repository Guidelines

## Project Structure & Module Organization

- `codex-container.sh` is the thin entry script, identical in every wrapper:
  it sources the shared launcher core `launcher/core.sh` with Codex's agent
  part `agent/launcher.sh` (profile values and three hooks: the `CODEX_YOLO`
  help, the `--yolo` approval bypass and the protected Codex arguments). The
  core owns argument parsing, mounts, user mapping, Podman checks and the
  session lifecycle; `docs/launcher-contract.md` in `sandbox-container` is its
  contract.
- `codex-container.ps1` is the thin Windows entry, identical in every
  wrapper: it runs the shared shim `launcher/windows/core.ps1`, which starts
  the managed installation inside a Podman machine's WSL distribution through
  `launcher/windows/bootstrap.sh`, and runs sessions and setup in the machine's
  systemd namespaces through `launcher/windows/enter.sh`. Windows supports
  every network mode that setup prepared; host Podman delegation was removed
  there as on Linux. See the README's Windows section.
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
  `smoke.py`), the `diagnostics.py` stderr filter and the operator toolchain
  library (`toolchains.py`, mounted read-only at `/toolchains`);
  `docs/setup.md` documents it.

## Shared and agent-specific files

`network/`, `setup/`, `launcher/` and the shared tests listed in
`tests/test_alignment.py` (`sandbox_profile.py`, `test_alignment.py`,
`test_launcher.py`, `fake_podman.py`, `test_setup.py`,
`test_agent_profile.py`, `test_network_policy.py`, `test_mux.py`,
`test_tls_client_hello.py`, `test_tls_proxy.py`, `test_platform.py`,
`test_qualification.py`, `test_guard.py`, `test_session.py`,
`test_network_feasibility.py`, `test_engine.py`, `test_toolchains.py`,
`test_windows_bootstrap.py`, `test_windows_enter.py`, `guard_terminal_probe.py`
and their fixtures) are copied unchanged from
`sandbox-container` at tag `sandbox-ref-36`. Never edit them here and never add an
agent identifier (`codex`, `openai`) to them: fix a defect in `sandbox-container`
first, then copy the files again and update the manifest in
`tests/test_reference_copy.py`. Codex values come only from `agent/`, the
entry scripts (`codex-container.sh`, and `codex-container.ps1`, the same text
in every wrapper under the wrapper's name), `Containerfile`, `.containerignore` and the per-agent tests
(`test_wrapper.py` for Codex's agent part only, `test_setup_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`,
`network_tls_fixture.py`, `test_setup_runtime.py`, `test_image_pins.py`,
`test_reference_copy.py`, `run-runtime.sh`). `tests/test_alignment.py` enforces
the identifier scan and wrapper/profile consistency;
`tests/test_reference_copy.py` enforces byte identity with the tag. The core
calls `network/session.py` (`prepare`, `start`, `agent-args`, `stop`) and never
re-implements the restricted lifecycle inline.

## Build, Test, and Development Commands

Run from the repository root:

```bash
bash ./codex-container.sh --container-setup  # Guided setup and managed launcher
export CODEX_CONTAINER_NETWORK=unrestricted   # direct launches: offline/provider/unrestricted
CODEX_CONTAINER_MAINTENANCE=1 ./codex-container.sh --container-build  # Build only, then exit
./codex-container.sh                    # Start in the current workspace
./codex-container.sh --container-shell # Open Bash in the runtime image
./codex-container.sh --container-help  # Show wrapper options
CODEX_CONTAINER_NETWORK=offline ./codex-container.sh --container-qualify  # Restricted gate
bash -n codex-container.sh launcher/core.sh agent/launcher.sh  # Check Bash syntax
git diff --check                       # Check whitespace
openspec validate --specs --strict      # Validate main specifications
bash ../sandbox-container/tools/shellcheck.sh .   # ShellCheck at warning level
bash ../sandbox-container/tools/powershell.sh .   # PSScriptAnalyzer and shim tests
```

Every tracked `*.sh` file, the shared `launcher/core.sh` and launcher fixtures
included, passes `tools/shellcheck.sh` of `sandbox-container` (pinned
ShellCheck, warning level). Codex's agent part `agent/launcher.sh` starts with
`# shellcheck shell=bash disable=SC2034,SC2154`, because the core reads its data
and defines the state its hooks read.

Every tracked `*.ps1` file passes `tools/powershell.sh` of `sandbox-container`
(pinned PSScriptAnalyzer, warning level), which also runs the shared shim tests
`tests/windows/shim_tests.ps1` against a fake `wsl.exe`. The thin entry and the
shim stay ASCII and run on Windows PowerShell 5.1 and PowerShell 7; Windows
PowerShell 5.1 itself is validated on a Windows host, as follow-up after
closure.

Host Linux rootless Podman is verified before image operations and startup,
independently of YOLO, shell mode, and explicit builds. Local Podman needs no
API service. Explicit absolute same-host Unix `CONTAINER_HOST` launch
connections verify that launch service, which never reaches the session; named,
TCP/SSH, implicit remote, and unverifiable contexts are rejected. All absolute
bind sources must refer to the same host; forwarded cross-host sockets are
unsupported. Host Podman delegation was removed: an exact
`CODEX_CONTAINER_PODMAN=1` stops every launch with migration guidance before
any engine query, and `CODEX_CONTAINER_PODMAN_SOCKET` is ignored.
Container-based tests use the session container engine instead: a private
rootless engine started with the session when the toolchain library holds image
toolchains (`launcher/engine/`, the `session-container-engine` capability).
Never mount a host Podman socket into a session or into the engine. The Podman
command stays installed as the engine's client; without an engine the session
has no `CONTAINER_HOST`.
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

The launcher behavior (launch engine verification, YOLO parsing, naming, signals,
creation recovery, cleanup, TTY handling, temporary storage, environment and
image freshness) lives in the shared core and is tested once by
`tests/test_launcher.py`; change it in `sandbox-container`, never here. In
short: a signal starts shutdown at once within one 20-second deadline,
`/tmp`, `/var/tmp`, `/run` and the shared-state home are `noexec` tmpfs mounts
(512/512/32/512 MiB), images carry a `build-inputs-hash` label and a stale image
is refused, and `--container-build` without Codex arguments builds and exits.
Codex declares no executable temporary storage.

Setup is the first step for new users. An unset or empty
`CODEX_CONTAINER_NETWORK` selects `provider`, Codex's default; without a
protected installation or the saved provider settings (profile, policy, runtime
directory, proxy image) the launch stops with `setup required:` guidance before
engine queries or state creation, and explicit empty overrides never restore a
saved mode. Restricted Codex launches add a protected
`--no-daemon -c sandbox_mode="danger-full-access"` because Codex's own sandbox cannot start
under the guard; never weaken the guard to make it work. Every image build,
including the automatic build of a missing image, requires the exact
`CODEX_CONTAINER_MAINTENANCE=1`. `offline` and `provider` require host
Python 3, a same-host Unix rootless
Netavark service with Podman >= 4.9, Landlock ABI >= 3, a protected
installation with the guard in `network/bin`, and a current qualification
report; they run the image by its immutable ID and never fall back to
unrestricted networking. Provider sessions add protected `-c` overrides for
optional traffic before the user's arguments and forward `OPENAI_API_KEY` only
for the `openai-api` and `openai-api-docs` profiles of the default policy. `CODEX_CONTAINER_STATE_DIR` selects an
isolated `/codex-home` and conflicts with a nonempty `CODEX_HOME`; host CA
trust is opt-in and mounts one bundle read-only at `/codex-home/ca/bundle.pem`.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quoted variables, and command arrays for
user-controlled arguments. Follow the script's four-space indentation. Prefer
small functions, actionable errors, lowercase `snake_case` local variables,
and uppercase environment/configuration variables. Write documentation,
comments, help, and messages in English.

## Change workflow and validation environments

A change is validated and closed in the environment where it is developed:
the session the work runs in. Once a change is applied, no task waits for
another environment or for the operator: not the WSL host outside the
session, a native Linux host, a Windows host, nor a real installation.

- **Before the change starts:** while exploring, proposing or designing, a
  spike may run on another environment to answer one specific question. The
  design records the question, the environment, the command and the result.
  A spike is never a task.
- **During the change:** run every check the session supports. A check the
  session cannot run, or one that fails because of the session's
  environment, is recorded in `docs/validation.md` as unavailable in the
  session, with its reason. It moves to the follow-up and does not block
  closure. A failure caused by the change is fixed in the change.
- **Test storage in a session:** `$HOME`, `/tmp` and `/var/tmp` are `noexec`
  there. Point `SANDBOX_TEST_TMPDIR` at a new directory on the workspace
  mount, and remove it afterwards, or tests with stubs fail for the
  session's reasons.
- **After closure:** runs on other environments are follow-up verification:
  runner modes on WSL and on the native Linux host, `tools/adoption-run.sh`,
  `tools/windows-validate.ps1` on Windows PowerShell 5.1, sessions opened on
  another host, and operator checks with real accounts. `tasks.md` lists
  them as plain bullets under "Follow-up after closure", never as
  checkboxes. `docs/validation.md` lists them as pending, then their
  results. A defect they find opens a new change.

`CLAUDE.md` imports this file for Claude Code and holds nothing else: edit
only `AGENTS.md`.

## Testing Guidelines

Tests use Python's standard-library `unittest`; there is no coverage threshold.
Every script change must
pass syntax and whitespace checks. Verify argument order and boundaries,
default/parent mounts, spaces, symlinks, and shell mode. With usable Podman,
check image build, Codex startup, isolated `CODEX_HOME` persistence, local Git
worktrees, and child-container bind mounts through the session container engine. Use disposable local repositories
and configuration; record unavailable checks separately from mock results.
Run `bash tests/run-runtime.sh --wrapper` for the shared launcher and wrapper suites in a runner
container (the agent sandbox mounts `/tmp` noexec and cannot bind Unix sockets
on its workspace), `--shared` for the copied shared suites and
`tests/test_reference_copy.py`, and `--network-policy`, `--mux`,
`--network-feasibility`, `--qualification`, `--guard`, `--network`, `--setup`
(shared `test_setup.py`) and `--setup-runtime` for the
real rootless acceptance modes. `--guard` and `--network` need the toolchain
image `localhost/codex-guard-toolchain:development`; see `network/README.md`.
Standard-library Python tests live in `tests/`. Run wrapper checks with
`python3 -B -m unittest discover -s tests -p test_launcher.py -v`,
`-p test_wrapper.py -v` and `test_image_pins.py`. Real runtime
checks require opt-in via `CODEX_RUNTIME_TESTS=1`, a built image, a same-host
rootless service, and private host-visible `CODEX_TEST_ROOT`, or use
`bash tests/run-runtime.sh` for disposable native Linux volume storage. Use a
pseudo-terminal for interactive checks and pipes/files for nonterminal checks.
Cover concurrent reservation, signals, owned cleanup, and exit 125. Record results and
limitations in `docs/validation.md`; do not treat skipped or synthetic tests
as real engine verification, and do not use actual Codex credentials in tests.
The session engine cases need `localhost/codex-cli-engine:latest` and the
pinned alpine sample image in the runner's engine; they skip, asking to prepare
an image, without them.
Where no terminal attaches to a `--read-only` container through the runner's
Podman client, because the engine gives it a read-only `/dev` (the runtime
image's Podman 4.3.1 against Podman 5.8 with crun 1.27), the guarded terminal
tests skip with the engine's error (`tests/guard_terminal_probe.py`). Record
them as unavailable there. After closure, as follow-up, record an interactive
session opened on that host with its own client: it is the evidence for the
`container-isolation` scenario "Terminal attaches on an engine that mounts /dev
read-only".

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

Treat Codex configuration and the host Podman socket as sensitive. Never
expose the host Podman API socket to a session. The session container engine
shares the session's network namespace, mounts only the workspace and the
library's read-only image store, holds no secrets, and keeps only its documented
hardening exceptions (design D4 of the reference's session engine change, and
the startup step that delegates the engine's own cgroup subtree, design D1 of
`support-nested-systemd-containers`); never widen them to make a nested tool
work. Only that startup step runs as the root of the engine's user namespace;
the launcher's commands in the engine run as its `podman` user. Disabled YOLO
does not override native flags or settings. Never embed
credentials or add `--privileged`. Preserve absolute workspace paths for child
bind mounts. Parent mounting is opt-in and exposes all contents read/write;
sensitive roots (`/`, system directories, `/tmp`, the physical home,
`/mnt/<letter>` and the Windows system and profile folders on those drives)
are refused unless exactly `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1`.
Do not broaden mounts beyond that documented behavior. Every session drops all
capabilities, sets no-new-privileges and has validated, inspected memory, CPU
and process budgets (`CODEX_CONTAINER_MEMORY_LIMIT`/`CPU_LIMIT`/`PIDS_LIMIT`,
defaults 4g/2/512) plus an optional `CODEX_CONTAINER_RUN_TIMEOUT`; never add
capabilities back or weaken a budget the engine can enforce to fix a tool. A
budget whose cgroup v2 controller the rootless engine does not delegate
(`Host.CgroupControllers`) is omitted, announced and bound into the
qualification identity; never require host changes to delegate it. Reported
controllers count as delegated only with the `systemd` cgroup manager
(`Host.CgroupManager`): a rootless `cgroupfs` engine reports controllers but
applies no limits, so it delegates none (`delegated()` in
`network/agent_budgets.py`, mirrored in `launcher/core.sh`). The process
budget alone falls back to a soft and hard process rlimit when the engine
kernel (`Host.Kernel`) is Linux 5.14 or later, which counts it per user
namespace; the mechanism (`cgroup`, `rlimit` or `none`) is one rule in
`network/agent_budgets.py` and `launcher/core.sh`, verified and qualified like
a cgroup budget. Each container's first process sets that limit: a fixed
`/bin/sh` step for the agent and the proxy, the startup program for the engine.
Never use `--ulimit nproc`: the engine applies it before it creates the
container's user namespace, so the kernel counts every container of the user
against it. Sessions
mask `/run/secrets` and `/dev/shm` with empty read-only tmpfs mounts and leave
`/dev` and its `devpts` to the engine (an explicit `devpts` gets
`ptmxmode=000`, so no pseudo-terminal can be opened); do not reintroduce
`--read-only-tmpfs=false` or a writable `/dev/shm`. The runtime recipe fetches
Debian packages over verified HTTPS only; the host CA reaches builds only as the
`build-ca` secret. Image inputs are pinned in
`Containerfile` and change only through the README update procedure.
