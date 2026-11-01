# Proposal

## Why

The updated `todo.md` identifies four remaining differences from the adjacent Claude Code and Antigravity wrappers: slash-only Unix endpoints, hidden response records, mixed-case YOLO values, and unbounded `/var/tmp`. Reusing their established validation and storage patterns closes these gaps while preserving Codex's response format and executable temporary storage.

## What Changes

- Adopt Claude Code's launch-endpoint validation: reject Unix paths consisting only of slashes before any Podman query, retaining valid absolute socket paths and local execution.
- Adopt Antigravity's boundary-preserving Podman output capture, accepting a normal optional final newline but rejecting additional blank or nonblank records. Keep one launch-engine record and Codex's two delegated-socket records, preserving host socket paths with spaces.
- Normalize `CODEX_YOLO` case before parsing, matching both reference wrappers. Preserve accepted boolean words, invalid-value rejection, shell behavior, native argument forwarding, and the independent exact `CODEX_CONTAINER_PODMAN=1` opt-in.
- Limit `/var/tmp` to 512 MiB, matching Antigravity's capacity and Codex's existing `/tmp` limit, while retaining Codex's `rw,exec,nosuid,nodev,mode=1777` policy and ephemeral lifetime.
- Add focused synthetic and real-engine regressions and update help, README, repository runtime guidance, and validation evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `podman-access`: Reject slash-only launch endpoints and validate response record boundaries without losing trailing blank records.
- `container-session`: Define case-insensitive YOLO environment parsing independently of Podman delegation and native arguments.
- `runtime-filesystem`: Extend temporary capacity contracts and documentation to `/var/tmp` at 512 MiB.

## Impact

Implementation affects `codex-container.sh`, `tests/test_wrapper.py`, `tests/test_runtime.py`, `README.md`, `AGENTS.md`, and `docs/validation.md`. No image package, dependency, or new configuration option is required. The existing filesystem contract and README explicitly say `/var/tmp` has no added capacity; their replacement is intentional. Additional response records and slash-only endpoints will fail earlier, mixed-case boolean spellings become valid, and writes exceeding `/var/tmp` capacity can fail.

## Non-goals

Changing adjacent repositories, agent authentication or state layout, executable temporary-storage policies, other mount capacities, delegation authority, container lifecycle management, or Codex's internal sandbox. Reference behavior is reused per task; differences between the two reference wrappers do not imply wholesale copying of either wrapper.
