# Proposal: Harden the Codex session baseline

## Why

Codex sessions run with Podman's default capability set, without no-new-privileges, without resource budgets, can expose `/`, the home directory or system directories read/write, have no lifetime limit, and install unpinned agent and tool versions. `claude-container` closed the same gaps in Wave 0 (tag `sandbox-ref-2`, change `2026-11-09-harden-session-baseline`). Wave 2 brings Codex to the same baseline before the Wave 3 network port, so the port starts from an equivalent wrapper. This change covers todo items B01–B05.

## What Changes

- **BREAKING** Every Codex and shell container, with or without Podman delegation and YOLO, runs with `--cap-drop=all` and `--security-opt=no-new-privileges`. Codex's own Linux command sandbox and the delegated Podman client must keep working; capabilities are not added back.
- **BREAKING** Every session gets explicit, validated resource budgets: `CODEX_CONTAINER_MEMORY_LIMIT` (default `4g`), `CODEX_CONTAINER_CPU_LIMIT` (default `2`) and `CODEX_CONTAINER_PIDS_LIMIT` (default `512`). Invalid values stop before any engine query. The created container's configured budgets are checked before start; runtime tests verify the effective cgroup v2 values. Budgets cannot be disabled.
- **BREAKING** The wrapper refuses a writable workspace (including the `--container-git-worktree` parent) that physically resolves to `/`, a system directory, `/tmp`, the caller's physical home or a WSL drive root `/mnt/<letter>`, before engine queries or state creation. Only the exact `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` overrides it, with a warning.
- New optional `CODEX_CONTAINER_RUN_TIMEOUT` sets the native Podman container lifetime in whole seconds; unset, empty or `0` disables it. A stderr notice reports a reached limit; the exit status is unchanged.
- `Containerfile` pins `@openai/codex` and `@fission-ai/openspec` to exact versions and the base image by digest; versions change only by explicit edit and rebuild, recorded in `docs/validation.md`.
- Help, README, AGENTS.md and `docs/validation.md` document the controls, defaults and the statement that budgets and tmpfs sizes do not bound workspace or state storage.

Semantics, defaults, formats and messages match Claude's wrapper with the `CODEX_CONTAINER_` prefix. The shared Python budget module, setup questions and qualification binding do not exist in Codex yet; they arrive with the Wave 3 network port.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: privilege dropping in every mode, explicit and verified resource budgets, documentation of these controls.
- `workspace-mounts`: refusal of sensitive workspace roots and the exact unsafe-workspace override.
- `container-session`: optional session lifetime limit with preserved exit status.
- `runtime-image`: pinned agent, OpenSpec and base image inputs, updated only through explicit maintenance.

## Impact

- `codex-container.sh`: validation of the new variables and workspace guard before engine queries, new `podman create` arguments, post-create budget inspection, lifetime notice, help text.
- `Containerfile`: pinned base digest and package versions.
- `tests/test_wrapper.py`: fake engine support for the budget inspection and new cases; `tests/test_runtime.py`: effective hardening, budgets, lifetime and Codex sandbox checks on a real rootless engine; new `tests/test_image_pins.py`.
- Documentation: `README.md`, `AGENTS.md`, `docs/validation.md`.
- Users: hosts without delegated cgroup v2 `cpu`/`memory`/`pids` controllers can no longer start sessions; launching from a sensitive directory requires the override; images rebuilt from this revision carry the pinned versions.
