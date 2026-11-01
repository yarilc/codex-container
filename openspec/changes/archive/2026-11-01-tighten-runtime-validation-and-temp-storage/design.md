# Design

## Context

See `proposal.md` for motivation. `codex-container.sh` currently matches Unix endpoints with `unix:///?*`, which admits slash-only paths longer than `/`. Its two verification command substitutions discard all final newlines before validation. YOLO parsing enumerates lowercase and uppercase spellings but rejects mixed case. `/var/tmp` is already writable, executable, private to the session lifetime, and protected by nosuid/nodev, but has no explicit size.

The synthetic fixture in `tests/test_wrapper.py` uses Python `print` for verification responses, so it always adds a final LF. Existing rejection matrices cover extra nonblank lines but not hidden trailing blank records. `tests/test_runtime.py` already inspects `/tmp` and `/run` capacities and exercises executable temporary storage and session recreation. README and AGENTS.md explicitly describe `/var/tmp` as lacking an added capacity; those statements must be replaced during implementation.

## Goals / Non-Goals

**Goals:** Reuse the reference wrappers' existing patterns per task, retain Codex-specific formatting and execution requirements, and make new rejection boundaries directly testable.

**Non-Goals:** General URI canonicalization, querying whether an unverified endpoint is same-host, changing socket precedence, normalizing arbitrary boolean whitespace, copying authentication/state behavior, or changing the container lifecycle. Adjacent repositories are read-only references, not implementation targets.

## Decisions

### 1. Adopt Claude Code's lexical endpoint check

For a nonempty `CONTAINER_HOST`, separate the `unix://` scheme and require an absolute path with at least one character other than `/`, as in `../claude-container/claude-container.sh`. Place rejection before the launch-engine query. Keep unset/empty local mode, named-connection rejection, and existing rootless/remote checks. Preserve the supplied valid path verbatim; do not resolve it in the caller's namespace because the explicit Unix endpoint may be remapped there.

A stricter socket-existence check would add a different requirement and is unnecessary for rejecting slash-only endpoints. Copying Antigravity's current wildcard would retain the specific bug that this task addresses.

### 2. Adopt Antigravity's capture technique, preserving Codex's record formats

Use a shared small capture helper modeled on `../antigravity-container/antigravity-container.sh`: append a non-newline sentinel only after Podman succeeds, let command substitution retain the final LF bytes, remove the appended sentinel, and remove at most one final LF. A query's nonzero exit remains a failure; printing the sentinel unconditionally must not mask it.

The helper captures output, while format-specific validation checks one launch record or two delegated records. Reject remaining CR characters and unexpected LF separators. For launch output, retain the existing rootless, Linux, remote-status, and extra-field checks. For delegated output, retain `true` on the first record and the entire absolute host socket path on the second, including spaces. Keep the exact existing Podman format string containing the intentional line break between those two fields.

This acceptance table applies after Podman succeeds:

| Response payload | No final LF | One final LF | Two or more final LF |
| --- | --- | --- | --- |
| One valid launch record | Accept | Accept | Reject |
| Two valid delegated records | Accept | Accept | Reject |
| Wrong number of records, blank required record, CR, or invalid fields | Reject | Reject | Reject |

Leading or interior extra records are rejected as well. The table describes the trailing terminator, separately from the LF separating delegated fields. Standard command substitution or trimming all trailing whitespace would hide the malformed records. Copying Antigravity's single-record validator wholesale would instead reject legitimate Codex delegated responses.

Extend the fixture with exact-byte output control alongside its existing convenient print defaults. That lets tests distinguish a normal terminator, its absence, and an extra blank record without depending on Python print behavior.

### 3. Normalize only YOLO case

Assign the raw `CODEX_YOLO` default-empty value to a variable and apply Bash lowercase expansion before the existing boolean cases, matching both reference wrappers. Keep `1/true/yes`, `0/false/no`, unset/empty behavior, and actionable errors for all other values. Do not trim whitespace or accept new words. Preserve shell-mode validation and suppression of wrapper-added Codex arguments. Do not apply the helper or normalization to `CODEX_CONTAINER_PODMAN`, whose enabling value remains exactly `1`.

This retains native argument forwarding: a disabled environment switch does not remove a user-supplied `--yolo` argument or override saved application settings. A generic permissive boolean parser would obscure that separation.

### 4. Use Antigravity's capacity with Codex's execution policy

Add `size=512m` to the existing `/var/tmp` tmpfs, retaining its explicit exec, rw, nosuid, nodev, and mode 1777 options. Antigravity uses 512 MiB and Claude uses 256 MiB; the selected value matches Antigravity and Codex's current `/tmp` capacity. Both references use noexec for `/var/tmp`, but the agreed scope explicitly preserves Codex's executable storage policy.

Keep `/tmp` at 512 MiB, `/run` at 32 MiB, ephemeral home without an explicit cap, and existing persistent binds. These independent maxima are not reserved memory or a total container memory limit. Verify `/var/tmp` with effective statvfs capacity, mount flags/mode, an executable file, and a new-session absence check. Capacity inspection avoids allocating the full 512 MiB during tests; retain the existing `/run` exhaustion regression.

## Risks / Trade-offs

- A capture sentinel can mask query failures if appended unconditionally. Mitigation: append only on success and test failed queries that emit valid-looking output at both endpoints.
- Record validation can reject normal output if its terminator is counted as a record. Mitigation: exact-byte fixture cases for zero, one, and multiple final LF bytes, plus actual local/Unix engine checks where available.
- Reusing a single-record helper unchanged would break socket paths or the delegated format. Mitigation: distinct format validation and regression cases for host paths with spaces and remapped sockets.
- A finite `/var/tmp` can break workloads using more temporary storage. Mitigation: document the fixed maximum and use existing workspace storage when the workload requires more; do not silently fall back to another mount.
- Reference wrappers differ in capacity and execution policy. Mitigation: keep the explicit decisions above and test Codex's selected behavior rather than assuming complete equivalence.

## Migration Plan

Apply the endpoint and response changes, then boolean parsing and the mount capacity, with tests and documentation delivered alongside each area. No image rebuild, configuration migration, or credential copying is needed. New sessions receive the updated capacity; running sessions keep their existing mounts.

Run the synthetic wrapper suite, Bash syntax and whitespace checks, strict change validation, and the opted-in real-engine suite with disposable native Linux state and host-absolute paths. Record unavailable checks separately from passed ones in `docs/validation.md`. Rolling back the wrapper restores the previous parsing and capacity behavior without modifying persistent state. Main-spec synchronization, archival, and commits require their subsequent workflow request.
