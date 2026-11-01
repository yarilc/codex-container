# Proposal

## Why

With `CODEX_CONTAINER_PODMAN=1`, the wrapper currently checks only that the expected Unix socket exists. That does not establish that the service is reachable or actually rootless, despite the existing rootless-service contract.

## What Changes

- Query the exact socket that will be exposed to the session and require the connected engine to report rootless operation, following the socket-validation approach in the Antigravity wrapper.
- Reject rootful engines, failed queries, and missing or unexpected rootless values with actionable errors before image inspection, building, or session startup.
- Apply the check to both Codex and shell modes only when `CODEX_CONTAINER_PODMAN` equals exactly `1`.
- Document the automatic check and failure behavior while preserving the fixed socket path, existing mounts, and disabled-mode behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `podman-access`: Require positive verification that the service behind the exposed socket is rootless and document rejection of unverified services.

## Impact

- Implementation will affect the enabled-access preflight in `codex-container.sh`, wrapper help, `README.md`, and runtime guidance in `AGENTS.md` where appropriate.
- Uses the existing host Podman CLI; no image changes or additional dependencies are required.
- Enabled sessions that previously accepted an existing but unreachable or rootful socket will fail earlier. Disabled sessions retain their current behavior.
- General runtime-engine validation, remote-context restrictions, configurable sockets, and nested-wrapper socket remapping from Antigravity are outside this change.
