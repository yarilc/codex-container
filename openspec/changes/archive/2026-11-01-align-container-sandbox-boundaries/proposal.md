# Proposal

## Why

The wrapper verifies only the optional delegated Podman service, leaving the engine used for builds and startup unchecked, and mounts persistent Codex state without checking its privacy. Antigravity's newer wrapper demonstrates stronger preconditions and support for same-host containerized callers that this project can adopt while preserving its existing mount model.

## What Changes

- **BREAKING**: Require a verified Linux rootless launch engine before image inspection, build, or startup, even when session Podman access is disabled. Reject named connections, TCP/SSH contexts, and unverifiable engine responses; support local execution and explicit same-host Unix service connections.
- **BREAKING**: Create missing `CODEX_HOME` privately and reject inaccessible, incorrectly owned, or group/other-accessible state directories. Preserve the default `~/.codex`, overrides, and the ephemeral home with nested persistent state.
- Add `CODEX_CONTAINER_PODMAN_SOCKET`, with selection precedence of nonempty override, explicit Unix `CONTAINER_HOST`, then `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. Verify the selected service and use its reported host-side socket path for delegation.
- Preserve exact `CODEX_CONTAINER_PODMAN=1` activation, disabled-mode environment removal, workspace semantics, read-only root, and current YOLO behavior.
- Add focused wrapper and opt-in real-runtime checks for preconditions, socket remapping, mount boundaries, identity, and state persistence; document security boundaries and migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `podman-access`: Verify the launch engine independently of delegation, support explicit Unix socket selection and host-path remapping, and clarify host access boundaries.
- `runtime-filesystem`: Require private, caller-owned persistent Codex state while retaining existing writable and ephemeral locations.

## Impact

Implementation affects `codex-container.sh`, `README.md`, and runtime guidance in `AGENTS.md`; new verification files belong under `tests/` with results and limitations recorded in `docs/validation.md`. No new production package dependency is expected; tests use standard-library Python and optional real rootless Podman. Existing insecure state directories need an explicit user correction or a private Linux `CODEX_HOME`; no automatic recursive permission changes or state migration are introduced.

Dedicated state defaults, tmpfs limits/permissions, terminal allocation, naming and signal lifecycle changes, authentication helpers, network restrictions, and custom seccomp/capability policies are out of scope. The Antigravity internal sandbox failure is not evidence of a Codex failure and introduces no workaround here.
