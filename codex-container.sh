#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${CODEX_CONTAINER_IMAGE:-localhost/codex-cli:latest}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
WORKSPACE="$(pwd -P)"

usage() {
    cat <<'EOF'
Usage: codex-container.sh [container option] [codex arguments...]

Runs Codex with a read-only image filesystem. The current directory (or its
parent with --container-git-worktree) and CODEX_HOME are mounted read/write.
/tmp, /var/tmp, /run, and HOME outside CODEX_HOME are writable and ephemeral.
CODEX_HOME must be caller-owned, accessible, and private (no group/other
permissions). Missing state is created with mode 0700; existing state is not
repaired automatically. Use private Linux storage if Unix modes are ignored.
Podman is installed; host socket access requires CODEX_CONTAINER_PODMAN=1.
Builds and sessions always require a verified Linux rootless launch engine.
Use local Podman or an explicit same-host Unix CONTAINER_HOST; named and
TCP/SSH connections are not supported. A Unix launch connection requires
its service even when session socket access is disabled.
Enabled access verifies that the socket serves a reachable rootless engine;
rootful or unverifiable services stop startup before image operations.

Container options:
  --container-build      build or refresh the container image before starting
  --container-shell      open a shell instead of starting Codex
  --container-git-worktree mount the parent of the current physical directory
                         read/write; the container starts in the current directory
  --container-help       show this wrapper help

All other arguments are passed to Codex unchanged.

Environment:
  CODEX_CONTAINER_IMAGE  image name (default: localhost/codex-cli:latest)
  CODEX_CONTAINER_PODMAN expose the host Podman socket only when exactly 1
                         (default: disabled; other values also disable access)
  CODEX_CONTAINER_PODMAN_SOCKET absolute socket override for enabled access
                         (then Unix CONTAINER_HOST, then XDG_RUNTIME_DIR or
                         /run/user/<uid>, with /podman/podman.sock appended)
  CODEX_HOME             Codex home on the host (default: ~/.codex)
  CODEX_YOLO             enable Codex --yolo (default: disabled)

Socket access permits new host mounts beyond the workspace with the service
user's authority. YOLO and socket access are independent. The service reports
the host-side socket source; containerized callers must preserve host absolute
workspace and state paths. No privileges or security-policy overrides are added.
EOF
}

die() { printf 'codex-container: %s\n' "$*" >&2; exit 1; }

container_prefix="${WORKSPACE##*/}"
container_prefix="$(printf '%s' "$container_prefix" | sed -E 's/[^[:alnum:]_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')"
[[ -n "$container_prefix" ]] || container_prefix="codex-container"

container_name() {
    local highest=-1 name suffix
    while IFS= read -r name; do
        [[ "$name" == "$container_prefix"-* ]] || continue
        suffix="${name#"$container_prefix"-}"
        [[ "$suffix" =~ ^[0-9]+$ ]] || continue
        if (( suffix > highest )); then
            highest="$suffix"
        fi
    done < <(podman ps --format '{{.Names}}')
    printf '%s-%d\n' "$container_prefix" "$((highest + 1))"
}

build_image=0
shell_mode=0
git_worktree=0
args=()
while (($#)); do
    case "$1" in
        --container-build) build_image=1; shift ;;
        --container-shell) shell_mode=1; shift ;;
        --container-git-worktree) git_worktree=1; shift ;;
        --container-help) usage; exit 0 ;;
        *) args+=("$1"); shift ;;
    esac
done

workspace_mount="$WORKSPACE"
if ((git_worktree)); then
    workspace_mount="$(dirname -- "$WORKSPACE")"
fi

command -v podman >/dev/null || die "podman is not installed on the host"

codex_args=("${args[@]}")
case "${CODEX_YOLO:-}" in
    1|true|TRUE|yes|YES)
        ((shell_mode)) || codex_args=(--yolo "${args[@]}")
        ;;
    ''|0|false|FALSE|no|NO) ;;
    *) die "CODEX_YOLO must be 0, 1, true, false, yes, or no" ;;
esac

[[ -z "${CONTAINER_CONNECTION:-}" ]] || die "Named Podman connections are not supported; use local Podman or a same-host Unix CONTAINER_HOST"
case "${CONTAINER_HOST:-}" in
    ''|unix:///?*) ;;
    *) die "Unsupported Podman connection; use local Podman or an absolute same-host Unix CONTAINER_HOST" ;;
esac
runtime_info=$(podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}') || die "Cannot query the launch engine; check local rootless Podman or the same-host Unix service"
read -r rootless runtime_os service_remote extra <<< "$runtime_info"
[[ "$rootless" == true && "$runtime_os" == linux && -z "$extra" && "$runtime_info" != *$'\n'* ]] || die "The launch engine must report Linux rootless operation; check Podman info and run as a non-root user"
case "$service_remote" in
    false) ;;
    true)
        [[ "${CONTAINER_HOST:-}" == unix:///?* ]] || die "A remote launch engine requires an explicit same-host Unix CONTAINER_HOST"
        ;;
    *) die "Cannot verify launch engine ServiceIsRemote; check that Podman reports true or false" ;;
esac

if [[ "${CODEX_CONTAINER_PODMAN:-}" == 1 ]]; then
    socket="${CODEX_CONTAINER_PODMAN_SOCKET:-}"
    if [[ -z "$socket" && "${CONTAINER_HOST:-}" == unix:///?* ]]; then
        socket="${CONTAINER_HOST#unix://}"
    fi
    socket="${socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
    [[ "$socket" == /* ]] || die "Podman socket path must be absolute: $socket (set CODEX_CONTAINER_PODMAN_SOCKET to a same-host Unix socket)"
    selected_socket="$socket"
    socket=$(readlink -f -- "$selected_socket") || die "Cannot resolve Podman socket: $selected_socket (check the path and permissions)"
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $selected_socket (start 'podman system service --time=0' or enable podman.socket; check socket permissions)"
    socket_info=$(podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}}{{"\n"}}{{.Host.RemoteSocket.Path}}') || die "Cannot query Podman socket: $socket (check the service and socket permissions)"
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

if [[ ! -e "$CODEX_DIR" && ! -L "$CODEX_DIR" ]]; then
    (umask 077; mkdir -p -- "$CODEX_DIR") || die "Cannot create Codex state: $CODEX_DIR (choose an accessible private CODEX_HOME)"
fi
[[ -d "$CODEX_DIR" ]] || die "Codex state is not a directory: $CODEX_DIR (choose a private CODEX_HOME)"
state_path="$CODEX_DIR"
CODEX_DIR=$(CDPATH= cd -- "$state_path" && pwd -P) || die "Cannot resolve Codex state: $state_path (check directory access or choose a private CODEX_HOME)"
[[ -r "$CODEX_DIR" && -w "$CODEX_DIR" && -x "$CODEX_DIR" ]] || die "Codex state is not accessible: $CODEX_DIR (check read/write/traverse permissions or choose a private CODEX_HOME)"
state_owner=$(stat -c '%u' -- "$CODEX_DIR") || die "Cannot inspect Codex state owner: $CODEX_DIR"
state_mode=$(stat -c '%a' -- "$CODEX_DIR") || die "Cannot inspect Codex state permissions: $CODEX_DIR"
[[ "$state_owner" == "$(id -u)" ]] || die "Codex state must belong to the calling user: $CODEX_DIR (correct ownership or choose a private CODEX_HOME)"
[[ "$state_mode" =~ ^[0-7]{3,4}$ ]] || die "Cannot verify Codex state permissions: $CODEX_DIR"
(( (8#$state_mode & 077) == 0 )) || die "Codex state must be private: $CODEX_DIR (chmod 700 your directory, or choose CODEX_HOME on a Linux filesystem that enforces Unix permissions)"

if ((build_image)) || ! podman image exists "$IMAGE"; then
    podman build --tag "$IMAGE" --file "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"
fi

podman_args=(
    --rm --interactive --tty
    --read-only --read-only-tmpfs=false
    --tmpfs /tmp:rw,exec,nosuid,nodev,mode=1777
    --tmpfs /var/tmp:rw,exec,nosuid,nodev,mode=1777
    --tmpfs /run:rw,nosuid,nodev,mode=1777
    --tmpfs /codex-home:rw,exec,nosuid,nodev,mode=1777
    --name "$(container_name)"
    --userns=keep-id
    --user "$(id -u):$(id -g)"
    --workdir "$WORKSPACE"
    --env HOME=/codex-home
    --env CODEX_HOME=/codex-home/.codex
    --volume "$workspace_mount:$workspace_mount:rw"
    --volume "$CODEX_DIR:/codex-home/.codex:rw"
)

if [[ "${CODEX_CONTAINER_PODMAN:-}" == 1 ]]; then
    podman_args+=(
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
        --volume "$host_socket:/run/podman/podman.sock:rw"
    )
else
    podman_args+=(--unsetenv CONTAINER_HOST)
fi

if ((shell_mode)); then
    podman_args+=(--entrypoint /bin/bash)
    podman run "${podman_args[@]}" "$IMAGE"
else
    podman run "${podman_args[@]}" "$IMAGE" "${codex_args[@]}"
fi
