#!/usr/bin/env bash
# Same-host service runner with disposable state on native Linux volume storage.
set -Eeuo pipefail
project_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${CODEX_CONTAINER_IMAGE:-localhost/codex-cli:latest}
socket=${CODEX_CONTAINER_PODMAN_SOCKET:-}
if [[ -z "$socket" && "${CONTAINER_HOST:-}" == unix:///?* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
socket=${socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}
host_socket=$(podman --remote --url "unix://$socket" info --format '{{.Host.RemoteSocket.Path}}')
[[ "$host_socket" == /* ]] || { printf 'Runtime tests require an absolute host socket path\n' >&2; exit 1; }
volume=$(podman volume create)
cleanup() { podman volume rm --force "$volume" >/dev/null; }
trap cleanup EXIT
native_root=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$project_root:$project_root:ro" \
    --volume "$native_root:$native_root:rw" \
    --volume "$host_socket:/run/podman/podman.sock:rw" \
    --workdir "$project_root" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    --env CODEX_RUNTIME_TESTS=1 \
    --env "CODEX_CONTAINER_IMAGE=$image" \
    --env "CODEX_TEST_ROOT=$native_root" \
    --entrypoint python3 "$image" \
    -B -m unittest discover -s tests -p test_runtime.py -v "$@"
