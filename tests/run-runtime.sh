#!/usr/bin/env bash
# Same-host service runner with disposable state on native Linux volume storage.
set -Eeuo pipefail
project_root=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${CODEX_CONTAINER_IMAGE:-localhost/codex-cli:latest}
socket=${CODEX_CONTAINER_PODMAN_SOCKET:-}
if [[ -z "$socket" && "${CONTAINER_HOST:-}" == unix:///?* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
socket=${socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}
host_socket=$(podman --remote --url "unix://$socket" info --format '{{.Host.RemoteSocket.Path}}')
[[ "$host_socket" == /* ]] || { printf 'Runtime tests require an absolute host socket path\n' >&2; exit 1; }
pattern=test_runtime.py
guard_environment=()
# The guarded Windows-workspace check writes below the checkout's .test-state.
project_mode=ro
# Shared suites copied from the reference, run without real-engine opt-ins.
shared=(test_reference_copy test_alignment test_agent_profile test_network_policy test_mux test_tls_client_hello
    test_tls_proxy test_platform test_qualification test_guard test_session test_network_feasibility)
case "${1:-}" in
    --wrapper) pattern=test_wrapper.py ;;
    --shared) pattern='' ;;
    --setup) pattern=test_setup.py; project_mode=rw ;;
    --setup-runtime) pattern=test_setup_runtime.py; project_mode=rw ;;
    --qualification) pattern=test_qualification.py ;;
    --network-feasibility) pattern=test_network_feasibility.py ;;
    --network) pattern=test_network_runtime.py; project_mode=rw ;;
    --network-policy) pattern=test_network_policy.py ;;
    --mux) pattern=test_mux.py ;;
    --guard|--guard-idle)
        pattern=test_guard.py
        guard_toolchain=$(podman image inspect --format '{{.Id}}' \
            "${SANDBOX_GUARD_TOOLCHAIN:-localhost/codex-guard-toolchain:development}")
        guard_environment=(--env SANDBOX_GUARD_TESTS=1 --env "SANDBOX_GUARD_TOOLCHAIN=$guard_toolchain")
        if [[ "$1" == --guard-idle ]]; then
            guard_environment+=(--env SANDBOX_IDLE_TESTS=1)
            set -- "$1" -k test_guarded_multiplex_idle_resume "${@:2}"
        fi
        ;;
    *) set -- '' "$@" ;;
esac
shift
# Wrapper fixtures need private, executable temporary storage: the image's
# /tmp is world-writable, and the toolchain library refuses such ancestors.
volume=$(podman volume create)
cleanup() { podman volume rm --force "$volume" >/dev/null; }
trap cleanup EXIT
native_root=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
if [[ -n "$pattern" ]]; then
    selection=(discover -s tests -p "$pattern" -v)
    runtime_environment=(--env CODEX_RUNTIME_TESTS=1 --env SANDBOX_RUNTIME_TESTS=1)
    # Opt-in checks that contact a real external service (no credentials).
    [[ "${SANDBOX_EXTERNAL_TESTS:-}" != 1 ]] || runtime_environment+=(--env SANDBOX_EXTERNAL_TESTS=1)
else
    selection=(-v "${shared[@]/#/tests.}")
    runtime_environment=()
fi
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$project_root:$project_root:$project_mode" \
    --volume "$native_root:$native_root:rw" \
    --volume "$host_socket:/run/podman/podman.sock:rw" \
    --tmpfs /tmp:rw,exec,nosuid,nodev,mode=1777 \
    --mount type=tmpfs,destination=/sandbox-test-tmp,tmpfs-mode=0700,U=true,tmpfs-size=1g \
    --env SANDBOX_TEST_TMPDIR=/sandbox-test-tmp \
    --workdir "$project_root" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    "${runtime_environment[@]}" \
    --env "CODEX_CONTAINER_IMAGE=$image" \
    --env "CODEX_TEST_ROOT=$native_root" --env "SANDBOX_TEST_STATE_ROOT=$native_root" \
    "${guard_environment[@]}" \
    --entrypoint python3 "$image" \
    -B -m unittest "${selection[@]}" "$@"
