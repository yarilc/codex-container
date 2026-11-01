# Tasks

## 1. Read-only runtime filesystem

- [x] 1.1 Add the shared read-only root policy and writable tmpfs locations to `codex-container.sh`, retaining workspace and nested persistent Codex mounts; verify captured run arguments in Codex, shell, and YOLO modes and run `bash -n codex-container.sh`.
- [x] 1.2 Verify effective mount permissions with real Podman and a disposable workspace and `CODEX_HOME`: inspect read-only root, prove writes fail on an otherwise user-writable image path, and confirm temporary/home writes, temporary executable use, persistent Codex state, and ephemeral cleanup across sessions. Prepare image mountpoint directories only if required and verify a rebuilt image if changed.
- [x] 1.3 Update wrapper help and README to explain read-only image files, persistent writable binds, ephemeral locations, and broad workspace mount precedence; verify `--container-help` and the documented paths against the effective runtime mounts.

## 2. Optional host Podman service access

- [x] 2.1 Gate socket validation, socket binding, and `CONTAINER_HOST` on exact `CODEX_CONTAINER_PODMAN=1`, keeping Podman installed and existing image selection unchanged; verify captured arguments for unset, empty, `0`, `true`, and `1` values in both entry modes, including a caller-set `CONTAINER_HOST` that must not leak into disabled sessions.
- [x] 2.2 Verify the integration with real Podman: default sessions start without the host API socket, retain `command -v podman`, and have no supplied socket or `CONTAINER_HOST`; enabled sessions report an actionable missing-socket error or reach the usable host service as appropriate. Verify switching back to disabled mode removes the connection without changing the image.
- [x] 2.3 Update README setup and examples, help environment documentation, and `AGENTS.md` runtime guidance for conditional socket setup and the exact opt-in; verify examples cover both Codex and shell mode and distinguish the installed client from optional host access.

## 3. Integration and final verification

- [x] 3.1 Verify preserved argument order and boundaries, default and parent mounts, paths containing spaces, symbolic links, naming, working directory, build mode, and `CODEX_CONTAINER_IMAGE`; with enabled access, launch a disposable child container using the identical absolute workspace bind path and verify the read-only parent runtime does not break that operation.
- [x] 3.2 Verify Codex startup and OpenSpec availability in the final runtime and run `bash -n codex-container.sh`, `git diff --check`, `openspec validate readonly-container-opt-in-podman --strict`, and `openspec validate --specs --strict`; record real runtime results separately from mocks and explicitly identify unavailable checks.

## Workflow follow-up

- Synchronize delta specifications into the main specifications and archive the completed change through the appropriate OpenSpec workflow after implementation and verification.
