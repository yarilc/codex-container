# Tasks

## 1. Enabled-service preflight and guidance

- [x] 1.1 Add the explicit remote rootless query after the existing socket check in `codex-container.sh`; accept only `true` and handle query failure, rootful results, and invalid output with actionable errors. Verify with disposable Podman stubs and a Unix socket fixture that the exact mounted URL is queried and failures precede image inspection, build, and run, including `--container-build`.
- [x] 1.2 Verify the behavior matrix with disposable fixtures: successful rootless access in Codex and shell modes; missing socket; failed query even if stdout says `true`; `false`, empty, whitespace, and unexpected output; unset, empty, `0`, `true`, and other non-enabling opt-in values. Confirm disabled modes make no service query, and help exits without requiring Podman.
- [x] 1.3 Update wrapper help, README socket verification and troubleshooting, and relevant `AGENTS.md` runtime guidance to describe automatic rootless verification and early failure. Verify documentation matches exact opt-in semantics and the unchanged socket path, and the manual formatted query requires `true`.

## 2. Integration verification

- [x] 2.1 Run `bash -n codex-container.sh`, `git diff --check`, `openspec validate verify-rootless-podman-service --strict`, and `openspec validate --specs --strict`; record passing results and resolve any failures introduced by this change.
- [x] 2.2 With usable host rootless Podman, verify enabled shell startup and an in-container formatted rootless query against the mounted service using disposable configuration; also check disabled startup without an API socket and preserve argument forwarding, workspace/parent mounts, spaces, and symlink behavior. Record actual integration results separately from stub results and identify any unavailable checks.

## Workflow follow-up

- After implementation verification, synchronize the delta into the main specification and archive the completed change through the project's OpenSpec workflow.

## Verification results

- `bash -n codex-container.sh` and `git diff --check`: passed.
- `openspec validate verify-rootless-podman-service --strict`: passed.
- `openspec validate --specs --strict`: all three main specifications passed.
- Disposable Podman command stubs with an actual Unix socket fixture: 54 wrapper scenarios passed, plus help without Podman. Covered exact remote URL despite a different ambient `CONTAINER_HOST`, success in Codex/shell/build combinations, rootful/invalid/empty/whitespace results, failed queries including stdout `true`, missing socket, disabled values, argument boundaries, spaces, symlinks, and default/parent mounts. Fixtures were outside the repository and the socket was removed afterward.
- Real integration checks unavailable: local `podman info` exits 125 because `newuidmap` is absent. Neither `/run/podman/podman.sock` nor `/run/user/1000/podman/podman.sock` is exposed; an explicit remote query also fails because the socket is absent. Image build, actual Codex/shell startup, persistence, and child-container access therefore could not be exercised against a real engine. Stub results do not establish real integration success.
