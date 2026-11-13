# Codex CLI in Podman

`codex-container.sh` runs Codex CLI in a rootless Podman container. The
image filesystem is read-only, with writable workspace, Codex state, and
temporary storage. Every launch selects a network mode explicitly:
`offline`, `provider` (only the OpenAI hosts of one protected profile) or
`unrestricted` (ordinary networking, the previous behavior); see
[Network modes](#network-modes). In `unrestricted` mode, set
`CODEX_CONTAINER_PODMAN=1` to expose the host Podman socket and let Codex launch
containers for tests and builds. The Podman command remains installed in every
mode.

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
or startup, including shell mode and sessions without delegated Podman access.
It requires explicit Linux/rootless information and a recognized
`Host.ServiceIsRemote` boolean. Failed queries and unverifiable results stop
startup. Local Podman requires no API service. An explicit absolute Unix
`CONTAINER_HOST` is supported for a service on the same host, including callers
inside another container; that launch connection still requires its service
when delegation to the Codex session is disabled. Named connections through
`CONTAINER_CONNECTION`, TCP/SSH endpoints, and implicit remote contexts are
rejected. Forwarded Unix sockets to other hosts are unsupported: Unix transport
alone does not prove that the service is on the same physical host.

Unix launch endpoints must contain an absolute socket path beyond `/`.
`unix://`, `unix:///`, and longer slash-only forms such as `unix:////` are
rejected before any Podman query. Valid absolute paths are preserved as supplied.

Verification preserves record boundaries: the launch response has one record,
and Codex's delegated response has two (`true`, then the absolute host socket
path, including any spaces). Either response can omit its final LF or end in
exactly one LF. Additional blank or nonblank records and CR characters are
rejected before image operations or startup. A failed query remains an error
even if its output looks valid.

## Optional host Podman API access

Default local sessions do not require an API service or socket. Skip this section
and continue to Usage unless you want to enable `CODEX_CONTAINER_PODMAN=1`.
Host Podman is still required to build and launch the Codex container.

With that opt-in, socket selection uses the first nonempty choice:

1. `CODEX_CONTAINER_PODMAN_SOCKET`, an absolute socket path.
2. The path from an explicit Unix `CONTAINER_HOST` used by the caller.
3. `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock`.

The override affects delegation only, not the launch engine. Empty overrides
fall through. Socket selection and verification are skipped entirely when
delegation is disabled. Choose **one** of the following service setup methods.

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

### Verify the socket before enabling host access

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${CODEX_CONTAINER_PODMAN_SOCKET:-${CONTAINER_HOST#unix://}}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info \
    --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true` followed by an absolute host-side socket path. A socket file alone does
not prove that a service is listening
or that its engine is rootless. With `CODEX_CONTAINER_PODMAN=1`, the wrapper
automatically queries the selected socket explicitly before image inspection,
building, or startup, in both Codex and shell modes, including `--container-build`.
It rejects rootful services, failed queries, and empty or unexpected results.
If the API command fails, check socket permissions, the systemd status, or
the foreground service output above. If rootless is `false`, start the service
as your normal non-root user. If the result is empty or unexpected, check
that the service supports reporting `Host.Security.Rootless` as `true`.

The client-visible socket is canonicalized and must be readable and writable.
The wrapper mounts the service's reported `Host.RemoteSocket.Path`, which may
be different when the caller itself runs in a container. Missing or relative
host-side paths fail startup. The reported path is interpreted by the launch
engine, not checked for existence in the caller's namespace. Both services
must run on the same host, with workspace, state, and build context available
at their host absolute paths; socket remapping does not translate those paths.
For an explicit delegation override:

```bash
CODEX_CONTAINER_PODMAN=1 \
CODEX_CONTAINER_PODMAN_SOCKET="/absolute/path/to/podman.sock" ./codex-container.sh
```

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
state, Podman endpoint, delegation, YOLO, worktree scope, budgets, lifetime and
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

Every ordinary launch needs a nonempty `CODEX_CONTAINER_NETWORK`, explicit or
supplied by the managed launcher. An unset or empty mode stops with
`setup required:` guidance before any engine call or state creation;
`unrestricted` keeps the previous networking behavior. Unknown values
fail before image operations.

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

The default-deny `.containerignore` admits only `Containerfile`,
`.containerignore` and the two relay inputs `network/relay.py` and
`network/mux.py`, which the image copies to `/opt/sandbox-egress/`. Git
metadata, local configuration, state, credentials, the guard binary, policies,
caches, tests, documentation, and other files are excluded, including nested
and newly added files. Future local `COPY` or `ADD` inputs must be deliberately
included in `.containerignore`. This policy filters builds; it does not
restrict runtime workspace mounts.

To allow access to the host Podman service, complete the optional socket setup
and verification, then use:

```bash
CODEX_CONTAINER_NETWORK=unrestricted CODEX_CONTAINER_PODMAN=1 ./codex-container.sh
CODEX_CONTAINER_NETWORK=unrestricted CODEX_CONTAINER_PODMAN=1 ./codex-container.sh --container-shell
```

Delegation is available only with explicit `unrestricted` networking: in
`offline` and `provider` the wrapper rejects `CODEX_CONTAINER_PODMAN=1` before
image or resource operations, because the host API bypasses egress
enforcement. Only the exact value `1` enables this integration. Unset, empty,
and all other values (including `true`) disable it: the wrapper does not
validate or mount the API socket and removes `CONTAINER_HOST` from the session
environment.
Existing users who launch child containers through the host service must now
set `CODEX_CONTAINER_PODMAN=1`. Both modes use the same image, and
`CODEX_CONTAINER_IMAGE` continues to override its name.

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

Each container is named from the last component of the physical current directory
and the next highest supported numeric index among running and stopped
containers, for example `codex-container-0`, `codex-container-1`. Suffixes of
one to nine decimal digits count (`08` means eight); malformed or longer
suffixes are ignored. Enumeration errors stop startup. Creation reserves the
name atomically, with at most 20 attempts for confirmed collisions. Other
creation or collision-check errors stop startup without replacing any container.

The wrapper tracks the full ID of the container it created and attempts cleanup
on exit, failed startup, or handled interruption. It never removes another
container to obtain a name. Application exit codes, including 125, pass through
without retrying execution, and cleanup failures do not replace that status.
TERM, INT, and HUP sent to the wrapper are forwarded to its running container;
wrapper interruption exits are 143, 130, and 129 respectively. A signal during
creation allows up to five seconds for the client to finish, then sends TERM
to the local client, allows up to five more seconds before KILL, and allows
one further second to observe termination. The wrapper then recovers any full
owned ID from its private CID file and attempts removal without starting the
application. The first signal selects the interruption status; repeated signals
do not renew deadlines or replace that status. A client that cannot be reaped
within its limit is reported rather than waited on indefinitely.

After forwarding a signal, graceful shutdown allows up to five seconds before
forced removal. Engine control commands have five-second deadlines (plus a
one-second forced termination allowance); local client cancellation allows
five seconds after TERM and one further second after KILL. These are separate
phases, not a five-second total deadline.
SIGKILL, host failure, or engine loss can leave residual containers; failed
cleanup reports the owned ID for explicit removal. Cancelling the local client
does not prove the engine stopped creating the container. Without a verified
owned ID, the wrapper reports an unresolved creation outcome and requires
explicit engine inspection; it never removes by a guessed name. Interrupted
creation budgets up to 17 seconds across completion, client cancellation/reaping,
and removal, excluding scheduling overhead. Uninterrupted creation has no new
timeout. Normal engine auto-removal remains enabled.

Both Codex and shell modes allocate a TTY only when stdin and stdout are
terminals. Pipes, file input, and redirected output retain stdin forwarding and
EOF without requesting a TTY. Commands that themselves require a terminal still
need one. For example, run shell commands from a file:

```bash
printf 'pwd\nexit 0\n' | ./codex-container.sh --container-shell
./codex-container.sh --container-shell < commands.sh > session.log
```

`CODEX_YOLO=1` starts Codex with `--yolo`, disabling approvals and sandboxing.
`CODEX_YOLO` accepts `1`, `true`, and `yes` to enable it, and unset, empty,
`0`, `false`, or `no` to disable it. Words are case-insensitive, so `TrUe`
and `YeS` enable it and `FaLsE` and `nO` disable it. Other values, including
words surrounded by spaces, stop startup with an error. Shell mode validates
the value but does not add Codex arguments. This parsing does not change the
exact `CODEX_CONTAINER_PODMAN=1` opt-in or explicit native CLI arguments.
Use it only when the container and its mounts are considered an isolated,
trusted environment.
The image filesystem remains read-only even with `CODEX_YOLO=1`.

Approvals, the CLI's internal sandbox, and outer container isolation are
separate controls. With `CODEX_YOLO` disabled, native arguments and saved CLI
settings still apply; the wrapper does not override them to enforce a policy.
Installing Bubblewrap or passing a basic namespace probe does not establish
that an actual CLI sandboxed operation succeeds. Check the operation and its
output independently; no Antigravity-specific seccomp workaround is applied.

| `CODEX_YOLO` | `CODEX_CONTAINER_PODMAN` | Session behavior |
| --- | --- | --- |
| Disabled | Disabled | Native CLI settings; no delegated socket |
| Enabled | Disabled | `--yolo`; no delegated socket |
| Disabled | Exactly `1` | Native CLI settings; host service access |
| Enabled | Exactly `1` | `--yolo` and host service access |

```bash
./codex-container.sh
CODEX_YOLO=1 ./codex-container.sh
CODEX_CONTAINER_PODMAN=1 ./codex-container.sh
CODEX_YOLO=1 CODEX_CONTAINER_PODMAN=1 ./codex-container.sh
```

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
and sessions without copying existing data. Inside the container it is always
`/codex-home/.codex`; the rest of `/codex-home` is ephemeral.

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

For a fully isolated application home, set `CODEX_CONTAINER_STATE_DIR`
instead of `CODEX_HOME`:

```bash
unset CODEX_HOME
CODEX_CONTAINER_STATE_DIR="$HOME/.local/share/codex-container/isolated" ./codex-container.sh
```

The directory is mounted read/write at `/codex-home` (with
`CODEX_HOME=/codex-home/.codex`), so caches and other home data persist with
it. The shared `~/.codex` is neither mounted nor imported: sign in again
inside the isolated home. A simultaneous nonempty `CODEX_HOME` is a conflict
error. The wrapper creates the home and its `.codex` privately, applies the
same ownership and mode checks to both, never repairs permissions, and rejects
`.codex` or the CA mount parent if a symbolic link resolves outside the home.

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

## Network modes

| `CODEX_CONTAINER_NETWORK` | Agent network access | Host Podman delegation |
| --- | --- | --- |
| unset or empty | Launch stops with setup guidance before engine calls and state creation | No session |
| `offline` | Own loopback, pipes and connected socket pairs only | Rejected |
| `provider` | As offline, plus one preconnected channel to an exact-destination proxy | Rejected |
| `unrestricted` | Ordinary runtime networking (the previous behavior) | Exact opt-in allowed |

**Migration.** Existing launches must add `CODEX_CONTAINER_NETWORK=unrestricted`
to keep today's networking, and `CODEX_CONTAINER_MAINTENANCE=1` to commands that
build the image. Restricted failures never fall back to unrestricted
networking. Offline sessions cannot reach the OpenAI API.

The restricted implementation is shared with `claude-container` and copied
unchanged from its tag `sandbox-ref-14`; see
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

`developers.openai.com` serves the OpenAI documentation MCP server
(`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`).
Its client uses the relay, and Codex 0.167.0 reached only
`developers.openai.com` for it. `openai-account` includes it, so account users
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

The policy revision is `openai-2026-11-11-v1`, measured against Codex 0.167.0.
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

Codex's command sandbox cannot run under the guard. With Codex 0.167.0 the
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

## Mounts and security

Both Codex and shell sessions use a read-only image root filesystem. The
workspace and persistent Codex state remain writable host binds. `/tmp`,
`/var/tmp`, `/run`, and `/codex-home` use writable temporary filesystems;
files there are discarded when the container is removed, except for the
nested persistent mount at `/codex-home/.codex`. Temporary build artifacts
can execute in `/tmp`, `/var/tmp`, and `/codex-home`.

`/tmp` and `/var/tmp` each have a 512 MiB maximum and `/run` a 32 MiB maximum.
All three retain mode 1777, `nosuid`, and `nodev`; `/tmp` and `/var/tmp` retain
executable storage and `/run` keeps its existing execution policy. These are
per-mount capacities, not reserved memory or a total container memory limit.
Ephemeral home has no explicit capacity imposed by this policy. Writes can fail
when a bounded mount fills; workspace and persistent state remain separate host
storage.

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
the host Podman service. Persistent configuration is stored in
`~/.codex` (or the host `CODEX_HOME` override), mounted at
`/codex-home/.codex`, and also selected through the container's `CODEX_HOME`.

When enabled, the socket gives Codex control over containers and volumes
available to the host Podman user. Without the opt-in, the client is still
installed, but the wrapper supplies no connection to that service. With the
socket enabled, the agent can request new host bind mounts beyond the workspace
using that service user's authority. Rootless delegation cannot enforce
project-only filesystem access. This controls the wrapper's socket integration;
it does not block independently
configured endpoints or sockets exposed through workspace files. The wrapper
does not use `--privileged` and does not install SSH clients or remote
repository configuration.

With `--container-git-worktree`, the selected parent is exposed read/write with
all files beneath it. Use the flag from a directory whose parent you intend to
expose. Sensitive roots are refused (see below); writable binds take precedence
over image paths they cover, so an explicitly allowed `/` would mask the image
root and the read-only image policy would not make such host files immutable.

### Session hardening, budgets and lifetime

Every Codex and shell session, with or without Podman delegation and YOLO, runs
with `--cap-drop=all` and `--security-opt=no-new-privileges`. The container has
no capabilities and cannot gain privileges through set-user-ID programs. Codex's
own Linux command sandbox, Bubblewrap, Git, OpenSpec and the delegated Podman
client work under these settings. The wrapper never adds capabilities back to
work around a tool; such a limitation is documented in `docs/validation.md`.
Delegation still grants host engine authority beyond these limits.

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
and 256 MiB limits. Without the memory or process budget, a session can exhaust
host memory or processes for your user. After creating the container, the
wrapper checks that every enforced budget was applied and that no unenforced one
is present, and stops before Codex starts otherwise. Restricted qualification
records the enforced set, so a change in delegation requires requalification.
Budgets and tmpfs sizes do not limit workspace or `CODEX_HOME` storage growth.

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
allowed. Launch from a project directory, or set exactly
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
codex --container-toolchain add java21.json   # install or replace from a recipe
codex --container-toolchain list              # name, version, default, size, verified base
codex --container-toolchain remove java21
codex --container-toolchain verify [java21]   # rerun the checks on the current runtime image
```

- **Sources:** a toolchain is a relocatable directory tree, taken either from
  a path inside an OCI image referenced by `@sha256:` digest, or from a local
  archive with its SHA-256. The command never downloads archives.
- **Pulls:** pulling a missing image requires exact
  `CODEX_CONTAINER_MAINTENANCE=1`. Like image builds, the pull happens on the
  host, outside runtime filtering.
- **Extraction:** it rejects absolute paths, `..`, device nodes and links
  that leave the toolchain, and clears setuid and setgid bits.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the Codex runtime image, without network and with the session's
  identity and hardening. A toolchain that needs a newer C library than the
  image's glibc fails here. The manifest records the base image from the
  installed `Containerfile`. If that base changes, the toolchain stays visible
  but loses its default environment until `verify` succeeds, and the launcher
  prints one warning naming it. All five wrappers build from the same base, so
  a toolchain verified by another wrapper keeps its default environment here.

### Recipes

A recipe is a JSON file that the operator keeps and reviews:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | `1`; `[a-z0-9][a-z0-9._-]*`; free version text |
| `source` | `{"image": "<ref>@sha256:<digest>", "path": "/abs/path"}` or `{"archive": "/abs/file.tar.xz", "sha256": "<hex>", "strip_components": 1}` |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown to the agent in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

- **Protected variables:** recipes cannot set `PATH`, `HOME`, `CODEX_HOME`,
  `CODEX_YOLO`, `OPENAI_API_KEY`, loader, proxy, CA or `CODEX_CONTAINER_*`
  variables.
- **Default toolchains:** in new sessions, their `PATH` entries come **after**
  the image's. They never replace the runtime's own `node` or `python3`, which
  Codex and the image tools use.
- **Conflicts:** two default toolchains cannot share a command or a variable.
  Install a second version with `"default": false` and use it through its
  `env.sh`.
- **Writable locations:** `/tmp`, `/var/tmp` and `/codex-home` are writable and
  executable in Codex sessions, but discarded with the container; the workspace
  and `/codex-home/.codex` persist. Recipes shared with other wrappers should
  still point caches to `/tmp` with literal values, and keep notes such as
  `GOTMPDIR` under the workspace, because `/tmp` is `noexec` in some of them.
- **Dependency downloads** (Maven, npm, pip, Cargo, Go modules) need network
  access that provider and offline modes do not grant. Provide dependencies in
  the workspace, or use an unrestricted session.

The verified example recipes (Temurin 21, Maven 3.9, Go, Node.js 24,
Python 3.13 and Rust) are kept in the reference repository, in
[`claude-container/docs/toolchains/`](https://github.com/yarilc/claude-container/tree/main/docs/toolchains),
with their versions, digests, checksums and usage notes in its
[README "Toolchains" section](https://github.com/yarilc/claude-container#toolchains).
They do not depend on the agent.

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
python3 -B -m unittest discover -s tests -p test_wrapper.py -v
python3 -B -m unittest discover -s tests -p test_image_pins.py -v
python3 -B -m unittest discover -s tests -p test_reference_copy.py -v
bash -n codex-container.sh tests/run-runtime.sh
git diff --check
openspec validate --specs --strict
```

`tests/run-runtime.sh` runs the suites in a disposable runner container with
native volume storage, which also avoids a caller whose `/tmp` is `noexec` or
whose workspace cannot bind Unix sockets:

```bash
bash tests/run-runtime.sh --wrapper              # wrapper suite
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
podman build --tag localhost/codex-cli:latest --file Containerfile .
# Native Linux test storage, also visible at this path to the host service:
CODEX_TEST_ROOT="$HOME/.local/share/codex-container-tests" \
CODEX_RUNTIME_TESTS=1 python3 -B -m unittest discover -s tests -p test_runtime.py -v
# Or use a disposable native Linux Podman volume (also works from a container):
bash tests/run-runtime.sh
```

The runtime suite requires a reachable delegation socket and supports the same
`CODEX_CONTAINER_PODMAN_SOCKET`, Unix `CONTAINER_HOST`, and XDG/UID defaults.
`CODEX_CONTAINER_IMAGE` selects the image for both runners. Explicitly enabled
tests fail if prerequisites are missing; without opt-in they are skipped.
Projects and state are disposable, and the suite starts only shell sessions
and `codex --version`, without loading real credentials or submitting requests.
It tests both pseudo-terminal attachment and redirected stdin. Use
the volume runner if the workspace filesystem cannot enforce state privacy,
or if the host has no Python. The checkout, test root, and build context must
retain their host absolute paths when using a containerized caller.

Checks cover real mount boundaries, identity, persistent state, all ephemeral
locations, tmpfs capacities and execution, concurrent naming, signals and owned
cleanup, exit 125, build-context exclusion, linked Git worktrees, child binds,
a caller with a remapped Unix service socket, zero capabilities and
no-new-privileges, effective cgroup v2 budgets and process-limit enforcement,
Codex's own sandbox, Bubblewrap and delegated children without capabilities,
the lifetime limit and the refused home workspace. Exact results and unavailable checks are recorded in
[docs/validation.md](docs/validation.md).
