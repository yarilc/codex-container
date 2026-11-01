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
Podman is installed; host socket access requires CODEX_CONTAINER_PODMAN=1.

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
[[ -d "$CODEX_DIR" ]] || mkdir -p "$CODEX_DIR"

codex_args=("${args[@]}")
case "${CODEX_YOLO:-}" in
    1|true|TRUE|yes|YES)
        ((shell_mode)) || codex_args=(--yolo "${args[@]}")
        ;;
    ''|0|false|FALSE|no|NO) ;;
    *) die "CODEX_YOLO must be 0, 1, true, false, yes, or no" ;;
esac

if [[ "${CODEX_CONTAINER_PODMAN:-}" == 1 ]]; then
    runtime_dir="/run/user/$(id -u)"
    socket="${runtime_dir}/podman/podman.sock"
    [[ -S "$socket" ]] || die "Podman socket not found: $socket (start 'podman system service --time=0' or enable podman.socket)"
fi

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
        --volume "$socket:/run/podman/podman.sock"
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
