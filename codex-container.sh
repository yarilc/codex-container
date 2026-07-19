#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${CODEX_CONTAINER_IMAGE:-localhost/codex-cli:latest}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
WORKSPACE="$(pwd -P)"

usage() {
    cat <<'EOF'
Usage: codex-container.sh [--build] [--shell] [codex arguments...]

Runs Codex in a Podman container. The current directory and ~/.codex are
mounted read/write. Podman inside the container uses the host rootless socket.

Environment:
  CODEX_CONTAINER_IMAGE  image name (default: localhost/codex-cli:latest)
  CODEX_HOME             Codex home on the host (default: ~/.codex)
  CODEX_YOLO             enable Codex --yolo (default: disabled)
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
args=()
while (($#)); do
    case "$1" in
        --build) build_image=1; shift ;;
        --shell) shell_mode=1; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; args+=("$@"); break ;;
        *) args+=("$1"); shift ;;
    esac
done

command -v podman >/dev/null || die "podman is not installed on the host"
[[ -d "$CODEX_DIR" ]] || mkdir -p "$CODEX_DIR"

codex_args=("${args[@]}")
case "${CODEX_YOLO:-}" in
    1|true|TRUE|yes|YES)
        ((shell_mode)) || codex_args=(--yolo "${args[@]}")
        ;;
    ''|0|false|FALSE|no|NO) ;;
    *) die "CODEX_YOLO must be 0, 1, true, false, yes, or no" ;;
esac

runtime_dir="/run/user/$(id -u)"
socket="${runtime_dir}/podman/podman.sock"
[[ -S "$socket" ]] || die "Podman socket not found: $socket (start 'podman system service --time=0' or enable podman.socket)"

if ((build_image)) || ! podman image exists "$IMAGE"; then
    podman build --tag "$IMAGE" --file "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"
fi

podman_args=(
    --rm --interactive --tty
    --name "$(container_name)"
    --userns=keep-id
    --user "$(id -u):$(id -g)"
    --workdir "$WORKSPACE"
    --env HOME=/codex-home
    --env CODEX_HOME=/codex-home/.codex
    --env CONTAINER_HOST=unix:///run/podman/podman.sock
    --volume "$WORKSPACE:$WORKSPACE:rw"
    --volume "$CODEX_DIR:/codex-home/.codex:rw"
    --volume "$socket:/run/podman/podman.sock"
)

if ((shell_mode)); then
    podman_args+=(--entrypoint /bin/bash)
    podman run "${podman_args[@]}" "$IMAGE"
else
    podman run "${podman_args[@]}" "$IMAGE" "${codex_args[@]}"
fi
