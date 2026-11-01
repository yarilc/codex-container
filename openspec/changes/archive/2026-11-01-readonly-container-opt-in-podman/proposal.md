# Proposal

## Why

The wrapper currently exposes a writable image filesystem and always grants access to the host Podman service. Sessions should protect the runtime image from modification and receive host Podman service access only through an explicit opt-in.

## What Changes

- **BREAKING**: Run both Codex and shell sessions with a read-only image filesystem; retain writable workspace mounts, persistent `CODEX_HOME`, and temporary runtime directories.
- **BREAKING**: Expose the host Podman socket only when `CODEX_CONTAINER_PODMAN` equals exactly `1`. Unset, empty, and all other values disable the integration.
- Keep the Podman command installed in the existing single image. Host Podman remains required to build and launch the runtime.
- Skip host API socket validation and mounting when the integration is disabled; set `CONTAINER_HOST` only when enabled.
- Update help, setup documentation, and verification guidance for both access modes and writable exceptions.

## Capabilities

### New Capabilities

- `runtime-filesystem`: Read-only image files with explicit writable persistent and temporary locations in both entry modes.
- `podman-access`: Environment-controlled exposure of the host API socket and connection environment, with the Podman command always installed.

### Modified Capabilities

- `workspace-mounts`: Make child-container access conditional on the Podman opt-in while preserving absolute workspace paths and existing writable mount selection.

## Impact

Implementation will primarily affect `codex-container.sh`, `README.md`, and repository guidance in `AGENTS.md` that currently calls the socket mandatory. `Containerfile` retains its Podman package and may need runtime directory preparation only. Existing sessions that launch child containers through the host service will need `CODEX_CONTAINER_PODMAN=1`. Writable host binds retain their existing scope, including the broad parent-directory opt-in. No privileged mode, new host bind mounts, or change to Codex argument forwarding is proposed.
