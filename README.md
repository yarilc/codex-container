# Codex CLI in Podman

`codex-container.sh` runs Codex CLI in a rootless Podman container. The
image filesystem is read-only, with writable workspace, Codex state, and
temporary storage. A launch runs in one network mode: `provider` (the
default; only the OpenAI hosts of one protected profile), `offline` or
`unrestricted` (ordinary networking); see [Network modes](#network-modes). Sessions never
receive the host Podman API. For container-based tests and builds, add the
images they need as toolchains: sessions then get a private container engine
of their own ([Container tests](#container-tests)).

## Enable rootless Podman on the host

Run this setup on the Linux host (or inside your Linux/WSL distribution),
using the same non-root account that will run `codex-container.sh`.
Install Podman and its rootless dependencies using your distribution's
[installation instructions](https://podman.io/docs/installation).
The account needs subordinate UID/GID ranges in `/etc/subuid` and
`/etc/subgid`, the `newuidmap`/`newgidmap` helpers, and a rootless networking
backend supported by the installed Podman version. If these are missing,
complete the administrator steps in the
[rootless setup guide](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md)
before continuing.

Check that local rootless Podman works:

```bash
podman info --format '{{.Host.Security.Rootless}}'
podman run --rm docker.io/library/alpine:latest id
```

The first command must print `true`; the second must successfully start a
container. Root inside that container is normal for rootless Podman.

The wrapper always verifies the launch engine before image inspection, builds,
or startup, including shell mode. It requires explicit Linux/rootless
information and a recognized `Host.ServiceIsRemote` boolean. Failed queries and
unverifiable results stop startup. Local Podman requires no API service. An
explicit absolute Unix `CONTAINER_HOST` is supported for a service on the same
host, including callers inside another container; launch verification then
queries that service, which never reaches the session. Named connections through
`CONTAINER_CONNECTION`, TCP/SSH endpoints (including the Podman machine
connection that `podman.exe` uses), and implicit remote contexts are rejected.
On Windows, the PowerShell entry runs the sandbox inside the Podman machine
instead; see [Windows with Podman machine](#windows-with-podman-machine).
Forwarded Unix sockets to other hosts are unsupported: Unix transport alone
does not prove that the service is on the same physical host.

Unix launch endpoints must contain an absolute socket path beyond `/`.
`unix://`, `unix:///`, and longer slash-only forms such as `unix:////` are
rejected before any Podman query. Valid absolute paths are preserved as supplied.

Verification preserves record boundaries: the launch response has one record,
which can omit its final LF or end in exactly one LF. Additional blank or
nonblank records and CR characters are rejected before image operations or
startup. A failed query remains an error even if its output looks valid.

## Enable the launch service

Restricted networking (`provider` and `offline`) requires a same-host Unix
launch service. An unrestricted local session needs no API service. Host Podman
is always required to build and launch the Codex container. The launch service
serves the wrapper only: no session ever receives a host Podman socket. Choose
**one** of the following service setup methods.

### With a systemd user session

From a normal login session for your account, enable socket activation:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket --no-pager
```

Systemd creates the socket and its parent directory, and starts the API
service when a client connects. An inactive `podman.service` between requests
is normal. To keep the user service available after logout and start it at
boot, optionally enable lingering:

```bash
sudo loginctl enable-linger "$(id -un)"
```

If `systemctl --user` reports that it cannot connect to the bus, ensure you
are logged in directly as the intended user with a working systemd user
session. On systems without systemd, use the manual procedure below.

### Without systemd: create the directories and start the service

An error such as
`bind: no such file or directory` when creating the socket means that a
parent directory is missing. The socket file itself is created by Podman;
do not create it with `touch`.

In a terminal on the host, prepare the runtime directory. On systems without
a login manager, `/run/user/<uid>` may also be absent; creating it under
`/run` usually requires administrator privileges:

```bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$XDG_RUNTIME_DIR"
fi
ls -ld "$XDG_RUNTIME_DIR"
```

The directory must belong to your account and have mode `0700`
(`drwx------`). If an existing directory has incorrect ownership or
permissions, have the administrator correct it before continuing. Then run
the following as your normal user:

```bash
install -d -m 0700 "$XDG_RUNTIME_DIR/podman"
podman system service --time=0 "unix://$XDG_RUNTIME_DIR/podman/podman.sock"
```

Leave this terminal open and use a second terminal for the checks and wrapper
commands below. The service runs in the foreground; Ctrl+C stops it.
Repeat this setup after reboot because `/run` is temporary. Export the same
`XDG_RUNTIME_DIR` in any other terminal used to run local Podman if your
session does not set it automatically. Run the service and wrapper without
`sudo` so they use your rootless containers and configuration.

### Verify the launch service

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${CONTAINER_HOST#unix://}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info --format '{{.Host.Security.Rootless}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true`. A socket file alone does not prove that a service is listening or that
its engine is rootless.
If the API command fails, check socket permissions, the systemd status, or
the foreground service output above. If it prints `false` or another
unexpected result, verify that the service was started as the intended
non-root user, without `sudo`, and repeat the rootless service setup above.
Workspace, state and build context must be available to the service at their
host absolute paths.

See also the official
[Podman API service documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

## Usage

### First run: guided setup

New users start with guided setup, after completing the rootless host setup
above, from a reviewed checkout and an interactive terminal:

```bash
bash ./codex-container.sh --container-setup
```

Setup asks for the network mode (default `provider`), authentication method,
state, Podman endpoint, YOLO, worktree scope, budgets, lifetime and
CA trust. In provider mode it shows the residual-exfiltration notice and needs
your acknowledgement. It then reviews the choices and the image maintenance it
will perform, prepares the images and guard, installs a protected release in
`~/.local/lib/codex-container`, runs qualification and a credential-free smoke
check, and installs the managed launcher `~/.local/bin/codex-container`. Use
that command from any workspace; it supplies the saved choices unless you export
the corresponding variable. Rerun setup to change them; a failed update keeps
the last working release. For ChatGPT accounts, setup offers
`codex login --device-auth`. See [docs/setup.md](docs/setup.md).

### Direct operator launches

The wrapper also runs directly with an explicit mode, from the repository
directory:

```bash
chmod +x codex-container.sh
export CODEX_CONTAINER_NETWORK=unrestricted
CODEX_CONTAINER_MAINTENANCE=1 ./codex-container.sh --container-build
./codex-container.sh
./codex-container.sh exec --full-auto
./codex-container.sh --container-shell
./codex-container.sh --container-help
CODEX_YOLO=1 ./codex-container.sh
```

An unset or empty `CODEX_CONTAINER_NETWORK` selects `provider`, the default for
an agent wrapper. Without a protected installation or the provider settings
that setup saves, the launch stops with `setup required:` guidance before any
engine call or state creation. Unknown values fail before image operations.

Every image build is maintenance: `--container-build` and the automatic build
of a missing image both require the exact `CODEX_CONTAINER_MAINTENANCE=1`, in
every mode. Without it the wrapper stops before any build or pull. Image
inspection status 0 uses the existing image; status 1 builds a missing image
only under maintenance. Other inspection errors stop startup; check the
reported storage or engine error instead of expecting a rebuild. A failed
build never starts a session. Image preparation fetches Debian packages over
verified HTTPS only and needs outbound HTTPS (443) to the Debian, npm and
container registries, not port 80. With host CA trust enabled, the selected
bundle is also passed to the build as the `build-ca` secret, so the package
fetches verify on TLS-intercepting networks; it is never stored in a layer. Host pulls and build `RUN` steps happen outside
runtime network filtering.

A build pulls the exact `FROM` base first and then runs with `--pull=never`
and the docker format, without a timeout. Every image carries a
`build-inputs-hash` label over its build inputs (`Containerfile`,
`.containerignore`, `network/relay.py`, `network/mux.py`); a launch refuses an
image built from other inputs and names the rebuild command.
`--container-build` without Codex arguments, also together with
`--container-git-worktree` or `--container-shell`, validates every setting,
builds the image and exits without a session; setup uses this operation. With
Codex arguments, it builds and then starts the session.

The default-deny `.containerignore` admits only `Containerfile`,
`.containerignore` and the two relay inputs `network/relay.py` and
`network/mux.py`, which the image copies to `/opt/sandbox-egress/`. Git
metadata, local configuration, state, credentials, the guard binary, policies,
caches, tests, documentation, and other files are excluded, including nested
and newly added files. Future local `COPY` or `ADD` inputs must be deliberately
included in `.containerignore`. This policy filters builds; it does not
restrict runtime workspace mounts.

`CODEX_CONTAINER_IMAGE` overrides the image name.

OpenSpec is installed globally in the image. Initialize it once in each
workspace where you want to use spec-driven development:

```bash
./codex-container.sh --container-shell
cd /absolute/path/to/your-project
openspec init
```

After initialization, use the generated OpenSpec instructions from Codex,
including `/opsx:explore` and `/opsx:propose`. Refresh them with
`openspec update` after upgrading OpenSpec.

The wrapper is designed to replace the `codex` command through a shell alias:

```bash
alias codex=/absolute/path/to/codex-container.sh
```

The wrapper handles `--container-build`, `--container-shell`,
`--container-git-worktree`, `--container-toolchain` (see [Toolchains](#toolchains))
and `--container-help`. Every other argument is
forwarded unchanged, so `codex --help`, `codex resume --last`, and other normal
Codex invocations keep their original meaning.

Each container reserves a name from the physical current directory and the
next numeric index among all existing instances, for example
`codex-container-0` and `codex-container-1`. Suffixes of one to nine decimal
digits count (`08` means eight). Concurrent name collisions are retried up to
20 times; existing sessions are never deleted to free a name. INT, TERM, and
HUP are forwarded to the owned container. The wrapper preserves process exit
codes (including 125) and removes only its own container at termination.

A signal starts shutdown at once, also while the container is being created.
Shutdown has one 20-second budget. After forwarding a signal, the wrapper allows
at most 5 seconds for graceful exit, then attempts forced removal with Podman's
stop wait set to zero. Shutdown engine calls have a 2-second soft timeout and
at most 1 further second before forced client termination, capped by the remaining
overall budget. Local create/attach clients are also terminated and reaped within
that budget. Normal application and build durations are unrestricted.

The first terminal signal selects status 143 (TERM), 130 (INT), or 129 (HUP);
later signals do not restart shutdown. Otherwise the application's exit status
is retained, including zero and 125, even if cleanup fails. Failures are reported
on stderr with the known container ID or session ownership label. If the engine
cannot confirm removal, inspect that identity on the host with `podman inspect`
or filter `podman ps --all --filter label=io.codex-container.session=SESSION`,
replacing `SESSION` with the reported session token.
Only remove a confirmed session container. A disconnected engine can finish
creation after bounded recovery ends; a warning does not mean it was removed.
SIGKILL, host failure, or engine loss can leave residual containers.

Private per-attempt CID files and a unique session label support recovery when
creation is interrupted before its client returns an ID. A workspace name alone
never authorizes removal, and interrupted creation never starts the application.

Both Codex and shell modes allocate a TTY only when stdin and stdout are
terminals. Pipes, file input, and redirected output retain stdin forwarding and
EOF without requesting a TTY. Commands that themselves require a terminal still
need one. For example, run shell commands from a file:

```bash
printf 'pwd\nexit 0\n' | ./codex-container.sh --container-shell
./codex-container.sh --container-shell < commands.sh > session.log
./codex-container.sh --container-shell -c 'make test'
```

Shell mode passes its arguments to Bash and never adds Codex arguments or the
YOLO flag. `--container-help` requires no engine and creates no state.

The session receives `USER`, `EDITOR=nano` and `VISUAL=nano`, and by name
`TERM`, `COLORTERM`, `LANG` and `LC_ALL` when set. Unrestricted sessions also
receive `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their
lowercase forms, run with `--init`, and see their container name as
`CONTAINER_NAME`. In offline and provider sessions the confined guard plays the
role of `--init`: Ctrl+C and the shutdown signals reach Codex, and the session
ends with Codex's status. `CODEX_CONTAINER_ENV_VARS` lists further host variable names
(separated by whitespace) to forward by name, never by value; an invalid name
stops the launch, an empty variable is not forwarded, and names the launcher
sets itself (and, in restricted modes, proxy, CA and provider settings, or in
provider mode another profile's credential) are skipped with a notice.

`CODEX_YOLO=1` starts Codex with `--yolo`, disabling approvals and sandboxing.
`CODEX_YOLO` accepts `1`, `true`, and `yes` to enable it, and unset, empty,
`0`, `false`, or `no` to disable it. Words are case-insensitive, so `TrUe`
and `YeS` enable it and `FaLsE` and `nO` disable it. Other values, including
words surrounded by spaces, stop startup with an error. Shell mode validates
the value but does not add Codex arguments. This parsing does not change
explicit native CLI arguments.
Use it only when the container and its mounts are considered an isolated,
trusted environment.
The image filesystem remains read-only even with `CODEX_YOLO=1`.

Approvals, the CLI's internal sandbox, and outer container isolation are
separate controls. With `CODEX_YOLO` disabled, native arguments and saved CLI
settings still apply; the wrapper does not override them to enforce a policy.
Installing Bubblewrap or passing a basic namespace probe does not establish
that an actual CLI sandboxed operation succeeds. Check the operation and its
output independently; no Antigravity-specific seccomp workaround is applied.

| `CODEX_YOLO` | Session behavior |
| --- | --- |
| Disabled | Native CLI settings |
| Enabled | `--yolo` |

```bash
./codex-container.sh
CODEX_YOLO=1 ./codex-container.sh
```

### Container tests

Sessions never receive the host Podman API. When the toolchain library holds at
least one image toolchain, every session instead gets a private, rootless
Podman engine of its own, in every network mode. The engine shares the
session's network namespace, so its containers have the session's egress: an
offline session's containers reach nothing outside. The session reaches it at
`CONTAINER_HOST=tcp://127.0.0.1:2375`, also given as `DOCKER_HOST` for
Docker-API clients such as Testcontainers. The engine runs the library's images
offline by their pinned references, mounts only the workspace (at the same
path) and the library's read-only image store, holds no secrets, and is removed
with its storage when the session ends. Without images in the library, or with
`CODEX_CONTAINER_TOOLCHAINS=0`, there is no engine and `CONTAINER_HOST` and
`DOCKER_HOST` are absent from the session, including image or engine defaults.

```bash
./codex-container.sh --container-toolchain add ~/recipes/postgres16.json   # see Images
./codex-container.sh --container-shell -c 'podman run --rm --network=none docker.io/library/postgres@sha256:<digest> postgres --version'
```

- **Images:** add them as toolchains ([Images](#images)). In offline and
  provider sessions the engine pulls nothing; in unrestricted sessions it can
  also pull, and pulled or built images stay in the session's storage. An image
  added during a session is usable at once; the first image needs a new
  session, because a session without library images starts without an engine.
- **Workspace:** a container that bind-mounts a path inside the workspace sees
  the workspace files, and files its root creates there belong to you. Any
  other path a nested container mounts is the engine's own file system, never
  the host's.
- **Isolation:** each nested container has its own process view and host name
  (its container ID). Two sessions have separate engines and never see each
  other's containers.
- **Lifetime:** the launcher starts the engine before the application, waits
  until it answers as a rootless engine, and removes it with its storage when
  the session ends, also after a signal. A later launch removes the engine of a
  launch that was killed.
- **Budgets:** the engine gets the session's memory, CPU and process budgets,
  checked like the agent's; together the session can therefore use twice the
  agent's budget, and the launch says so. On the process rlimit fallback the
  engine's first process sets the limit before anything else, and the launch
  reads it from that process before the session starts; the engine and
  everything it runs share that one limit. Explicit `--memory` or
  `--pids-limit` limits on nested containers apply for every cgroup controller
  the engine has (see **Systemd containers and nested limits** below); a limit
  that needs a controller the engine lacks fails, and the container does not
  start.
- **Hardening exceptions:** the engine container is the one container that
  relaxes the standard policy, only as nested rootless containers and image
  operations need: the `SETUID` and `SETGID` capabilities for the
  user-namespace helpers and `SYS_CHROOT` for layer extraction and builds
  (with no-new-privileges kept on), the FUSE and TUN devices, an unmasked procfs,
  SELinux labelling disabled, a seccomp profile derived from the host's
  default that also allows `sethostname` and `setdomainname`, and a startup
  step that delegates the engine's own cgroup subtree. That step is the
  engine's first process: it starts as the root of the engine's user namespace
  (never you) with the `CHOWN` capability as well, hands the subtree to the
  engine user, and then runs everything else as that user. Afterwards no
  engine process runs as root, and `CHOWN` stays only in the bounding set,
  where no-new-privileges keeps it unreachable. The engine user is unprivileged
  and mapped to you (`--userns=keep-id:uid=1000,gid=1000`), which needs 65535
  of your subordinate IDs in one contiguous range. A tool that needs more
  privilege is unsupported. The engine image declares these four capabilities
  (`SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`) in its
  `io.containers.capabilities` label, so Podman starts the engine without a
  capability error. An engine image built before `sandbox-ref-36` keeps its
  base's label, and Podman logs `Capabilities requested by user or image are
  not allowed by default` at each start. The message is harmless, because
  Podman keeps the engine's capabilities. Rerun
  `codex-container --container-setup` to rebuild the image.
- **Systemd containers and nested limits:** on an eligible engine, nested
  containers get cgroups of their own, so an image that starts systemd runs it
  as PID 1, for example to test Ansible roles that manage services:

  ```bash
  # an image toolchain whose image starts /sbin/init, such as a Rocky Linux 9 init image
  podman run --detach --name target --systemd=always docker.io/rockylinux/rockylinux@sha256:<digest>
  podman exec target timeout 120 sh -c 'until systemctl is-system-running | grep -qE "^(running|degraded)$"; do sleep 1; done'
  podman exec target systemd-run --unit=probe --property=Type=oneshot /bin/true
  ```

  The second command waits until boot completes (`running` or `degraded`).
  `systemctl is-system-running --wait` does the same only when the image
  has D-Bus; init images without it answer `Failed to connect to bus`.

  An engine is eligible when its cgroup namespace is private and its cgroup
  v2 root is mounted read-write with `nsdelegate` and belongs to the root of
  its user namespace. This holds for native Linux with the `systemd` cgroup
  manager and for the Windows Podman machine (`cgroupfs`); no host change is
  needed. Explicit nested limits apply for each controller the engine has:
  `memory` and `pids` where the rootless engine delegates them (native Linux
  with the `systemd` manager); the Windows Podman machine delegates none, so
  there they fail, and systemd's resource-control unit settings (such as
  `MemoryMax=` or `TasksMax=`) have no effect. The engine's own limit files,
  and so the session budgets, stay unwritable from the engine and from nested
  containers. When an engine is not eligible, for example on a host with
  cgroup v1, the launch says `systemd containers and explicit limits for nested
  containers are unavailable` with the reason, and the session starts without
  them. Systemd containers and the delegation are untested with SELinux
  enforcing or an active AppArmor profile.
- **Host `/sys` in the session:** the session joins the engine's network
  namespace, and a rootless container that joins another namespace cannot
  mount a sysfs of its own: Podman bind-mounts the host's `/sys` read-only
  instead. A session with an engine therefore sees the host's network
  interfaces in `/sys/class/net` (names, MAC addresses, link state and
  counters). Its network namespace still has only loopback, as `/proc/net/dev`
  shows.

Migration: host Podman delegation (`CODEX_CONTAINER_PODMAN=1`, with
`CODEX_CONTAINER_PODMAN_SOCKET`) was removed. The exact value `1` now stops
every launch with this guidance, other values are ignored, and setup drops a
saved delegation choice. Add the images your tests need as toolchains (see
[Toolchains](#toolchains)); the next session has its engine.

### Using Git worktrees

When shared Git metadata and sibling worktrees are beneath a common parent,
run the wrapper from the worktree root with `--container-git-worktree`:

```bash
cd /path/to/root/main
codex --container-git-worktree
codex --container-git-worktree --container-shell
```

Here `codex` is the alias shown above. The option mounts `/path/to/root` at
`/path/to/root` read/write, while the container starts in `/path/to/root/main`.
All files beneath that parent, including sibling worktrees, become writable.
Git metadata outside the selected parent is not exposed by this option.

The wrapper selects the immediate parent of the physical launch directory,
resolving symbolic links without searching for a Git or worktree root. For
example, launching from `/path/to/root/main/src` mounts `/path/to/root/main`.
The flag does not create worktrees or require a Git repository.

### Persistent state and isolation

By default the wrapper reuses the caller's `${HOME}/.codex`, sharing its
configuration, credentials, and sessions with other uses of that directory.
Select separate state explicitly when you want isolation:

```bash
CODEX_HOME="$HOME/.local/share/codex-container/state" ./codex-container.sh
```

Two invocations using the same directory share state; state is not selected
automatically per project. Changing `CODEX_HOME` selects different settings
and sessions without copying existing data. A nonempty `CODEX_HOME` must be an
absolute path without colon, CR or LF; the wrapper checks it before any engine
operation. Inside the container it is always `/codex-home/.codex`; the rest of
`/codex-home` is an ephemeral 512 MiB `noexec` tmpfs whose files disappear with
the session.

Before any image operation or startup, the wrapper creates missing state
with mode `0700`, resolves its physical path, and requires caller ownership,
read/write/traverse access, and no group/other permission bits. Existing
permissions and ownership are never repaired automatically. For an existing
directory that you own, correct its permissions explicitly:

```bash
chmod 700 -- "${CODEX_HOME:-$HOME/.codex}"
```

Wrong ownership requires an appropriate ownership correction or a different
private directory. Some Windows-backed WSL filesystems ignore Unix modes;
choose a native Linux path for `CODEX_HOME` if private modes cannot be enforced.
Workspace files can remain on Windows storage. A containerized caller must
use a state path also available at the identical absolute path on the host.

These checks protect access to the selected directory; they do not encrypt
state or audit all ancestors, ACLs, or existing files. The agent can read and
write the mounted state. Removing a container does not remove it.

`CODEX_CONTAINER_READONLY_STATE` (`1`, `true` or `yes`) mounts the existing
Codex configuration read-only instead, from shared state or from the isolated
home; the directory must exist and be accessible, nothing is created, and the
isolated home itself is not mounted. Codex cannot save sign-ins or sessions in
such a launch.

For a fully isolated application home, set `CODEX_CONTAINER_STATE_DIR`
instead of `CODEX_HOME`:

```bash
unset CODEX_HOME
CODEX_CONTAINER_STATE_DIR="$HOME/.local/share/codex-container/isolated" ./codex-container.sh
```

The directory, which must be an absolute path without colon, CR or LF, is
mounted read/write at `/codex-home` (with `CODEX_HOME=/codex-home/.codex`), so
caches and other home data persist with it. The shared `~/.codex` is neither mounted nor imported: sign in again
inside the isolated home. A simultaneous nonempty `CODEX_HOME` is a conflict
error. The wrapper creates the home and its `.codex` privately, applies the
same ownership and mode checks to both, never repairs permissions, and rejects
`.codex` or the CA mount parent if a symbolic link resolves outside the home.
The isolated home must not be the workspace, contain it or lie inside it (the
parent directory in worktree mode), so credentials and history never land in a
repository; the wrapper and the managed launcher refuse an overlap before any
engine operation.

### Host CA trust

Host CA trust is opt-in. `CODEX_CONTAINER_TRUST_HOST_CA` accepts `1`, `true`
or `yes` (case-insensitive) to enable it, and empty, `0`, `false` or `no` to
disable it; other values fail before image operations. When enabled, the
wrapper mounts one bundle file read-only at `/codex-home/ca/bundle.pem` and sets
`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and
`NODE_EXTRA_CA_CERTS` to it. Codex reads `SSL_CERT_FILE` when
`CODEX_CA_CERTIFICATE` is unset. The bundle is `CODEX_CONTAINER_CA_BUNDLE`, or
the first existing file among `/etc/ssl/certs/ca-certificates.crt` and
`/etc/pki/tls/certs/ca-bundle.crt`; a missing file is an error. The host
certificate directory is never mounted.

With a Podman machine on Windows, the host is the machine: it must first
import the CAs that Windows trusts
([Trusting a host CA on Windows](#trusting-a-host-ca-on-windows)).

## Network modes

| `CODEX_CONTAINER_NETWORK` | Agent network access |
| --- | --- |
| unset or empty | `provider`; without setup's saved provider settings the launch stops with setup guidance |
| `offline` | Own loopback, pipes and connected socket pairs only |
| `provider` | As offline, plus one preconnected channel to an exact-destination proxy |
| `unrestricted` | Ordinary runtime networking |

A session container engine ([Container tests](#container-tests)) shares the
session's network namespace, so its containers have the same access.

First-run setup proposes `provider` and saves the selected mode for its managed
launcher. Operators can explicitly choose `offline` for prepared restricted
sessions or `unrestricted` for broad networking; commands that build the image
also need `CODEX_CONTAINER_MAINTENANCE=1`. Restricted failures never fall back
to unrestricted networking. Offline sessions cannot reach the OpenAI API.

The restricted implementation is shared with `sandbox-container` and copied
unchanged from its tag `sandbox-ref-36`; see
[docs/network-contract.md](docs/network-contract.md) and
[network/README.md](network/README.md). Every agent container, in every mode,
drops all capabilities, enables no-new-privileges and receives the memory, CPU
and process budgets.

### Restricted prerequisites

`offline` and `provider` require:

- host Python 3 and a same-host Unix rootless Podman service (explicit
  `CONTAINER_HOST=unix:///...`) with Netavark and Podman ≥ 4.9;
- Linux or WSL2 x86_64 with standard OCI seccomp and usable Landlock ABI ≥ 3;
- a protected installation: this checkout, the guard, the policy and the
  profile must lie outside every writable workspace and state tree;
- the static guard `network/bin/sandbox-egress-guard` and its SHA-256 manifest;
- a current local qualification report.

Unsupported setups fail closed. SELinux and AppArmor stay active when enabled;
their denials stop startup and are never disabled by the wrapper.

### Operator build inputs

Restricted modes run from a protected installation: a copy of this checkout on
native Linux storage (on WSL, not under `/mnt/<drive>`) whose directories are
owned by you and not writable by group or others, outside any workspace or
state directory. Guided setup creates such an installation. To prepare one
manually instead, build the guard and proxy image there under maintenance (see
"Operator build inputs" in
[network/README.md](network/README.md)):

```bash
install="$HOME/.local/opt/codex-container"     # protected native copy
git clone --branch main /path/to/codex-container "$install" && cd "$install"
export CODEX_CONTAINER_MAINTENANCE=1
tag=$(python3 -I network/agent_profile.py image toolchain development)
podman build --tag "$tag" --file network/guard-build.Containerfile network
mkdir -p network/bin && bash network/build-guard.sh "$install/network/bin"
podman build --tag localhost/codex-egress:local --file network/Containerfile network
podman image inspect --format '{{.Id}}' localhost/codex-egress:local
```

Pass the printed immutable image ID (or a registry digest) as
`CODEX_CONTAINER_EGRESS_IMAGE`. A missing proxy image is pulled only under
maintenance and only by digest. Restricted sessions run the runtime image by
its immutable ID.

### Qualification

```bash
CONTAINER_HOST=unix:///run/user/$(id -u)/podman/podman.sock \
CODEX_CONTAINER_NETWORK=offline bash ./codex-container.sh --container-qualify
```

`--container-qualify` must be used alone. It is credential-free, uses fixed
disposable controls and never runs an application command or grants image
maintenance. Every ordinary `offline` or `provider` launch first runs the same
check and stops with `qualification-required` when the report is missing or
stale. The report is bound to the boot, engine, backend and security policy,
code and images, policy and profile, CA trust and hardening settings (agent
budgets and lifetime included). Documented behaviors:

- a reboot changes the boot identity, so the next launch requires
  requalification;
- when the active LSM policy cannot be identified, the gate runs on every
  launch instead of reusing the report;
- `network/release_acceptance.json` is empty, so a passing installation is
  reported as `locally-qualified`, not release-measured.

### Provider mode

```bash
export CONTAINER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
export CODEX_CONTAINER_NETWORK=provider
export CODEX_CONTAINER_NETWORK_POLICY="$PWD/agent/policies/default.json"
export CODEX_CONTAINER_NETWORK_PROFILE=openai-account   # or openai-api, or openai-api-docs
export CODEX_CONTAINER_NETWORK_RUNTIME_DIR="$HOME/.local/state/codex-egress"  # private, native
export CODEX_CONTAINER_EGRESS_IMAGE=sha256:...           # immutable proxy image ID
bash ./codex-container.sh --container-qualify
bash ./codex-container.sh
```

| Profile | Allowed destinations | Credentials |
| --- | --- | --- |
| `openai-api` | `api.openai.com:443` | `OPENAI_API_KEY`, forwarded only to this profile |
| `openai-account` | `auth.openai.com:443`, `chatgpt.com:443`, `developers.openai.com:443` | ChatGPT sign-in stored in `CODEX_HOME`, plus the OpenAI documentation MCP |
| `openai-api-docs` | `api.openai.com:443`, `developers.openai.com:443` | As `openai-api`, plus the OpenAI documentation MCP |

A host `OPENAI_API_KEY` is forwarded by name only to provider sessions with
`openai-api` or `openai-api-docs`, never with `openai-account` or an operator
profile; offline and unrestricted sessions get no key unless
`CODEX_CONTAINER_ENV_VARS` lists it in unrestricted mode. No key is copied into
the image or policy. Provider help lists the hosts of the two base profiles from
the default policy.

`developers.openai.com` serves the OpenAI documentation MCP server
(`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`).
Codex 0.169.0 reached only `developers.openai.com` for this server through the
relay. The command stores the entry under the user's `CODEX_HOME`. Both
`codex mcp list` and `codex exec` load it from an untrusted workspace.
`openai-account` includes it, so account users
reach the server by default. For the API-key method, setup proposes the exact
`openai-api`; `openai-api-docs` is an opt-in extension that you export and
qualify once:

```bash
export CODEX_CONTAINER_NETWORK_PROFILE=openai-api-docs
codex-container --container-qualify   # managed launcher; or bash ./codex-container.sh
codex-container                        # exported values take precedence over setup
```

**Migration.** Policy revision `openai-2026-11-11-v1` adds
`developers.openai.com` to `openai-account` and removes the former
`openai-account-docs`. Existing provider installations need setup or
`--container-qualify` once after the update, because the policy file changed;
if you exported `CODEX_CONTAINER_NETWORK_PROFILE=openai-account-docs`, switch
to `openai-account`.

The policy revision is `openai-2026-11-11-v1`, revalidated with Codex 0.169.0 on
2026-11-18.
The account inventory comes from the official authentication documentation
and a static scan of the installed CLI; authenticated sign-in, request and
refresh are **unverified** until the operator check recorded in
[docs/validation.md](docs/validation.md). Wildcards are never used; gateways
and other providers need separately named profiles.

ChatGPT browser sign-in needs a callback on `localhost:1455` that the host
browser cannot reach in the container; no port is published. Use
`codex login --device-auth` (it must be enabled in the ChatGPT security
settings or workspace permissions) or an API key with `openai-api`.

Provider sessions place these overrides before your arguments:
`check_for_update_on_startup=false`, `analytics.enabled=false`,
`feedback.enabled=false`, `otel.exporter`, `otel.trace_exporter` and
`otel.metrics_exporter` set to `"none"`, and `features.apps`,
`features.plugins`, `features.remote_plugin` and
`features.plugin_discovery_prefetch` set to `false`. They take precedence over
the agent-writable `config.toml`; a `-c` you pass after them is your explicit
choice and wins. No environment variable controls these settings, so
`--container-shell` receives none; remote MCP servers configured in
`config.toml` have no disable control. The proxy denies all such traffic
anyway, because it reaches no allowed host.

**Limits and residual risk.** The proxy binds the TLS server name of the
initial ClientHello, and of the retried one after a TLS 1.3 HelloRetryRequest,
to the CONNECT host before forwarding; missing or mismatched names, ECH and
non-TLS traffic fail closed. TLS 1.2 renegotiation is encrypted and not
inspected. This does not prove exclusive OpenAI application access: the HTTP
`Host`, shared-service routing and provider-side forwarding stay opaque, and
allowed services can receive data. An injected agent can send workspace data
to an allowed host (`api.openai.com` for `openai-api`; `auth.openai.com`,
`chatgpt.com` and `developers.openai.com` for `openai-account`;
`api.openai.com` and `developers.openai.com` for `openai-api-docs`) with an
attacker's key or account; only `offline` removes this. Provider-hosted tools, such as web search, run at the
provider outside this boundary.

**Notices.** In `offline` and `provider`, the wrapper passes a protected
`--no-daemon`, so Codex runs embedded without the `Running without the shared
background server` notice. The shared background server cannot run under the
guard, because it needs a Unix listener, and the protected `-c` overrides would
select embedded mode anyway. A remote MCP server in `config.toml` whose host
is not in the selected profile fails to start with a `HTTP CONNECT failed` or
`error sending request` message, because the proxy denies it. Set `enabled = false` for that
server under `[mcp_servers.<name>]`, or, for the OpenAI documentation MCP,
use `openai-account` or `openai-api-docs`.

### Codex's own sandbox

Codex's command sandbox cannot run under the guard. With Codex 0.169.0 the
Bubblewrap path needs a Netlink socket to configure loopback in a new network
namespace, which the guard denies, and the Landlock-only path refuses to run
without Bubblewrap. In `offline` and `provider`, the wrapper therefore adds a
protected `--no-daemon -c sandbox_mode="danger-full-access"` before your
arguments, so Codex runs embedded and executes commands without its inner
sandbox. The guard stays the enforced
boundary: no network beyond the selected mode, no new Unix sockets, no
capabilities, and a read-only image root. A `--sandbox` or
`-c sandbox_mode=...` you pass after it wins as an explicit choice; an inner
sandbox selected that way fails before the command. `--container-shell` and
`unrestricted` sessions get no override, and Codex's own sandbox keeps working
in `unrestricted`. The measurements are in
[docs/validation.md](docs/validation.md).

## Windows with Podman machine

On Windows, `codex-container.ps1` starts the sandbox from PowerShell on the
rootless engine of a Podman machine that Podman Desktop created with the WSL
provider. The session runs inside the machine's WSL distribution
(`podman-machine-default`, user `user`), in the PID and mount namespaces where
the machine runs systemd and its Podman service, as the machine's own login
shells do. The entry uses neither `podman.exe` nor the machine's SSH or
Windows API connection, so it works while other WSL distributions, such as
Ubuntu, are running.

Prerequisites:

- Windows PowerShell 5.1 or PowerShell 7, with a policy that allows local
  scripts, for example `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`;
- a rootless Podman machine with the WSL provider, created with Podman
  Desktop, and started by Podman (Podman Desktop or `podman machine start`)
  before setup and sessions;
- `sudo` without a password for the machine's user, which Podman machines
  provide: sessions and setup enter the machine's systemd namespaces with
  `sudo nsenter`, as its login shells do (`/usr/local/bin/enterns`);
- a checkout of this repository in a folder on a Windows drive, with LF line
  endings. The repository's `.gitattributes` keeps them LF even with
  `core.autocrlf=true`; [docs/setup.md](docs/setup.md) explains how to fix an
  older CRLF checkout.

Run setup once from the checkout, in an interactive PowerShell window:

```powershell
cd C:\Work\codex-container
.\codex-container.ps1 --container-setup
```

Setup runs the guided setup inside the machine distribution. The release,
preferences and images are installed there, in `~/.local/lib/codex-container`.
Its output leaves out the Linux shell guidance; the entry prints how to start
sessions.
Setup finds the machine's own Podman service, so it offers provider
networking, the default, with the account or API method, and offline and
unrestricted networking, as on Linux.

With the account method, setup offers to run `codex login --device-auth` in the
machine. Open the printed URL in a Windows browser, sign in and enter the code
shown. The credentials stay in the machine user's Codex state (`~/.codex` in
shared state mode), separate from Codex on Windows. When you postpone the
login, setup names the next step: `codex-container.ps1 login --device-auth`.
With the API method, set `$env:OPENAI_API_KEY = '...'` in PowerShell before
`codex-container.ps1`. The entry forwards the key by name, and setup stores
none. Rerun setup after updating the checkout, and after the machine is
recreated. To run the sandbox as a command without keeping the checkout,
install it instead ([Install as a command](#install-as-a-command)).

Start sessions from a project directory on a Windows drive:

```powershell
cd C:\Work\my-project
C:\Work\codex-container\codex-container.ps1
C:\Work\codex-container\codex-container.ps1 --container-shell -c 'git status'
C:\Work\codex-container\codex-container.ps1 --container-help
```

The project is mounted at its drive path, for example `/mnt/c/Work/my-project`.
A launch is refused before any engine query in these cases:

- the machine is stopped: the entry does not start its distribution, because
  `wsl.exe` would start it without the user's runtime directory
  `/run/user/<uid>`, where no `podman` command works. Start the machine with
  Podman Desktop or `podman machine start`;
- the distribution runs without that directory, because `wsl.exe` alone
  started it. Run `wsl --terminate podman-machine-default`, then start the
  machine with Podman. Setup refuses both states too;
- `sudo` asks the machine's user for a password, so the entry cannot enter the
  machine's systemd namespaces. Setup refuses it too;
- the location is a network share, a path inside a WSL distribution, a drive
  the distribution does not mount, or not a file system path;
- the project or the worktree parent contains the checkout, or lies inside it;
- the project is a Windows system or profile folder (see
  [Session hardening, budgets and lifetime](#session-hardening-budgets-and-lifetime)).

The exit status, the terminal and Ctrl+C work as on Linux. Closing the window
also ends the session and removes its container. The machine's engine uses
the `cgroupfs` manager: the memory and CPU budgets are not enforced, and the
process budget uses the process rlimit, as the launch notices state (see
[Session hardening, budgets and lifetime](#session-hardening-budgets-and-lifetime)).
Codex's own sandbox behaves as on Linux
([Codex's own sandbox](#codexs-own-sandbox)): in `unrestricted` it runs inside
the machine's rootless engine and denies workspace writes under its default
policy, and in `offline` and `provider` the guard replaces it.

| Variable | Meaning |
| --- | --- |
| `CODEX_CONTAINER_NETWORK` | `provider`, `offline` or `unrestricted` for one launch (default: the mode setup saved); a restricted mode needs a setup that prepared it |
| `CODEX_CONTAINER_WSL_DISTRO` | WSL distribution (default `podman-machine-default`) |
| `CODEX_CONTAINER_WSL_USER` | user in the distribution (default `user`) |
| `CODEX_CONTAINER_WSL_INSTALLATION` | absolute installation path in the distribution, when setup used another one |

Set them with `$env:NAME = 'value'`. The entry forwards to the launcher in the
distribution, by name, the other `CODEX_CONTAINER_*` variables whose names use
only letters, digits and `_`, `CODEX_HOME` when it holds a distribution path
(starting with `/`), `CODEX_YOLO`, `OPENAI_API_KEY`, and the names listed in
`CODEX_CONTAINER_ENV_VARS`. A Windows path in `CODEX_HOME`, such as one set for
Codex on Windows, is skipped with a notice, and the directory saved by setup
applies. `$env:OPENAI_API_KEY = '...'` before the entry supplies the key as an
exported variable does on Linux; the help lists it. It forwards no other
Windows variable. Path values are distribution paths, such as
`/home/user/...`.

Limits on Windows:

- No host Podman delegation, as on Linux: `CODEX_CONTAINER_PODMAN=1` is
  refused with the migration guidance, and a release whose setup saved
  delegation asks to rerun setup from Windows. Sessions with image toolchains
  get their private container engine in the machine
  ([Container tests](#container-tests)).
- PowerShell pipeline input, such as
  `'x' | .\codex-container.ps1 --container-shell -c cat`, is refused, because
  PowerShell alters it. Redirect a file from `cmd.exe` instead:
  `cmd /c "powershell -File C:\Work\codex-container\codex-container.ps1 --container-shell -c cat < input.txt"`.
- PowerShell parses the arguments first. Quote a `--` meant for Codex or Bash
  (`'--'`), values with commas (`'a,b'`), numbers whose spelling matters
  (`'007'`) and arguments of the form `-x:y`. The encoded arguments are
  limited to 32766 characters.
- A variable with an empty value counts as unset.
- `podman machine stop` (`wsl --terminate`) ends running sessions.
- After the machine starts, the folder of its first session may stay in use
  by a WSL process until `wsl --shutdown`, so Windows cannot delete that
  folder meanwhile.
- Projects on a Windows drive go through drvfs, which is slow on large trees.
  Git for Windows clones with `core.autocrlf=true` look modified to Git in the
  session: set `core.autocrlf=false` for the project, or give it a
  `.gitattributes`.
- Bitdefender's Advanced Threat Control (`Atc4.Detection`) has blocked the
  operator validation script `tools/windows-validate.ps1` of
  `sandbox-container`, and quarantined files while validation bundles were
  extracted with `tar`, for example `tests/fixtures/shell-agent/launcher.sh`,
  which only the Linux tests use. Setup, the installer and sessions ran with it
  active, and another Windows system with other antivirus products ran the
  validation without problems. Run the validation script with the checkout
  folder excluded, or with the protection paused for the run, as your
  administrator allows. Setup and the entry fail when a file they need is
  missing: restore it from the quarantine, and report the false positive to
  the vendor.

### Trusting a host CA on Windows

Setup and sessions run in the machine, so host CA trust uses a bundle of the
machine, not the Windows certificate store. On a network that intercepts TLS
(a corporate proxy that re-signs certificates), the machine trusts the
interception CA only when Podman imports the Windows store into it. Without
it, image pulls and builds in the machine and HTTPS requests in sessions fail
with a certificate verification error. With Podman 6.0 or later, enable the
import once. `podman machine set` fails while the machine runs, so stop it
first:

```powershell
podman machine stop
podman machine set --import-native-ca
podman machine start
```

The import happens at every machine start: Podman copies the CAs that Windows
trusts into the machine and runs `update-ca-trust`, so the machine's system
bundle contains them. Restart the machine after Windows gains a new CA.

Then run setup and answer yes to "Trust a host CA bundle?". Keep the bundle
setup proposes, the machine's system bundle (see
[Host CA trust](#host-ca-trust)): setup passes it to the image builds and saves
it for sessions. Rerun setup after the machine is recreated, and enable the
import again on the new machine.

### Toolchains on Windows

The [toolchain](#toolchains) commands run from PowerShell like the other
options, from any directory outside the checkout:

```powershell
codex-container --container-toolchain add java21
codex-container --container-toolchain add C:\Users\me\recipes\x.json
codex-container --container-toolchain list
```

- **Location:** the library lives inside the Podman machine's distribution, in
  `~/.local/share/sandbox-toolchains` of the machine user, or in
  `CODEX_CONTAINER_TOOLCHAINS_DIR` (a distribution path). Every wrapper that
  runs in the machine shares it. Recreating the machine removes it: after the
  new setup, add the toolchains again.
- **Windows paths:** a recipe path or a local archive path in a recipe written
  as a Windows drive path (`C:\...` or `C:/...`) is translated to its drive
  mount in the machine. Network shares, paths inside a WSL distribution and
  drives that the distribution does not mount are refused. Keep your recipes
  outside project folders (see [Managing the library](#managing-the-library)).
- **Network:** pulls and downloads run inside the machine. On a network that
  re-signs TLS, they trust the CA that `podman machine set --import-native-ca`
  adds to the machine (see [Trusting a host CA on Windows](#trusting-a-host-ca-on-windows)).
  The entry forwards no Windows proxy variable, so `add` downloads without an
  explicit HTTP proxy; pulls follow the machine's Podman configuration.

### Install as a command

Instead of setup from the checkout, you can install the entry for your
Windows account:

```powershell
cd C:\Work\codex-container
.\codex-container.ps1 --container-install
```

The install copies the entry, the Windows scripts and every file that setup
needs into `%LOCALAPPDATA%\Programs\codex-container`. It then adds that
folder to your user `PATH` (`HKCU\Environment`, no administrator rights; the
other entries and their `%VAR%` references stay as they are) and runs setup
from the copy. The installer announces the `PATH` change before making it;
nothing is written to the PowerShell profile or system-wide. Afterwards the
checkout can be deleted, and a new PowerShell window runs the command from any
project directory:

```powershell
cd C:\Work\my-project
codex-container
codex-container --container-shell -c 'git status'
codex-container --container-setup
```

New PowerShell windows and new Windows Terminal tabs find the command; the
window or tab that ran the install may not. When setup fails after the copy,
the copy and the `PATH` entry stay; finish with
`codex-container --container-setup`.

To update, run `--container-install` again from a newer checkout or download.
It replaces the installed files, removes the ones the new version no longer
has, and runs setup. Do not update while a setup runs from the installed
copy. The installed command refuses to install itself. An
interrupted install leaves the copy marked incomplete: the command then
refuses to start sessions until the next install completes. Two installs never
run at once.

`codex-container --container-uninstall` (also from a checkout) removes the
`PATH` entry and the installed copy. The installation inside the Podman machine
stays until the machine is reset. A folder still used by a WSL process is
reported; `wsl --shutdown` releases it.

The scripts are not signed. The installer writes new local files, so the
installed command runs under the default `RemoteSigned` policy. A downloaded
zip keeps the Mark of the Web on its files: run its first install as
`powershell -ExecutionPolicy Bypass -File .\codex-container.ps1 --container-install`,
or `Unblock-File` its files first. Running the installer is your decision to
trust that source. Policies stricter than `RemoteSigned`, such as `AllSigned`,
are unsupported.

## Mounts and security

Both Codex and shell sessions use a read-only image root filesystem. The
workspace and persistent Codex state remain writable host binds. `/tmp`,
`/var/tmp` and `/codex-home` (in shared state) use writable temporary
filesystems; files there are discarded when the container is removed, except
for the nested persistent mount at `/codex-home/.codex`. `/run` is a temporary
filesystem the session user cannot write.

`/tmp`, `/var/tmp` and the shared-state home each have a 512 MiB maximum and
`/run` a 32 MiB maximum, the same in every wrapper. All four are `nosuid`,
`nodev` and `noexec`: nothing written there can be executed, so build and test
artifacts that must run belong in the workspace. `/tmp`, `/var/tmp` and the home
keep mode 1777; `/run` does not. These are per-mount capacities, not reserved memory or a total
container memory limit. Writes can fail when a bounded mount fills; workspace
and persistent state remain separate host storage.

Podman 5 with crun 1.27 cannot attach a terminal when `/dev` is read-only, so
the wrapper keeps automatic read-only tmpfs provisioning. The engine provides
`/dev` and a `devpts` at `/dev/pts` that allows pseudo-terminals, which
interactive tools such as `script`, `expect` or `tmux` need. An explicit
`devpts` mount would get `ptmxmode=000`, and no pseudo-terminal could be
opened. Each session mounts an empty read-only `/dev/shm`. On Podman 5,
`/dev` is the engine's writable tmpfs, but no device can be created without
capabilities. On Podman 4.9, `/dev` stays read-only. Tools that need POSIX shared memory in
`/dev/shm` are not supported. An empty read-only tmpfs at `/run/secrets` masks
engine default mounts there (for example RHEL subscription certificates from
`mounts.conf`), so host secrets are not visible in any mode.

By default, the current workspace is mounted at the same absolute path inside
the container. With `--container-git-worktree`, its immediate physical parent
is mounted at that same absolute path instead; the working directory and
container naming still use the original launch directory. Preserving absolute
paths is required because bind mounts for child containers are resolved by
the session's container engine, which mounts the workspace at the same path. Persistent configuration is stored in
`~/.codex` (or the host `CODEX_HOME` override), mounted at
`/codex-home/.codex`, and also selected through the container's `CODEX_HOME`.

No session receives a host Podman socket. A session's private container engine
mounts only the workspace and the library's read-only image store, so its
containers stay inside the project-only filesystem boundary and the session's
network boundary ([Container tests](#container-tests)). The wrapper does not
block independently configured endpoints or sockets exposed through workspace
files. It does not use `--privileged` and does not install SSH clients or
remote repository configuration.

With `--container-git-worktree`, the selected parent is exposed read/write with
all files beneath it. Use the flag from a directory whose parent you intend to
expose. Sensitive roots are refused (see below); writable binds take precedence
over image paths they cover, so an explicitly allowed `/` would mask the image
root and the read-only image policy would not make such host files immutable.

### Session hardening, budgets and lifetime

Every Codex and shell session, with or without YOLO and a container engine,
runs with `--cap-drop=all` and `--security-opt=no-new-privileges`. The
container has no capabilities and cannot gain privileges through set-user-ID
programs. Codex's own Linux command sandbox, Bubblewrap, Git, OpenSpec and the
Podman client of the session's container engine work under these settings. The
wrapper never adds capabilities back to work around a tool; such a limitation
is documented in `docs/validation.md`. The engine container has its own fixed
exceptions ([Container tests](#container-tests)).

Every session has explicit resource budgets:

| Variable | Default | Accepted values |
| --- | --- | --- |
| `CODEX_CONTAINER_MEMORY_LIMIT` | `4g` | positive integer with unit `k`, `m` or `g` |
| `CODEX_CONTAINER_CPU_LIMIT` | `2` | positive number of CPUs, at most 3 decimals, up to 1024 |
| `CODEX_CONTAINER_PIDS_LIMIT` | `512` | integer from 1 to 4194304 |

Only an unset variable selects the default; no value disables a budget, and an
invalid value stops the wrapper before any engine query. Each budget is enforced
only when the rootless engine delegates its cgroup v2 controller (`memory`,
`cpu`, `pids`), as reported by `podman info` (`Host.CgroupControllers`). A
missing controller leaves that budget unenforced: the wrapper does not request
it, prints a notice such as `codex-container: agent CPU budget not enforced:
cgroup controller cpu is not delegated to the rootless engine`, and continues
without a question. Provider proxies follow the same rule for their 128-process
and 256 MiB limits. After creating the container, the wrapper checks that every
enforced budget was applied and that no unenforced one is present, and stops
before Codex starts otherwise. Restricted qualification records the enforced
set, so a change in delegation requires requalification. Budgets and tmpfs
sizes do not limit workspace or `CODEX_HOME` storage growth.

A rootless engine applies cgroup limits only through the `systemd` cgroup
manager (`podman info --format '{{.Host.CgroupManager}}'`). With `cgroupfs`,
for example on a Podman machine on WSL, the engine reports every controller but
ignores the limits. The sandbox therefore treats no controller as delegated: it
prints `agent memory budget not enforced: the rootless engine uses the cgroupfs
cgroup manager, which applies no cgroup limits` and the matching CPU line, and
the process budget uses the fallback below.

The process budget has a fallback. Without the `pids` controller, the agent
container's first process sets its soft and hard process rlimit to the
selected budget, and the notice reads `agent process budget enforced through the
process rlimit (512 tasks of the session user, threads included)`:
- **Where it is set.** The container starts with a fixed `/bin/sh` step,
  `{ ulimit -u N 2>/dev/null || ulimit -p N; } && exec <program>`, before Codex
  or, in restricted modes, the guard runs (dash names the limit `-p`). If the
  limit cannot be set, the container stops before anything else runs, and each
  launch checks that the created container starts with this step.
- **Per session.** Linux 5.14 and later count the limit per user namespace, and
  the step sets it inside the container's own. The wrapper never uses
  `--ulimit nproc`: the engine applies that limit before it creates the
  container's user namespace, and the kernel then checks every fork against
  the processes of all your containers together (see `docs/validation.md`).
- **Not raisable.** The session cannot raise the limit, because it has no
  capabilities. Its own processes count against it, so slightly fewer than `N`
  processes are left for commands.
- **Exceptions.** A process that host tools start in the container with
  `podman exec` gets the engine's default limits instead. Only the launcher's
  checks and the validation script do that; a session has no engine access to
  its own container.
- **The machine as a whole.** Each session, proxy and engine is bounded
  separately; together they are bounded only by your user's own process
  limit.

The fallback applies only when the engine reports kernel 5.14 or later
(`podman info --format '{{.Host.Kernel}}'`). Older or unrecognized kernels may
count every process of your user, so the process budget then stays unenforced,
and the notice names the reason. The memory and CPU budgets have no fallback.
The provider proxy's process budget uses the same fallback, set by the proxy's
first process. Which mechanism enforces each process budget is part of the
restricted qualification identity.

Risk: without the memory or process budget, a session can exhaust host memory
or processes for your user; without a CPU budget it can saturate every CPU.
Delegating the controllers (for example a systemd
`Delegate=cpu cpuset io memory pids` drop-in for `user@.service`) restores full
enforcement, but the sandbox never requires it.

`CODEX_CONTAINER_RUN_TIMEOUT` optionally sets the session container lifetime in
whole seconds; unset, empty or `0` disables it (the default). When the engine
stops a session at the limit, the wrapper prints
`codex-container: session lifetime limit reached (N s); exit status S` and
returns the Podman client status (255 on the measured Podman 4.9.3).

The writable workspace, or the `--container-git-worktree` parent, is refused
when its physical path is `/`, `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`,
`/sbin`, `/lib`, `/lib64`, `/boot`, `/opt`, `/srv`, `/mnt`, `/media`, `/proc`,
`/sys`, `/dev`, `/run`, `/tmp`, your physical home directory, or a WSL drive
root such as `/mnt/d`. Subdirectories such as `/mnt/d/Workspace/project` are
allowed.

On a WSL drive mount, it also must not be one of these Windows folders, in any
letter case, because drvfs ignores case:

- `/mnt/<drive>/Users`;
- a profile, `/mnt/<drive>/Users/<name>`, its `Documents`, its `OneDrive`
  (also `OneDrive - <organization>`) or `OneDrive/Documents`, which hold the
  PowerShell profile and modules;
- anything inside the profile's `AppData`, which holds the startup folder;
- `/mnt/<drive>/Windows`;
- `/mnt/<drive>/Program Files` or `/mnt/<drive>/Program Files (x86)`;
- `/mnt/<drive>/ProgramData`.

Apart from `AppData`, only these exact folders are refused. A project below
them, such as `/mnt/c/Users/me/projects/app` or
`/mnt/c/Users/me/Documents/GitHub/app`, is accepted. In worktree mode, however, a
project placed directly in a profile is refused, because its parent is the
profile.

Launch from a project directory, or set exactly
`CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` to expose a refused directory
deliberately; the wrapper then prints a warning.

## Toolchains

Sessions can use extra toolchains, such as Java, Go or Python, without Podman
access, an unrestricted network or a rebuilt image. The operator keeps a
toolchain library on the host. Every session sees it read-only, with `nosuid`
and `nodev`, at `/toolchains`. The library is shared by the Claude, Codex,
OpenCode, Pi and Antigravity wrappers. A toolchain adds no network, IPC or
privilege capability: it runs under the same restrictions as the rest of the
session.

- **Location:** `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains`, or
  `CODEX_CONTAINER_TOOLCHAINS_DIR`. The launcher creates it private (`0700`)
  when it is missing. It must stay outside the workspace, the Codex state
  (`CODEX_HOME` or `CODEX_CONTAINER_STATE_DIR`) and the installation. A home
  directory exposed as the workspace with
  `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` contains the default library, so
  that launch stops. Move the library with `CODEX_CONTAINER_TOOLCHAINS_DIR`,
  or omit it.
- **Disable:** `CODEX_CONTAINER_TOOLCHAINS=0` (or `false`, `no`) starts a
  session without the mount.
- **Live updates:** a toolchain added or removed on the host appears in
  running sessions without a restart.

### Managing the library

The operator runs these commands on the host; `--container-toolchain` must be
the first argument:

```bash
codex --container-toolchain add java21            # install or replace a catalog recipe
codex --container-toolchain add ~/recipes/x.json  # install or replace an operator recipe
codex --container-toolchain list                  # installed toolchains, then the catalog
codex --container-toolchain remove java21
codex --container-toolchain verify [java21]       # rerun the checks on the current runtime image
```

An argument without `/` that does not end in `.json` names a recipe of the
release's catalog (see [Recipes](#recipes)); any other argument is a recipe
file. `list` shows the name, version, default flag, size, requirements and
verified base of each installed toolchain, then the catalog recipes that are
not installed.

- **Sources:** a toolchain is a relocatable directory tree, assembled from one
  or more sources: a path inside an OCI image referenced by `@sha256:` digest,
  an HTTPS archive URL with its SHA-256, or a local archive with its SHA-256.
  A toolchain can also, or only, provide container images for the session
  container engine (see [Images](#images)); `list` shows them with the others,
  and `remove` deletes images no other toolchain lists, once no session engine
  runs.
- **Operator recipes:** keep them outside project directories, for example in
  `~/recipes`. A session can write its workspace and state directories, so an
  agent could have written a recipe found there: `add` refuses a recipe file
  inside the directory it runs from (its parent, when setup saved the worktree
  scope) or inside a state directory, before fetching anything. It cannot
  recognize the directories of other projects. Catalog names are not affected,
  and neither are the local archives that a recipe pins by SHA-256.
- **Fetching:** `add` fetches what the recipe names by itself and prints each
  image and URL first. It pulls a missing image and downloads archive URLs
  without `CODEX_CONTAINER_MAINTENANCE`, because the content is fixed by its
  digest or SHA-256 and no code runs while it is fetched and extracted.
  Downloads use HTTPS only and follow redirects only to HTTPS. They trust the
  host CA bundle that setup saved when host CA trust is enabled, and the system
  trust otherwise, and they use the host's proxy variables. Like image builds,
  pulls and downloads happen on the host, outside runtime filtering. `add`
  never builds an image; image builds still require maintenance.
- **Extraction:** every archive is checked against its SHA-256 before anything
  is extracted, and is extracted from a private copy in the library, so a local
  archive changed afterwards cannot reach the toolchain. Extraction rejects
  absolute paths, `..`, device nodes and links that leave the toolchain, and
  clears setuid and setgid bits. A file that two sources provide fails the
  command.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the Codex runtime image, without network and with the session's
  identity and hardening. A toolchain that needs a newer C library than the
  image's glibc fails here. The manifest records the base image from the
  installed `Containerfile`.
- **After an update:** when setup selects a new release, it reruns the check of
  every installed toolchain verified on another base, records the new base
  when the check passes, and prints the result for each. A failed check does
  not fail setup: that toolchain stays visible but loses its default
  environment until `verify` succeeds, and the launcher prints one warning
  naming it. All five wrappers build from the same base, so a toolchain
  verified by another wrapper keeps its default environment here.

### Recipes

The release contains a catalog of reviewed recipes in
`setup/toolchain-catalog/`, shared by every wrapper: `add <name>` installs one
with nothing else to prepare. An operator recipe is a JSON file that the
operator keeps and reviews, and gives to `add` by its path:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | `2`; `[a-z0-9][a-z0-9._-]*`; free version text |
| `sources` | 1 to 16 sources, extracted in order into one toolchain (see below); optional with `images` |
| `images` | 1 to 16 container images for the session container engine (see [Images](#images)) |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown to the agent in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

Each source is one of:

| Source | Keys |
| --- | --- |
| Image | `{"image": "<ref>@sha256:<digest>", "path": "/abs/dir", "target": "rel/dir"}` |
| Archive URL | `{"url": "https://...", "sha256": "<hex>", "path": "member/dir", "target": "rel/dir"}` |
| Local archive | `{"archive": "/abs/file.tar.xz", "sha256": "<hex>", "path": "member/dir", "target": "rel/dir"}` |

- **Placement:** an image source copies the directory `path` of the image. For
  an archive, `path` selects one directory inside it, or `strip_components`
  drops that many leading directories instead. The result goes to `target`
  (default: the toolchain root). Directories of several sources merge; a file
  that two sources provide fails `add`. An archive that several sources use is
  fetched once.
- **Schema 1:** recipes with `"schema": 1` and one `source` object (an image or
  a local archive, with `strip_components`) stay valid.
- **Catalog recipes** use only images and archive URLs, never local files.
- **Protected variables:** recipes cannot set `PATH`, `HOME`, loader, proxy
  or CA variables, any `XDG_` variable (a wrapper may place its state with
  them) or `DBUS_SESSION_BUS_ADDRESS` (no session has a bus). These rules are
  the same in every wrapper. Each wrapper also protects its own variables:
  its prefix, configuration, approval and credential variables, such as
  `CODEX_CONTAINER_*`, `CODEX_HOME`, `CODEX_YOLO` and `OPENAI_API_KEY` here,
  and the agent's own variables that its profile lists in
  `native.protected_env`. For Codex these are every `CODEX_` and `OPENAI_`
  variable (for example `OPENAI_BASE_URL`). `add` rejects them. If another wrapper installed a toolchain that sets one,
  this wrapper leaves that variable out of its sessions and prints a warning
  naming the toolchain; the rest of the toolchain stays available.
- **Default toolchains:** in new sessions, their `PATH` entries come **after**
  the image's. They never replace the runtime's own `node` or `python3`, which
  Codex and the image tools use.
- **Conflicts:** two default toolchains cannot share a command or a variable.
  Install a second version with `"default": false` and use it through its
  `env.sh`.
- **Writable locations:** `/tmp`, `/var/tmp` and `/codex-home` are writable but
  `noexec`, and discarded with the container; the workspace and
  `/codex-home/.codex` persist. Point caches to `/tmp` with literal values, and
  keep executables such as `GOTMPDIR` under the workspace.
- **Dependency downloads** (Maven, npm, pip, Cargo, Go modules) need network
  access that provider and offline modes do not grant. Provide dependencies in
  the workspace, or use an unrestricted session.

#### Images

A recipe can also list container images. Sessions started while the library
holds at least one image get a private container engine that runs them
([Container tests](#container-tests)). Each image is one of:

| Image | Form |
| --- | --- |
| Registry image | `"<ref>@sha256:<digest>"`; a reference without a digest is refused |
| Local image | `{"local": "sha256:<full image ID>", "name": "localhost/<name>[:tag]"}` |

```json
{"schema": 2, "name": "postgres16", "version": "16.4", "default": false,
 "images": ["docker.io/library/postgres@sha256:<digest>"],
 "check": ["podman", "run", "--rm", "--network=none", "docker.io/library/postgres@sha256:<digest>", "postgres", "--version"]}
```

- **Store:** `add` keeps the images in the library's image store, `.images`,
  through a helper container of the engine image. Registry images are pulled on
  the host, with host CA trust when setup enabled it, and keep both their index
  and platform digests. A local image is copied from the host engine by its
  full ID (`podman image inspect --format '{{.Id}}' <image>`) and named as the
  recipe says; `add` fails if the host engine has no image with that ID. An image
  several toolchains list is stored once.
- **Image-only recipes** have no `sources`, `path` or `env`, and `default` must
  be `false`; `toolchains.md` lists their images with a `podman run` example.
- **Check:** for a recipe with images, `check` runs in the runtime image against
  a temporary engine like a session's, without network, so a check that runs
  the image proves it runs offline.
- **Live updates:** an image added while sessions run is usable by their engines
  at once. Removing an image, or replacing a toolchain with one that drops an
  image, waits until no session engine runs: the command fails and names the
  running sessions.
- **Catalog recipes** never list local images.
- **Cleanup:** image layers in `.images` can belong to your subordinate IDs, as in
  any rootless Podman storage. Remove image toolchains with `remove`, which
  deletes their layers through the helper; deleting the directory directly needs
  `podman unshare rm -rf`.

The catalog recipes pin the versions, digests and checksums below; the
recipe files hold the full values. See [the validation
record](docs/validation.md#toolchain-library-2026-11-13) for the checks.

| Name | Version | Source | Default | Notes |
| --- | --- | --- | --- | --- |
| `java21` | Temurin 21.0.13 | image `eclipse-temurin@sha256:0a3f3298…`, `/opt/java/openjdk` | yes | `JAVA_HOME` |
| `maven3.9` | 3.9.16 | image `maven@sha256:99e61abc…`, `/usr/share/maven` | yes | requires `java21`; local repository in `/tmp/m2`; harmless jansi warning |
| `go` | 1.27.4 | image `golang@sha256:4fa7c968…`, `/usr/local/go` | yes | `GOTOOLCHAIN=local`; caches in `/tmp`; `go test` needs `GOTMPDIR` in the workspace |
| `node24` | 24.22.3 | archive `node-v24.22.3-linux-x64.tar.xz` from `nodejs.org` | no | the image's Node.js 22 stays first |
| `python3.13` | 3.13.18 | python-build-standalone `20261110` `install_only` archive from GitHub | no | the image's `python3` stays first; virtual environments in the workspace |
| `rust` | 1.100.0 | `rustc`, `cargo` and `rust-std` (host and `x86_64-unknown-linux-musl`) archives from `static.rust-lang.org` | yes | target `x86_64-unknown-linux-musl` linked by `rust-lld`; crates with build scripts or procedural macros fail |

The runtime image has no C linker, so the `rust` recipe uses the musl target,
whose startup files ship with Rust, and links with `rust-lld`.

### Telling the agent

The wrapper never edits `AGENTS.md` or other instruction files. The library
contains a generated `/toolchains/toolchains.md` with the usage rules and every
installed toolchain, plus a machine-readable `/toolchains/index.json`. Add one
line to the project's `AGENTS.md` or to `$CODEX_HOME/AGENTS.md`:

```markdown
Read /toolchains/toolchains.md before using or looking for build tools.
```

The agent then runs a toolchain in one command with
`. /toolchains/<name>/env.sh && <command>`. This form also works for
toolchains added after the session started.

SELinux and AppArmor enforcement were not tested with the library mount. On
hosts that enforce them, profile the tools you add.

## Shared sandbox components and the agent profile

`network/`, `setup/`, `launcher/` and the shared tests come unchanged from the
reference repository `sandbox-container` and are shared with the Claude,
Antigravity, OpenCode and Pi wrappers. They contain no Codex-specific names.
`launcher/core.sh` is the whole launcher: `codex-container.sh` is the thin
entry script every wrapper shares, and `agent/launcher.sh` holds the profile
values the core needs plus Codex's three hooks. They document `CODEX_YOLO` and
turn it into `--yolo`, and add the protected Codex arguments: in offline and
provider sessions `--no-daemon -c sandbox_mode="danger-full-access"`, and in
provider sessions also the `-c` overrides that disable optional traffic
(`docs/launcher-contract.md` in `sandbox-container`). The shared launcher tests
(`tests/test_launcher.py`, with the fake engine `tests/fake_podman.py`) run the
core against fixture agent parts; `tests/test_wrapper.py` covers only Codex's
part. Every other agent-specific value is declared in `agent/profile.json`.

## Included Tools

The image includes Node.js/npm, Python 3, Codex CLI, the OpenSpec CLI
(`openspec`), the Podman client, Bubblewrap (`bwrap`), local Git, Bash, search
and editing tools (`ripgrep`, `grep`, `sed`, `gawk`, `find`, `patch`, `diff`),
archive tools (`tar`, `gzip`, `bzip2`, `xz`, `zip`, `unzip`), JSON support
(`jq`), HTTP/TLS support (`curl`, CA certificates), diagnostics (`procps`,
`util-linux`, `file`, `less`), and standard POSIX utilities.

Image inputs are pinned in `Containerfile`: the `node:22-bookworm-slim` base by
digest, Codex CLI by `CODEX_VERSION` and OpenSpec by `OPENSPEC_VERSION`.
`tests/test_image_pins.py` rejects floating tags, `@latest` and version ranges.
Codex cannot update itself inside a session because the image root is read-only.
With OpenSpec 2.0.0, invoke the project's OpenSpec skills as `$openspec-*`.

### Updating pinned image inputs

1. Change `CODEX_VERSION`, `OPENSPEC_VERSION` or the base digest in
   `Containerfile`; resolve a new digest with
   `podman pull docker.io/library/node:22-bookworm-slim` and
   `podman image inspect --format '{{.Digest}}'`.
2. Rebuild explicitly with `./codex-container.sh --container-build`.
3. Check `codex --version` and `openspec --version` in the image, then rerun the
   credential-free suites and `bash tests/run-runtime.sh`.
4. Record the tested versions, digest and results with the date in
   `docs/validation.md`.

## Verification

Run credential-free wrapper tests using standard-library Python:

```bash
python3 -B -m unittest discover -s tests -p test_launcher.py -v
python3 -B -m unittest discover -s tests -p test_wrapper.py -v
python3 -B -m unittest discover -s tests -p test_image_pins.py -v
python3 -B -m unittest discover -s tests -p test_reference_copy.py -v
bash -n codex-container.sh launcher/core.sh agent/launcher.sh tests/run-runtime.sh
git diff --check
openspec validate --specs --strict
```

`tests/run-runtime.sh` runs the suites in a disposable runner container with
native volume storage, which also avoids a caller whose `/tmp` is `noexec` or
whose workspace cannot bind Unix sockets:

```bash
bash tests/run-runtime.sh --wrapper              # shared launcher and wrapper suites
bash tests/run-runtime.sh --shared               # copied shared suites
bash tests/run-runtime.sh --network-policy       # protected policy paths
bash tests/run-runtime.sh --mux                  # multiplexed relay
bash tests/run-runtime.sh --network-feasibility  # isolated topology
bash tests/run-runtime.sh --guard                # static guard (toolchain image)
bash tests/run-runtime.sh --qualification        # local qualification gate
bash tests/run-runtime.sh --setup                # shared setup suite
bash tests/run-runtime.sh --setup-runtime        # real setup acceptance
bash tests/run-runtime.sh --network              # restricted wrapper acceptance
```

The restricted modes build a disposable guard and proxy, qualify a disposable
installation and use a local TLS fixture with a synthetic Responses API; they
need no credentials and send no model requests to OpenAI.

The wrapper suite uses synthetic Podman responses; it does not prove real
mount or namespace enforcement. Wrong-owner and non-enforcing filesystem
branches use controlled metadata fixtures. Run the opt-in runtime suite
separately against a built image and a usable same-host rootless service:

```bash
# Build once, without real Codex state or authentication:
CODEX_CONTAINER_NETWORK=unrestricted CODEX_CONTAINER_MAINTENANCE=1 bash ./codex-container.sh --container-build
# Native Linux test storage, also visible at this path to the host service:
CODEX_TEST_ROOT="$HOME/.local/share/codex-container-tests" \
CODEX_RUNTIME_TESTS=1 python3 -B -m unittest discover -s tests -p test_runtime.py -v
# Or use a disposable native Linux Podman volume (also works from a container):
bash tests/run-runtime.sh
```

The runtime suite reaches the launch service through a Unix `CONTAINER_HOST`,
else through the runtime directory's socket (`XDG_RUNTIME_DIR` or
`/run/user/<uid>`). Its session engine cases need the engine image
(`localhost/codex-cli-engine:latest`) and the pinned alpine sample image in that
engine; without them they skip, asking to prepare the image.
`CODEX_CONTAINER_IMAGE` selects the image for both runners. Explicitly enabled
tests fail if prerequisites are missing; without opt-in they are skipped.
Projects and state are disposable, and the suite starts only shell sessions
and `codex --version`, without loading real credentials or submitting requests.
It tests both pseudo-terminal attachment and redirected stdin. Use
the volume runner if the workspace filesystem cannot enforce state privacy,
or if the host has no Python. The checkout, test root, and build context must
retain their host absolute paths when using a containerized caller.

Checks cover real mount boundaries, identity, persistent state, all ephemeral
locations, tmpfs capacities and `noexec`, concurrent naming, signals and owned
cleanup, exit 125, build-context exclusion, linked Git worktrees,
a caller with a remapped Unix service socket, zero capabilities and
no-new-privileges, effective cgroup v2 budgets and process-limit enforcement,
Codex's own sandbox and Bubblewrap without capabilities, the refusal of the
removed delegation opt-in, the session container engine, the lifetime limit
and the refused home workspace. Exact results and unavailable checks are recorded in
[docs/validation.md](docs/validation.md).
