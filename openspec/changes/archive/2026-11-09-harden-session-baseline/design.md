# Design

## Context

`codex-container.sh` (387 lines) parses wrapper options, checks for Podman, verifies the launch engine and optional delegation socket, validates private `CODEX_HOME`, inspects or builds the image, then reserves a name with `podman create` and attaches with `podman start`. It has no network modes, maintenance gate, setup or qualification. The reference implementation is `claude-container.sh` at tag `sandbox-ref-2` (archived change `2026-11-09-harden-session-baseline`), which applies the same controls to an equivalent lifecycle. The Wave 3 network port will later copy Claude's identifier-free `network/` and `setup/` trees, including `network/agent_budgets.py`, into this repository.

## Goals / Non-Goals

**Goals:**
- Same observable semantics, defaults, accepted formats and diagnostics as Claude, with the `CODEX_CONTAINER_` prefix, so that the Wave 3 port changes no behavior.
- All new validation happens before the first engine query, state creation or image operation.
- Real-engine evidence of the effective limits, not only of configured flags.

**Non-Goals:**
- Python budget normalization, setup questions, saved preferences and qualification binding (Wave 3).
- A maintenance gate for builds (Wave 3, C02); this change keeps today's explicit `--container-build` and missing-image build.
- Disabling Codex update notifications or other optional traffic (Wave 3, C06).
- Limits on workspace or state storage growth.

## Decisions

### D1: Port Claude's Bash code, not a new design
The validation block, workspace guard, `podman create` arguments, post-create inspection and lifetime notice are taken from `claude-container.sh` with only the prefix and the program name in messages changed. The regular expressions, ranges and messages stay identical so that a later `diff` between the wrappers shows only identity differences.
- Memory: `^([1-9][0-9]{0,15})([kmgKMG])$`, normalized to bytes, capped at 2^50.
- CPU: `^([0-9]{1,4})(\.([0-9]{1,3}))?$`, greater than 0 and at most 1024, normalized to NanoCpus for inspection; the original text is passed to `--cpus`.
- Process limit: 1 to 4194304.
- Lifetime: `^(0|[1-9][0-9]{0,9})$`.
- Defaults use `${VAR-default}`, so only an unset variable selects a default; the lifetime uses `${VAR:-0}`, so empty disables it.

Alternative: write Codex-specific validation. Rejected because it would diverge from the reference and complicate Wave 3.

### D2: Validation order
Immediately after option parsing (and before `command -v podman`), the wrapper validates budgets and lifetime, then resolves the workspace mount and applies the sensitive-workspace guard. Help still exits during parsing, before validation. This keeps every refusal free of engine queries and state creation and works on hosts without Podman.

### D3: Common container arguments
`podman_args` gains `--cap-drop=all`, `--security-opt=no-new-privileges`, `--memory=<bytes>`, `--cpus=<text>` and `--pids-limit=<n>` for every mode, and `--timeout <n>` when the lifetime is greater than zero. The existing keep-id user, read-only root and tmpfs layout are unchanged. The help sentence "No privileges or security-policy overrides are added" is replaced by the hardening description.

### D4: Post-create budget check
After a successful create and before `podman start`, the wrapper runs `timeout --kill-after=1s 10s podman inspect --type container --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}'` on the owned full ID, with the same pending-signal handling as the other control calls. A query failure or a mismatch exits non-zero with a diagnostic naming rootless cgroup v2 controller delegation; the existing EXIT cleanup removes only the owned container. There is no retry with other limits.

### D5: Lifetime notice
The wrapper records `SECONDS` before `podman start`. When the client exits non-zero and the elapsed time is at least the lifetime, it prints `codex-container: session lifetime limit reached (N s); exit status S` and keeps the status. Claude measured status 255 from the Podman 4.9.3 client after expiry; the Codex runtime test asserts the notice and a non-zero status, and records the observed value.

### D6: Workspace guard on physical paths
`WORKSPACE` is already `pwd -P`, and the worktree parent is its `dirname`, so the mount source is physical. The physical home is `cd -- "$HOME" && pwd -P`, falling back to `$HOME`. The refused set is the exact list of Claude's spec plus `^/mnt/[A-Za-z]$`; descendants remain allowed. The exact override `CODEX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` prints `codex-container: WARNING: sensitive workspace explicitly exposed read/write: <path>`.

### D7: Pinned image inputs
- Base: `docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`, the digest recorded for `sandbox-ref-2`, so both wrappers share a base until the next maintenance.
- `ARG OPENSPEC_VERSION=1.16.0`, as in Claude.
- `ARG CODEX_VERSION=<exact>`: the current published `@openai/codex` version, resolved on the host at implementation time and verified with `codex --version` after the rebuild.
- `npm install --global` uses `@openai/codex@${CODEX_VERSION}` and `@fission-ai/openspec@${OPENSPEC_VERSION}`.

Self-update inside a session is already impossible because the image root, including the global npm prefix, is read-only. A comment in `Containerfile` points to the update procedure in the README and `docs/validation.md`.

### D8: Tests
- `tests/test_wrapper.py`:
  - the fake engine records create arguments and answers the budget inspection, overridable with `FAKE_AGENT_BUDGETS`;
  - table-driven accepted and rejected values with no engine call;
  - flags in every mode and with delegation;
  - mismatch and inspection failure with owned cleanup;
  - lifetime argument and notice;
  - refused workspaces (fake `HOME`, worktree parent, symlink to `/etc`, `/mnt/d` and its project subdirectory, exact and non-exact override);
  - help content without engine calls.
- `tests/test_runtime.py` (real rootless engine through `tests/run-runtime.sh`):
  - zero capability sets and `NoNewPrivs: 1`;
  - cgroup `memory.max`, `pids.max` and `cpu.max` for default and overridden budgets;
  - enforced process limit;
  - lifetime expiry and early exit;
  - delegated `podman info` and child container;
  - Git, OpenSpec and bubblewrap;
  - Codex's own Linux sandbox running a command, using the sandbox subcommand of the pinned version (for example `codex sandbox linux -- true`), with no credentials or model request.
- New `tests/test_image_pins.py` rejects unpinned inputs.

Existing fixtures use descendants of `/tmp` and of the native volume, which remain allowed.

## Risks / Trade-offs

- [Host without delegated cgroup v2 `cpu`, `memory` or `pids` controllers] → The launch stops with an actionable diagnostic; the README names the requirement. There is no silent fallback.
- [Codex's Linux sandbox needs a capability or privilege gain] → Claude measured bubblewrap working under the same hardening on this WSL target. If Codex still fails, record it, document the Codex sandbox configuration that works, and do not re-privilege the container.
- [4 GiB or 512 processes too small for some builds or test suites] → Operators override the budgets per launch; values cannot disable a budget.
- [Users who launch from their home directory or a drive root] → Refused with guidance; the exact override exists for deliberate use.
- [Pinned versions age] → The documented maintenance procedure updates them deliberately; the unit test prevents accidental unpinning.
- [The budget inspection adds an engine call per launch] → Bounded by a 10-second timeout and part of the existing cleanup path.

## Migration Plan

1. Implement on branch `harden-session-baseline`; run the unit suites in the sandbox and the real-engine suite on the host.
2. Users rebuild with `--container-build` to get the pinned image; existing images keep working, but only a rebuild applies the pins.
3. Users who launched from a refused directory move to a project subdirectory or set the override deliberately.
4. Rollback: revert the commit; no state format changes.
