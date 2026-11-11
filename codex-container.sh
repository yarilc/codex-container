#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: codex-container.sh [container option] [codex arguments...]

Runs Codex with a read-only image filesystem. The current directory (or its
parent with --container-git-worktree) and CODEX_HOME are mounted read/write.
/tmp, /var/tmp, /run, and HOME outside CODEX_HOME are writable and ephemeral.
/tmp and /var/tmp are each limited to 512 MiB, /run to 32 MiB (per-mount maxima).
TTY allocation requires terminal stdin and stdout; redirected stdin is retained.
CODEX_HOME must be caller-owned, accessible, and private (no group/other
permissions). Missing state is created with mode 0700; existing state is not
repaired automatically. Use private Linux storage if Unix modes are ignored.
Podman is installed; host socket access requires CODEX_CONTAINER_PODMAN=1.
Builds and sessions always require a verified Linux rootless launch engine.
Use local Podman or an explicit same-host Unix CONTAINER_HOST; named and
TCP/SSH connections are not supported. A Unix launch connection requires
an absolute socket path beyond / and its service, even without session access.
Enabled access verifies that the socket serves a reachable rootless engine;
rootful or unverifiable services stop startup before image operations.
Verification expects one launch record or two delegated-socket records, with
an optional single final LF. Additional records or CR characters are rejected.

Container options:
  --container-setup      interactively prepare a complete user installation and
                         its managed launcher; must be used alone
  --container-qualify    verify a prepared restricted installation with fixed
                         local controls; must be used alone
  --container-build      build or refresh the container image before starting
  --container-shell      open a shell instead of starting Codex
  --container-git-worktree mount the parent of the current physical directory
                         read/write; the container starts in the current directory
  --container-help       show this wrapper help

All other arguments are passed to Codex unchanged.
TERM/INT/HUP are forwarded to the owned session; interruption exits are
143/130/129. Graceful shutdown allows five seconds before forced cleanup.
Interrupted creation allows five seconds to finish, then cancels its client
with TERM (five seconds) and KILL (one second to observe termination).
Owned removal allows five seconds plus one second for forced client termination.
Repeated signals preserve the first status and do not renew these deadlines.
Creation without a verified owned ID is reported for explicit engine inspection;
local client cancellation does not prove the engine request stopped.
Only this invocation's container is removed. SIGKILL or engine loss can leave
residual containers requiring explicit cleanup.

Environment:
  CODEX_CONTAINER_NETWORK offline, provider, or unrestricted; required for every
                         launch (unrestricted is the previous behavior)
  CODEX_CONTAINER_NETWORK_PROFILE protected provider policy profile name
                         (openai-api or openai-account; openai-account and
                         the extension openai-api-docs also allow the OpenAI
                         documentation MCP at developers.openai.com)
  CODEX_CONTAINER_NETWORK_POLICY absolute operator policy JSON path
  CODEX_CONTAINER_NETWORK_RUNTIME_DIR private native directory at its host path
  CODEX_CONTAINER_EGRESS_IMAGE immutable proxy image ID or registry digest
  CODEX_CONTAINER_MAINTENANCE authorize image builds and proxy pulls only with
                         exact value 1, including the build of a missing image
  CODEX_CONTAINER_IMAGE  image name (default: localhost/codex-cli:latest)
  CODEX_CONTAINER_PODMAN expose the host Podman socket only when exactly 1
                         (default: disabled; other values also disable access);
                         rejected in offline and provider modes
  CODEX_CONTAINER_PODMAN_SOCKET absolute socket override for enabled access
                         (then Unix CONTAINER_HOST, then XDG_RUNTIME_DIR or
                         /run/user/<uid>, with /podman/podman.sock appended)
  CODEX_HOME             Codex home on the host (default: ~/.codex)
  CODEX_CONTAINER_STATE_DIR optional isolated home mounted at /codex-home;
                         conflicts with a nonempty CODEX_HOME; no state is imported
  CODEX_CONTAINER_TRUST_HOST_CA trust a host CA bundle: 1, true, or yes
                         (default: disabled)
  CODEX_CONTAINER_CA_BUNDLE CA bundle file to trust (default: first of
                         /etc/ssl/certs/ca-certificates.crt and
                         /etc/pki/tls/certs/ca-bundle.crt)
  CODEX_YOLO             enable Codex --yolo (default: disabled)
                         1/true/yes enable; empty/0/false/no disable
                         words are case-insensitive; other values are errors
  CODEX_CONTAINER_MEMORY_LIMIT session memory, integer with k/m/g unit (default: 4g)
  CODEX_CONTAINER_CPU_LIMIT    session CPUs, up to 3 decimals (default: 2)
  CODEX_CONTAINER_PIDS_LIMIT   session process limit (default: 512)
                         Budgets cannot be disabled; they require delegated
                         rootless cgroup v2 cpu/memory/pids controllers
  CODEX_CONTAINER_RUN_TIMEOUT  session container lifetime in whole seconds
                         (default: 0, disabled by default)
  CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE exact 1 permits a refused sensitive
                         workspace with a warning (default: disabled)
  OPENAI_API_KEY         forwarded only to provider sessions using openai-api
                         or openai-api-docs

New users must first run: bash ./codex-container.sh --container-setup
Then use the managed launch command printed by setup (by default
~/.local/bin/codex-container) from your workspace. An ordinary launch with an
unset or empty CODEX_CONTAINER_NETWORK stops with setup guidance before runtime
checks or state creation.

Direct operator launches remain available with an explicit mode.
Migration: every direct launch needs an explicit CODEX_CONTAINER_NETWORK. Set
CODEX_CONTAINER_NETWORK=unrestricted to keep the previous networking behavior,
and add CODEX_CONTAINER_MAINTENANCE=1 to commands that build the image, e.g.:
  CODEX_CONTAINER_NETWORK=unrestricted CODEX_CONTAINER_MAINTENANCE=1 bash ./codex-container.sh --container-build
Offline sessions cannot reach the OpenAI API. Restricted failures never retry
unrestricted networking.

Socket access permits new host mounts beyond the workspace with the service
user's authority. YOLO and socket access are independent. The service reports
the host-side socket source; containerized callers must preserve host absolute
workspace and state paths. Every session drops all capabilities and sets
no-new-privileges; no security-policy overrides are added. Budgets and tmpfs
sizes do not limit workspace or CODEX_HOME storage growth.
The writable workspace (or worktree parent) must not physically be /, /home,
/root, /etc, /usr, /var, /bin, /sbin, /lib, /lib64, /boot, /opt, /srv, /mnt,
/media, /proc, /sys, /dev, /run, /tmp, the caller's home or a /mnt/<letter>
drive root; descendants such as /mnt/d/project are allowed.
When the lifetime limit stops a session, a notice is printed and the engine
client's exit status is returned.

Restricted modes (offline, provider) require host Python 3, a same-host Unix
rootless Netavark service with Podman >= 4.9, standard OCI seccomp, usable
Landlock ABI >= 3, a protected installation outside writable workspace/state
trees, a static guard and SHA-256 manifest in network/bin, and a current local
qualification report (run --container-qualify alone after preparation or
relevant updates). Changed boot, engine/backend/security, code/images,
policy/profile, CA trust or hardening invalidates the report; an unidentifiable
active LSM policy requires the gate on each launch. Locally-qualified
installations are distinguished from release-measured acceptance records.
Provider mode uses an external CONNECT proxy that binds the TLS server name
(initial and retried ClientHello) to the CONNECT host before forwarding; it
does not prove exclusive OpenAI application access. Allowed services can receive
data: an injected agent can send workspace data to an allowed host (openai-api:
api.openai.com; openai-account: auth.openai.com, chatgpt.com and
developers.openai.com; openai-api-docs adds developers.openai.com) with an attacker's key or account. Only offline removes this. Provider-hosted tools such as web
search run at the provider, outside this boundary. Provider sessions disable
update checks, analytics, feedback, OTEL export, connectors and remote plugins
with -c overrides placed before your arguments; the writable config.toml cannot
override them. ChatGPT browser sign-in is unsupported in the container; use
"codex login --device-auth" or an API key. Codex's own command sandbox cannot
run under the guard (it needs Netlink or Bubblewrap); offline and provider
launches add a protected --no-daemon and -c sandbox_mode="danger-full-access"
before your arguments (the shared background server needs a Unix listener the
guard denies), and the guard remains the enforced boundary. See network/README.md and
docs/network-contract.md.
EOF
}

die() { printf 'codex-container: %s\n' "$*" >&2; exit 1; }

# Help takes precedence regardless of option order and never needs Podman.
for arg in "$@"; do
    [[ "$arg" != --container-help ]] || { usage; exit 0; }
done
for arg in "$@"; do
    if [[ "$arg" == --container-qualify ]]; then
        [[ $# == 1 ]] || die '--container-qualify must be used alone'
        command -v python3 >/dev/null || die 'host Python 3 is required for qualification'
        script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
        script_dir=$(dirname -- "$script_path")
        exec python3 -I "$script_dir/network/qualify.py" qualify
    fi
done
for arg in "$@"; do
    if [[ "$arg" == --container-setup ]]; then
        [[ $# == 1 ]] || die '--container-setup must be used alone'
        [[ -t 0 && -t 1 ]] || die '--container-setup requires an interactive terminal'
        command -v python3 >/dev/null || die 'host Python 3 is required for interactive setup'
        setup_script=$(readlink -f -- "${BASH_SOURCE[0]}")
        exec python3 -I "$(dirname -- "$setup_script")/setup/setup.py"
    fi
done

build_image=0
qualification_probe=0
shell_mode=0
git_worktree=0
args=()
for arg in "$@"; do
    case "$arg" in
        --container-qualify-probe)
            [[ $# == 1 ]] || die 'the fixed qualification probe must be used alone'
            qualification_probe=1 ;;
        --container-build) build_image=1 ;;
        --container-shell) shell_mode=1 ;;
        --container-git-worktree) git_worktree=1 ;;
        *) args+=("$arg") ;;
    esac
done

# An explicit or managed mode precedes every other check, engine query and
# state operation. Files in the current directory never supply it.
if [[ -z "${CODEX_CONTAINER_NETWORK:-}" ]]; then
    setup_wrapper=${BASH_SOURCE[0]}
    [[ "$setup_wrapper" == /* ]] || setup_wrapper="$PWD/$setup_wrapper"
    printf -v setup_command 'bash %q --container-setup' "$setup_wrapper"
    die "setup required: run $setup_command; use the managed launcher afterward or explicitly set CODEX_CONTAINER_NETWORK for an operator workflow (offline, provider, or unrestricted; unrestricted keeps the previous networking behavior)"
fi

boolean() {
    case "${2,,}" in
        1|true|yes) printf 1 ;;
        ''|0|false|no) printf 0 ;;
        *) die "$1 must be 0, 1, true, false, yes, or no" ;;
    esac
}
codex_args=("${args[@]}")
yolo="${CODEX_YOLO:-}"
case "${yolo,,}" in
    1|true|yes)
        ((shell_mode)) || codex_args=(--yolo "${args[@]}")
        ;;
    ''|0|false|no) ;;
    *) die "CODEX_YOLO must be 0, 1, true, false, yes, or no" ;;
esac
podman_access=0
[[ "${CODEX_CONTAINER_PODMAN:-}" != 1 ]] || podman_access=1
trust_host_ca=$(boolean CODEX_CONTAINER_TRUST_HOST_CA "${CODEX_CONTAINER_TRUST_HOST_CA:-}")
network_mode=$CODEX_CONTAINER_NETWORK
case "$network_mode" in
    offline|provider|unrestricted) ;;
    *) die 'CODEX_CONTAINER_NETWORK must be offline, provider, or unrestricted' ;;
esac
if [[ "$network_mode" != unrestricted ]] && ((podman_access)); then
    die 'restricted networking rejects CODEX_CONTAINER_PODMAN=1: the host API bypasses egress enforcement; select explicit unrestricted mode for delegation'
fi
if [[ "$network_mode" == provider ]]; then
    [[ -n "${CODEX_CONTAINER_NETWORK_PROFILE:-}" && -n "${CODEX_CONTAINER_NETWORK_POLICY:-}" ]] \
        || die 'provider mode requires CODEX_CONTAINER_NETWORK_PROFILE and CODEX_CONTAINER_NETWORK_POLICY'
    [[ -n "${CODEX_CONTAINER_NETWORK_RUNTIME_DIR:-}" && -n "${CODEX_CONTAINER_EGRESS_IMAGE:-}" ]] \
        || die 'provider mode requires a private host-path CODEX_CONTAINER_NETWORK_RUNTIME_DIR and immutable CODEX_CONTAINER_EGRESS_IMAGE'
fi
[[ -z "${CODEX_CONTAINER_STATE_DIR:-}" || -z "${CODEX_HOME:-}" ]] \
    || die 'CODEX_CONTAINER_STATE_DIR conflicts with CODEX_HOME; unset CODEX_HOME to isolate state, or unset CODEX_CONTAINER_STATE_DIR to keep shared state'

# Session budgets and lifetime, validated before any engine or state operation.
# network/agent_budgets.py implements the same rules for qualification.
# Only an unset budget selects its default; no value disables a budget.
memory_text=${CODEX_CONTAINER_MEMORY_LIMIT-4g}
cpu_text=${CODEX_CONTAINER_CPU_LIMIT-2}
pids_text=${CODEX_CONTAINER_PIDS_LIMIT-512}
timeout_text=${CODEX_CONTAINER_RUN_TIMEOUT:-0}
memory_bytes=0
if [[ "$memory_text" =~ ^([1-9][0-9]{0,15})([kmgKMG])$ ]]; then
    case "${BASH_REMATCH[2],,}" in
        k) unit=1024 ;;
        m) unit=1048576 ;;
        *) unit=1073741824 ;;
    esac
    ((10#${BASH_REMATCH[1]} > (1 << 50) / unit)) || memory_bytes=$((10#${BASH_REMATCH[1]} * unit))
fi
((memory_bytes > 0)) || die 'CODEX_CONTAINER_MEMORY_LIMIT must be a positive integer with unit k, m or g, for example 4g'
cpu_nano=0
if [[ "$cpu_text" =~ ^([0-9]{1,4})(\.([0-9]{1,3}))?$ ]]; then
    fraction=${BASH_REMATCH[3]}000
    cpu_nano=$((10#${BASH_REMATCH[1]} * 1000000000 + 10#${fraction:0:3} * 1000000))
    ((cpu_nano <= 1024000000000)) || cpu_nano=0
fi
((cpu_nano > 0)) || die 'CODEX_CONTAINER_CPU_LIMIT must be a positive number of CPUs with at most 3 decimals, for example 2 or 1.5'
[[ "$pids_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((pids_text > 0 && pids_text <= 4194304)) \
    || die 'CODEX_CONTAINER_PIDS_LIMIT must be a positive integer process count up to 4194304'
[[ "$timeout_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((timeout_text <= 2147483647)) \
    || die 'CODEX_CONTAINER_RUN_TIMEOUT must be whole seconds; 0 disables the lifetime limit'
pids_limit=$((10#$pids_text))
run_timeout=$((10#$timeout_text))

# Refuse sensitive writable workspaces before any engine or state operation.
WORKSPACE="$(pwd -P)"
workspace_mount="$WORKSPACE"
if ((git_worktree)); then
    workspace_mount="$(dirname -- "$WORKSPACE")"
fi
[[ "${HOME:-}" == /* ]] || die 'HOME must be an absolute path'
# A missing home cannot be a workspace, so its lexical path is sufficient then.
physical_home=$(cd -- "$HOME" 2>/dev/null && pwd -P) || physical_home=$HOME
unsafe_workspace=0
case "$workspace_mount" in
    /|/home|/root|/etc|/usr|/var|/bin|/sbin|/lib|/lib64|/boot|/opt|/srv|/mnt|/media|/proc|/sys|/dev|/run|/tmp)
        unsafe_workspace=1 ;;
esac
[[ "$workspace_mount" != "$physical_home" && ! "$workspace_mount" =~ ^/mnt/[A-Za-z]$ ]] || unsafe_workspace=1
if ((unsafe_workspace)); then
    [[ "${CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE:-}" == 1 ]] \
        || die "refusing sensitive workspace $workspace_mount; launch from a project subdirectory or set exact CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1"
    printf 'codex-container: WARNING: sensitive workspace explicitly exposed read/write: %s\n' "$workspace_mount" >&2
fi

command -v podman >/dev/null || die "podman is not installed on the host"
script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
script_dir=$(dirname -- "$script_path")
IMAGE="${CODEX_CONTAINER_IMAGE:-localhost/codex-cli:latest}"
container_prefix="${WORKSPACE##*/}"
container_prefix="$(printf '%s' "$container_prefix" | sed -E 's/[^[:alnum:]_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')"
[[ -n "$container_prefix" ]] || container_prefix="codex-container"

[[ -z "${CONTAINER_CONNECTION:-}" ]] || die "Named Podman connections are not supported; use local Podman or a same-host Unix CONTAINER_HOST"
case "${CONTAINER_HOST:-}" in
    '') ;;
    unix://*)
        launch_socket=${CONTAINER_HOST#unix://}
        [[ "$launch_socket" == /* && -n "${launch_socket//\//}" ]] || die "CONTAINER_HOST requires an absolute Unix socket path beyond /"
        ;;
    *) die "Unsupported Podman connection; use local Podman or an absolute same-host Unix CONTAINER_HOST" ;;
esac
# Retain record boundaries through command substitution, including extra final LF.
# Appending the sentinel only on success preserves failed query results.
engine_response=''
capture_engine_info() {
    engine_response=$(podman "$@" && printf '\001') || return 1
    engine_response=${engine_response%$'\001'}
    engine_response=${engine_response%$'\n'}
    [[ "$engine_response" != *$'\r'* ]]
}
capture_engine_info info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}' || die "cannot query Podman or invalid engine response; check local rootless Podman or the same-host Unix service"
runtime_info=$engine_response
read -r rootless runtime_os service_remote extra <<< "$runtime_info"
[[ "$rootless" == true && "$runtime_os" == linux && -z "$extra" && "$runtime_info" != *$'\n'* ]] || die "The launch engine must report Linux rootless operation; check Podman info and run as a non-root user"
case "$service_remote" in
    false) ;;
    true)
        [[ "${CONTAINER_HOST:-}" == unix:///?* ]] || die "A remote launch engine requires an explicit same-host Unix CONTAINER_HOST"
        ;;
    *) die "Cannot verify launch engine ServiceIsRemote; check that Podman reports true or false" ;;
esac
if [[ "$network_mode" != unrestricted ]]; then
    command -v python3 >/dev/null || die 'host Python 3 is required for restricted network policy validation'
    [[ "$service_remote" == true ]] || die 'restricted networking currently requires the tested same-host Unix service; local-engine enforcement is unverified'
    capture_engine_info info --format '{{.Host.NetworkBackend}}' || die 'cannot verify restricted network backend'
    network_backend=$engine_response
    capture_engine_info version --format '{{.Server.Version}}' || die 'cannot verify restricted network server version'
    network_version=$engine_response
    capture_engine_info info --format '{{json .Host}}' || die 'cannot verify restricted platform security policy'
    network_platform=$engine_response
elif ((qualification_probe)); then
    die 'qualification probes require restricted networking'
fi

if ((podman_access)); then
    socket="${CODEX_CONTAINER_PODMAN_SOCKET:-}"
    if [[ -z "$socket" && "${CONTAINER_HOST:-}" == unix:///?* ]]; then
        socket="${CONTAINER_HOST#unix://}"
    fi
    socket="${socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
    [[ "$socket" == /* ]] || die "Podman socket path must be absolute: $socket (set CODEX_CONTAINER_PODMAN_SOCKET to a same-host Unix socket)"
    selected_socket="$socket"
    socket=$(readlink -f -- "$selected_socket") || die "Cannot resolve Podman socket: $selected_socket (check the path and permissions)"
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $selected_socket (start 'podman system service --time=0' or enable podman.socket; check socket permissions)"
    capture_engine_info --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}}{{"\n"}}{{.Host.RemoteSocket.Path}}' || die "Cannot query Podman socket or invalid response: $socket (check the service and socket permissions)"
    socket_info=$engine_response
    socket_rootless="${socket_info%%$'\n'*}"
    case "$socket_rootless" in
        true) ;;
        false) die "Podman socket must serve a rootless engine: $socket (start the service as your non-root user)" ;;
        *) die "Cannot verify rootless operation at Podman socket: $socket (check that the service reports Host.Security.Rootless as true)" ;;
    esac
    [[ "$socket_info" == *$'\n'* ]] || die "Podman service did not report a host socket path: $socket (check Host.RemoteSocket.Path support)"
    host_socket="${socket_info#*$'\n'}"
    [[ "$host_socket" == /* && "$host_socket" != *$'\n'* ]] || die "Podman service must report an absolute host socket path: $socket (check Host.RemoteSocket.Path)"
fi

# Create missing state privately and validate the resolved directory; never
# repair existing permissions. Sets resolved_state.
caller_uid=$(id -u)
resolved_state=''
private_state() {
    local label=$1 variable=$2 path=$3 owner mode
    if [[ ! -e "$path" && ! -L "$path" ]]; then
        (umask 077; mkdir -p -- "$path") || die "Cannot create $label: $path (choose an accessible private $variable)"
    fi
    [[ -d "$path" ]] || die "$label is not a directory: $path (choose a private $variable)"
    resolved_state=$(CDPATH='' cd -- "$path" && pwd -P) || die "Cannot resolve $label: $path (check directory access or choose a private $variable)"
    path=$resolved_state
    [[ -r "$path" && -w "$path" && -x "$path" ]] || die "$label is not accessible: $path (check read/write/traverse permissions or choose a private $variable)"
    owner=$(stat -c '%u' -- "$path") || die "Cannot inspect $label owner: $path"
    mode=$(stat -c '%a' -- "$path") || die "Cannot inspect $label permissions: $path"
    [[ "$owner" == "$caller_uid" ]] || die "$label must belong to the calling user: $path (correct ownership or choose a private $variable)"
    [[ "$mode" =~ ^[0-7]{3,4}$ ]] || die "Cannot verify $label permissions: $path"
    (( (8#$mode & 077) == 0 )) || die "$label must be private: $path (chmod 700 your directory, or choose $variable on a Linux filesystem that enforces Unix permissions)"
}

state_dir="${CODEX_CONTAINER_STATE_DIR:-}"
CODEX_DIR=''
if [[ -n "$state_dir" ]]; then
    private_state 'Isolated Codex home' CODEX_CONTAINER_STATE_DIR "$state_dir"
    state_dir=$resolved_state
    # Resolve before creating children so an existing symlink cannot redirect
    # configuration or the CA mount parent outside the dedicated home.
    children=(.codex)
    ((trust_host_ca == 0)) || children+=(ca)
    for relative in "${children[@]}"; do
        resolved=$(readlink -m -- "$state_dir/$relative")
        [[ "$resolved" == "$state_dir/"* ]] || die "isolated configuration escapes state home: $state_dir/$relative"
        private_state 'Isolated Codex configuration' CODEX_CONTAINER_STATE_DIR "$state_dir/$relative"
    done
    state_mounts=(--volume "$state_dir:/codex-home:rw")
else
    private_state 'Codex state' CODEX_HOME "${CODEX_HOME:-${HOME}/.codex}"
    CODEX_DIR=$resolved_state
    state_mounts=(
        --tmpfs /codex-home:rw,exec,nosuid,nodev,mode=1777
        --volume "$CODEX_DIR:/codex-home/.codex:rw"
    )
fi

ca_bundle=''
if ((trust_host_ca)); then
    if [[ -n "${CODEX_CONTAINER_CA_BUNDLE:-}" ]]; then
        [[ -f "$CODEX_CONTAINER_CA_BUNDLE" ]] || die "CODEX_CONTAINER_CA_BUNDLE is not a file: $CODEX_CONTAINER_CA_BUNDLE"
        ca_bundle=$(readlink -f -- "$CODEX_CONTAINER_CA_BUNDLE")
    else
        for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
            if [[ -f "$candidate" ]]; then
                ca_bundle=$candidate
                break
            fi
        done
        [[ -n "$ca_bundle" ]] || die 'no default CA bundle found; set CODEX_CONTAINER_CA_BUNDLE to a bundle file'
    fi
fi

# Restricted sessions use the shared helper; this wrapper keeps only the
# agent-specific command, environment, state and credentials.
session_helper=(python3 -I "$script_dir/network/session.py")
network_inputs=()
qualification_inputs=()
guard_digest=''
if [[ "$network_mode" != unrestricted ]]; then
    network_inputs=(--installation "$script_dir" --writable "$workspace_mount"
        --mount-target "$workspace_mount" --mount-target /codex-home)
    if [[ -n "$state_dir" ]]; then
        network_inputs+=(--writable "$state_dir")
    else
        network_inputs+=(--writable "$CODEX_DIR")
    fi
    if [[ "$network_mode" == provider ]]; then
        network_inputs+=(--policy "$CODEX_CONTAINER_NETWORK_POLICY"
            --profile "$CODEX_CONTAINER_NETWORK_PROFILE" --proxy-image "$CODEX_CONTAINER_EGRESS_IMAGE"
            --runtime "$CODEX_CONTAINER_NETWORK_RUNTIME_DIR")
    fi
    prepare_inputs=(--mode "$network_mode" --server-version "$network_version"
        --backend "$network_backend" --endpoint "${CONTAINER_HOST:-}" --engine "$runtime_info")
    if ((qualification_probe)); then
        prepare_inputs+=(--probe --qualification-input "${CODEX_CONTAINER_QUALIFICATION_INPUT:-}"
            --workspace "$WORKSPACE")
    fi
    prepared=$(printf '%s\n' "$network_platform" | "${session_helper[@]}" prepare "${network_inputs[@]}" "${prepare_inputs[@]}")
    read -r guard_digest qualification_token qualification_tls <<< "$prepared"
    if ((qualification_probe)); then
        qualification_inputs=(--probe --token "$qualification_token" --workspace "$WORKSPACE"
            --qualification-input "${CODEX_CONTAINER_QUALIFICATION_INPUT:-}")
        [[ "$qualification_tls" != 1 ]] || qualification_inputs+=(--tls)
    fi
fi

# Every build, including the automatic build of a missing image, is maintenance.
maintenance=0
[[ "${CODEX_CONTAINER_MAINTENANCE:-}" != 1 ]] || maintenance=1
if ((build_image)); then
    ((maintenance)) || die 'image refresh requires exact CODEX_CONTAINER_MAINTENANCE=1; host pulls and build RUN steps are outside runtime filtering'
    podman build --tag "$IMAGE" --file "$script_dir/Containerfile" "$script_dir"
elif podman image exists "$IMAGE"; then
    :
else
    image_status=$?
    if ((image_status != 1)); then
        printf 'codex-container: Cannot inspect image %s (status %s); check Podman storage and connection\n' "$IMAGE" "$image_status" >&2
        exit "$image_status"
    fi
    ((maintenance)) || die "image $IMAGE is absent; prepare it with exact CODEX_CONTAINER_MAINTENANCE=1 (build traffic is outside runtime filtering)"
    podman build --tag "$IMAGE" --file "$script_dir/Containerfile" "$script_dir"
fi
if [[ "$network_mode" == provider ]]; then
    if podman image exists "$CODEX_CONTAINER_EGRESS_IMAGE"; then
        :
    else
        image_status=$?
        [[ "$image_status" == 1 ]] || die 'cannot inspect immutable egress proxy image'
        ((maintenance)) && [[ "$CODEX_CONTAINER_EGRESS_IMAGE" == *@sha256:* ]] \
            || die 'proxy image is absent; prepare the pinned artifact under explicit operator maintenance authorization (CODEX_CONTAINER_MAINTENANCE=1 and a registry digest)'
        podman pull "$CODEX_CONTAINER_EGRESS_IMAGE"
    fi
fi

# Restricted sessions and their qualification bind the immutable image ID.
if [[ "$network_mode" != unrestricted ]]; then
    capture_engine_info image inspect --format '{{.Id}}' "$IMAGE" || die 'cannot resolve restricted runtime image identity'
    [[ "$engine_response" =~ ^(sha256:)?[a-f0-9]{64}$ ]] || die 'invalid restricted runtime image identity'
    IMAGE=$engine_response
fi

podman_args=(
    --rm --interactive
    --read-only --read-only-tmpfs=false
    --tmpfs /tmp:rw,exec,nosuid,nodev,mode=1777,size=512m
    --tmpfs /var/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m
    --tmpfs /run:rw,nosuid,nodev,mode=1777,size=32m
    --userns=keep-id
    --user "$caller_uid:$(id -g)"
    --cap-drop=all --security-opt=no-new-privileges
    "--memory=$memory_bytes" "--cpus=$cpu_text" "--pids-limit=$pids_limit"
    --workdir "$WORKSPACE"
    --env HOME=/codex-home
    --env CODEX_HOME=/codex-home/.codex
    --volume "$workspace_mount:$workspace_mount:rw"
    "${state_mounts[@]}"
)
((run_timeout == 0)) || podman_args+=(--timeout "$run_timeout")
if [[ -t 0 && -t 1 ]]; then
    podman_args+=(--tty)
fi

if ((podman_access)); then
    podman_args+=(
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
        --volume "$host_socket:/run/podman/podman.sock:rw"
    )
else
    podman_args+=(--unsetenv CONTAINER_HOST)
fi
if ((trust_host_ca)); then
    podman_args+=(
        --volume "$ca_bundle:/codex-home/ca/bundle.pem:ro"
        --env SSL_CERT_FILE=/codex-home/ca/bundle.pem
        --env REQUESTS_CA_BUNDLE=/codex-home/ca/bundle.pem
        --env CURL_CA_BUNDLE=/codex-home/ca/bundle.pem
        --env NODE_EXTRA_CA_CERTS=/codex-home/ca/bundle.pem
    )
fi

if ((qualification_probe)); then
    codex_args=()  # The shared helper supplies the fixed probe command.
elif ((shell_mode)); then
    podman_args+=(--entrypoint /bin/bash)
    codex_args=()
fi

command -v timeout >/dev/null || die "coreutils timeout is required for bounded session cleanup"
container_id=''
client_pid=''
session_tmp=''
session_token=''
pending_signal=''
pending_status=0
attached=0
creating=0
qualification_check_pid=''
session_start_pid=''
diagnostics_pid=''
diagnostics_fd=''
ownership_label=io.codex-container.session

record_signal() {
    if ((pending_status == 0)); then
        pending_signal=$1
        pending_status=$2
    fi
    if { ((attached || creating)) && [[ -n "$client_pid" ]]; } \
        || [[ -n "$qualification_check_pid" || -n "$session_start_pid" ]]; then
        exit "$pending_status"
    fi
}

# An interrupted create enters EXIT reconciliation with its PID still tracked.
wait_for_create() {
    ((pending_status == 0)) || exit "$pending_status"
    local status=0
    wait "$client_pid" || status=$?
    ((pending_status == 0)) || exit "$pending_status"
    return "$status"
}

# Consult Bash's child table rather than potentially recycled process IDs.
child_running() {
    local child=$1 running
    [[ -n "$child" ]] || return 1
    while IFS= read -r running; do
        [[ "$running" != "$child" ]] || return 0
    done < <(jobs -p)
    return 1
}

client_running() {
    child_running "$client_pid"
}

wait_for_client_until() {
    local deadline=$1
    while client_running; do
        ((SECONDS < deadline)) || return 1
        sleep 0.05
    done
}

reap_client() {
    [[ -n "$client_pid" ]] || return 0
    if client_running; then
        kill -TERM "$client_pid" 2>/dev/null || true
        if ! wait_for_client_until "$((SECONDS + 5))"; then
            kill -KILL "$client_pid" 2>/dev/null || true
        fi
    fi
    if wait_for_client_until "$((SECONDS + 1))"; then
        wait "$client_pid" 2>/dev/null || true
    else
        printf 'codex-container: Cannot reap Podman client %s within deadline; inspect it explicitly\n' "$client_pid" >&2
    fi
    client_pid=''
}

# Restricted helpers: TERM, a bounded grace period, then KILL and reap.
reap_helper() {
    local child=$1 grace=$2 until
    child_running "$child" || { wait "$child" 2>/dev/null || true; return 0; }
    kill -TERM "$child" 2>/dev/null || true
    until=$((SECONDS + grace))
    while child_running "$child" && ((SECONDS < until)); do
        sleep 0.05
    done
    if child_running "$child"; then
        printf 'codex-container: restricted helper %s did not confirm cleanup before the deadline\n' "$child" >&2
        kill -KILL "$child" 2>/dev/null || true
    fi
    until=$((SECONDS + 1))
    while child_running "$child" && ((SECONDS < until)); do
        sleep 0.05
    done
    if child_running "$child"; then
        printf 'codex-container: Cannot reap restricted helper %s within deadline; inspect it explicitly\n' "$child" >&2
    else
        wait "$child" 2>/dev/null || true
    fi
}

recover_container_id() {
    local recovered='' has_nul=0
    [[ -z "$container_id" && -n "$session_tmp" && -s "$session_tmp/cid" ]] || return 0
    # read preserves all LFs; a NUL delimiter is itself invalid CID data.
    IFS= read -r -d '' recovered < "$session_tmp/cid" && has_nul=1
    recovered=${recovered%$'\n'}
    if ((has_nul)) || [[ ! "$recovered" =~ ^[a-f0-9]{64}$ ]]; then
        printf 'codex-container: Invalid container ID in private creation record; inspect creation explicitly\n' >&2
        return 1
    fi
    container_id=$recovered
}

cleanup() {
    local status=$? control_status shutdown_deadline
    trap '' TERM INT HUP
    ((pending_status == 0)) || status=$pending_status
    shutdown_deadline=$((SECONDS + 20))
    if [[ -n "$qualification_check_pid" ]]; then
        reap_helper "$qualification_check_pid" 13
        qualification_check_pid=''
    fi
    if [[ -n "$session_start_pid" ]]; then
        # The session helper owns a separate process group. Reap the whole
        # group before its leader, including an engine client that ignores TERM.
        kill -TERM -- "-$session_start_pid" 2>/dev/null || true
        sleep 0.1
        kill -KILL -- "-$session_start_pid" 2>/dev/null || true
        reap_helper "$session_start_pid" 1
        session_start_pid=''
    fi
    if ((creating)); then
        if [[ -n "$client_pid" ]]; then
            wait_for_client_until "$((SECONDS + 5))" || true
            reap_client
        fi
        # The client can publish its CID while responding to cancellation.
        recover_container_id || true
        if ((pending_status)) && [[ -z "$container_id" ]]; then
            printf 'codex-container: Creation outcome unresolved for %s (no verified owned ID); inspect the engine explicitly\n' "$name" >&2
        fi
    fi
    if [[ -n "$container_id" ]]; then
        if ((pending_status && attached)); then
            if timeout --kill-after=1s 5s podman kill --signal "$pending_signal" "$container_id" >/dev/null; then
                wait_for_client_until "$((SECONDS + 5))" || true
            else
                printf 'codex-container: Cannot forward %s to owned container %s\n' "$pending_signal" "$container_id" >&2
            fi
        fi
        control_status=0
        timeout --kill-after=1s 5s podman rm --force --ignore --time 0 "$container_id" >/dev/null || control_status=$?
        if ((control_status)); then
            printf 'codex-container: Cannot remove owned container %s (status %s); check the engine and remove it explicitly\n' "$container_id" "$control_status" >&2
        fi
    fi
    reap_client
    if [[ -n "$diagnostics_fd" ]]; then
        exec {diagnostics_fd}>&-
        diagnostics_fd=''
    fi
    if [[ -n "$diagnostics_pid" ]]; then
        # Drain the final client output before reaping the stderr filter.
        drain_until=$((SECONDS + 1))
        while child_running "$diagnostics_pid" && ((SECONDS < drain_until)); do
            sleep 0.01
        done
        reap_helper "$diagnostics_pid" 1
        diagnostics_pid=''
    fi
    if [[ "$network_mode" == provider && -n "$session_tmp" ]]; then
        # Owned proxy recovery/removal and diagnostics share the remaining budget.
        "${session_helper[@]}" stop --session "$session_tmp" --deadline "$((shutdown_deadline - SECONDS))" \
            --container "${container_id:-unknown}" || true
    fi
    [[ -z "$session_tmp" ]] || rm -rf -- "$session_tmp"
    return "$status"
}

trap cleanup EXIT
trap 'record_signal TERM 143' TERM
trap 'record_signal INT 130' INT
trap 'record_signal HUP 129' HUP
if [[ "$network_mode" == provider ]]; then
    session_tmp=$(umask 077; mktemp -d -- "$CODEX_CONTAINER_NETWORK_RUNTIME_DIR/session.XXXXXXXXXXXX") \
        || die "Cannot create private session directory in CODEX_CONTAINER_NETWORK_RUNTIME_DIR"
else
    session_tmp=$(umask 077; mktemp -d) || die "Cannot create private session bookkeeping directory"
fi
session_token=${session_tmp##*/}
((pending_status == 0)) || exit "$pending_status"
printf 'codex-container: network mode=%s\n' "$network_mode" >&2
if [[ "$network_mode" != unrestricted ]] && ((qualification_probe == 0)); then
    CODEX_CONTAINER_IMAGE="$IMAGE" python3 -I "$script_dir/network/qualify.py" check &
    qualification_check_pid=$!
    if wait "$qualification_check_pid"; then
        qualification_check_pid=''
    else
        qualification_status=$?
        qualification_check_pid=''
        ((pending_status == 0)) || exit "$pending_status"
        exit "$qualification_status"
    fi
fi
((pending_status == 0)) || exit "$pending_status"
if [[ "$network_mode" == provider ]]; then
    "${session_helper[@]}" start "${network_inputs[@]}" "${qualification_inputs[@]}" --session "$session_tmp" \
        --guard-digest "$guard_digest" >"$session_tmp/policy.identity" &
    session_start_pid=$!
    wait "$session_start_pid"
    session_start_pid=''
fi
((pending_status == 0)) || exit "$pending_status"
if [[ "$network_mode" != unrestricted ]]; then
    application=()
    if ((shell_mode)); then
        application=(/bin/bash)
    elif ((qualification_probe == 0)); then
        # Codex's own sandbox cannot start under the guard (Bubblewrap needs
        # Netlink); the guard is the enforced boundary. A later operator
        # --sandbox or -c sandbox_mode remains an explicit choice.
        # The shared background server needs a Unix listener the guard denies;
        # --no-daemon runs Codex embedded without its startup warning.
        application=(/usr/local/bin/codex --no-daemon -c 'sandbox_mode="danger-full-access"')
        if [[ "$network_mode" == provider ]]; then
            # Protected overrides precede the operator's arguments; -c takes
            # precedence over the agent-writable config.toml.
            application+=(-c check_for_update_on_startup=false -c analytics.enabled=false
                -c feedback.enabled=false -c 'otel.exporter="none"' -c 'otel.trace_exporter="none"'
                -c 'otel.metrics_exporter="none"' -c features.apps=false -c features.plugins=false
                -c features.remote_plugin=false -c features.plugin_discovery_prefetch=false)
        fi
        application+=("${codex_args[@]}")
    fi
    "${session_helper[@]}" agent-args --installation "$script_dir" --mode "$network_mode" \
        --session "$session_tmp" --guard-digest "$guard_digest" "${qualification_inputs[@]}" \
        -- "${application[@]}" >"$session_tmp/agent.args"
    mapfile -d '' -t restricted <"$session_tmp/agent.args"
    [[ "${restricted[0]:-}" =~ ^[0-9]+$ ]] || die 'invalid restricted session arguments'
    podman_args+=("${restricted[@]:1:${restricted[0]}}")
    codex_args=("${restricted[@]:$((1 + restricted[0]))}")
    # The API key reaches only the API profiles; account sessions sign in natively.
    if [[ "$network_mode" == provider && ( "$CODEX_CONTAINER_NETWORK_PROFILE" == openai-api \
        || "$CODEX_CONTAINER_NETWORK_PROFILE" == openai-api-docs ) && -n "${OPENAI_API_KEY:-}" ]]; then
        podman_args+=(--env OPENAI_API_KEY)
    fi
fi
names=$(podman ps --all --format '{{.Names}}') || die "Cannot list Podman containers; check the launch engine"
((pending_status == 0)) || exit "$pending_status"
next_index=0
while IFS= read -r name; do
    [[ "$name" == "$container_prefix"-* ]] || continue
    suffix=${name#"$container_prefix"-}
    [[ "$suffix" =~ ^[0-9]{1,9}$ ]] || continue
    numeric=$((10#$suffix))
    ((numeric < next_index)) || next_index=$((numeric + 1))
done <<< "$names"

for ((attempt=0; attempt<20; attempt++)); do
    ((pending_status == 0)) || exit "$pending_status"
    name="$container_prefix-$next_index"
    rm -f -- "$session_tmp/cid"
    creating=1
    podman create --name "$name" --cidfile "$session_tmp/cid" --label "$ownership_label=$session_token" \
        "${podman_args[@]}" "$IMAGE" "${codex_args[@]}" \
        </dev/null >"$session_tmp/output" 2>"$session_tmp/error" &
    client_pid=$!
    create_status=0
    wait_for_create || create_status=$?
    client_pid=''
    recover_container_id || die "Invalid container ID returned by creation"
    creating=0
    ((pending_status == 0)) || exit "$pending_status"
    if ((create_status == 0)); then
        [[ -n "$container_id" ]] || die "Creation succeeded without a container ID"
        break
    fi
    cat -- "$session_tmp/error" >&2
    [[ -z "$container_id" ]] || exit "$create_status"
    exists_status=0
    podman container exists "$name" || exists_status=$?
    ((pending_status == 0)) || exit "$pending_status"
    case "$exists_status" in
        0) next_index=$((next_index + 1)) ;;
        1) exit "$create_status" ;;
        *) die "Cannot verify container name collision for $name (status $exists_status)" ;;
    esac
done
[[ -n "$container_id" ]] || die "Cannot reserve a container name after 20 attempts"
((pending_status == 0)) || exit "$pending_status"

# Engine flags alone are not evidence: require the created configuration to
# carry every selected budget before the application starts.
configured_budgets=$(timeout --kill-after=1s 10s podman inspect --type container \
    --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' "$container_id") \
    || die 'Cannot inspect session resource budgets; session not started'
((pending_status == 0)) || exit "$pending_status"
[[ "$configured_budgets" == "$memory_bytes $cpu_nano $pids_limit" ]] \
    || die "Session resource budgets were not applied (expected memory=$memory_bytes nano_cpus=$cpu_nano pids=$pids_limit); check rootless cgroup v2 cpu/memory/pids controller delegation; session not started"

# Explicit redirection retains redirected stdin for the background client.
attached=1
started_at=$SECONDS
if [[ -f "$script_dir/setup/diagnostics.py" ]] && command -v python3 >/dev/null; then
    # Optional for unrestricted installs without host Python. Only the exact
    # successful Podman 4.3 restart-check line changes level; errors pass.
    mkfifo -- "$session_tmp/diagnostics.pipe"
    python3 -I "$script_dir/setup/diagnostics.py" <"$session_tmp/diagnostics.pipe" >&2 &
    diagnostics_pid=$!
    exec {diagnostics_fd}>"$session_tmp/diagnostics.pipe"
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 2>&"$diagnostics_fd" {diagnostics_fd}>&- &
    client_pid=$!
    exec {diagnostics_fd}>&-
    diagnostics_fd=''
else
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 &
    client_pid=$!
fi
if ((pending_status)); then
    exit "$pending_status"
fi
status=0
wait "$client_pid" || status=$?
((pending_status == 0)) || exit "$pending_status"
client_pid=''
if ((run_timeout > 0 && status != 0 && SECONDS - started_at >= run_timeout)); then
    printf 'codex-container: session lifetime limit reached (%s s); exit status %s\n' "$run_timeout" "$status" >&2
fi
exit "$status"
