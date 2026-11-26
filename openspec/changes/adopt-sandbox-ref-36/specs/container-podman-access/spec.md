# Spec Delta

## REMOVED Requirements

### Requirement: Explicit Podman opt-in
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: A leftover exact `CODEX_CONTAINER_PODMAN=1` stops the launch with guidance (`container-session`); add the needed images as toolchains.

### Requirement: Installed command without host connection when disabled
**Reason**: Host Podman delegation is removed, so no session has a host connection to disable. The runtime keeps its Podman command as the client of the session container engine.
**Migration**: No session receives a host Podman socket (`container-isolation`). A session reaches only its own engine, when the library holds an image (`session-container-engine`).

### Requirement: Enabled access uses the host rootless service
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or mount.

### Requirement: Keep one image for both access modes
**Reason**: Host Podman delegation is removed, so there are no access modes to keep one image for.
**Migration**: Image selection and builds stay in `runtime-image`; the image keeps the Podman command for the session's engine.

### Requirement: Document the access boundary
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: The README documents the session container engine, image toolchains and the migration instead (`session-container-engine`).

### Requirement: Reject unverified Podman services before startup
**Reason**: Host Podman delegation is removed, so there is no delegated service to verify.
**Migration**: The launch engine is still verified before any image operation (`container-session`, "Verified launch engine").

### Requirement: Verified launch engine
**Reason**: The requirement concerns the launch engine, not delegation; it moves to `container-session` without its delegation scenarios.
**Migration**: See `container-session`, "Verified launch engine".

### Requirement: Local or explicit same-host Unix execution
**Reason**: The requirement concerns the launch engine, not delegation; it moves to `container-session` unchanged.
**Migration**: See `container-session`, "Local or explicit same-host Unix execution".

### Requirement: Explicit delegation socket selection
**Reason**: Host Podman delegation is removed; `CODEX_CONTAINER_PODMAN_SOCKET` is ignored.
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select.

### Requirement: Preserve Podman verification response boundaries
**Reason**: The launch response rule concerns the launch engine; it moves to `container-session` without the delegated two-record response.
**Migration**: See `container-session`, "Preserve Podman verification response boundaries".

### Requirement: Document verification input boundaries
**Reason**: The documentation rule concerns the launch engine; it moves to `container-session` without the delegated format.
**Migration**: See `container-session`, "Document verification input boundaries".

### Requirement: Delegation only in unrestricted mode
**Reason**: Host Podman delegation is removed in every mode.
**Migration**: A leftover exact `CODEX_CONTAINER_PODMAN=1` stops the launch in every network mode (`container-session`, "Leftover delegation opt-in is refused").
