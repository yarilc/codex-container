# Proposal

## Why

The six gaps recorded in `todo.md` make concurrent starts, interrupted sessions, redirected input, and image failures unreliable, while temporary storage and build inputs lack explicit bounds. Addressing them together allows container creation, attachment, and cleanup to share one consistent ownership model.

## What Changes

- Reserve directory-based container names atomically with `podman create`, considering stopped containers, parsing bounded decimal indices, propagating listing errors, and retrying confirmed collisions at most 20 times.
- Track the container created by each invocation, forward TERM/INT/HUP, use bounded shutdown handling, and clean up only that container while preserving application exit codes, including 125.
- Allocate a TTY only when stdin and stdout are terminals, preserving redirected stdin through attachment in both Codex and shell modes.
- Build automatically only when image existence returns status 1; terminate on other inspection errors. Preserve explicit builds and image overrides.
- Limit `/tmp` to 512 MiB and `/run` to 32 MiB while preserving existing writable mounts and execution permissions.
- Add a default-deny `.containerignore` with the current `Containerfile` as the only application build input.
- Add synthetic and opted-in engine regression coverage and update help, README, runtime guidance, and validation records.

## Capabilities

### New Capabilities

- `container-session`: Atomic session naming, container ownership, attachment, terminal selection, signal forwarding, cleanup, and exit status propagation.
- `container-image`: Image existence handling, explicit and automatic builds, and minimal build inputs.

### Modified Capabilities

- `runtime-filesystem`: Explicit capacities for `/tmp` and `/run`, with existing permissions, persistence, and ephemeral storage behavior retained.

## Impact

Implementation will affect `codex-container.sh`, add `.containerignore`, and update `tests/test_wrapper.py`, `tests/test_runtime.py`, applicable runtime helpers, `README.md`, `AGENTS.md`, and `docs/validation.md`. No new runtime dependency or configuration switch is intended. The existing `workspace-mounts` and `podman-access` contracts remain applicable, including launch-engine checks before image operations and use of the physical launch directory for naming. Observable changes include stopped containers influencing indices, failures replacing unintended builds, TTY-free pipeline support, and finite temporary storage capacities.

## Non-goals

Changing mount scope, delegation or YOLO policy, state privacy, image packages, Codex's own terminal requirements, `/var/tmp` or home capacities, or overall container memory limits. This change does not provide cleanup after SIGKILL, host failure, or loss of the Podman service, and does not treat reference-project tests as verification of this wrapper.
