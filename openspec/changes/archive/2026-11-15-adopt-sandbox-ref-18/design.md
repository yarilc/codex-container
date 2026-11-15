# Design

## Context

See proposal.md for the findings. Current Codex lifecycle:

- `codex-container.sh:910` creates the container with the session label `$ownership_label` (`io.codex-container.session`)
  and a private CID file.
- `cleanup()` recovers the ID from the CID file only (`recover_container_id`).
  With no ID it prints "creation outcome unresolved" (`codex-container.sh:786`).
- `codex-container.sh:927` treats any existing container with the candidate name as a
  collision.

The reference (`claude-container.sh`, `recover_container` and the create loop)
checks the label before treating a name as taken, and recovers an interrupted
creation with `ps --all --no-trunc --filter label=<label>=<token>`, then
confirms the label with `inspect` before removing.

## Goals / Non-Goals

**Goals:**
- Adopt `sandbox-ref-18` byte for byte and declare Codex's agent variables.
- Never leave or skip a container that carries this session's label.

**Non-Goals:**
- Rewriting Codex's lifecycle into the reference's structure. Only the two
  reconciliation rules are ported.
- Moving the lifecycle into shared code.

## Decisions

### Agent variables

Codex declares `CODEX_`, `OPENAI_`. Prefixes cover controls a later release may add;
exact names are used where a prefix would also catch unrelated tools (for
example `GOOGLE_` would catch a Google Cloud SDK toolchain's settings).

### Ownership-checked collision

After a failed create with no ID, run `container exists` and, when it
exists, `inspect --type container --format '{{index .Config.Labels "<label>"}}'`.
Only a different label is a collision. The same label leaves the creation
pending, so cleanup reconciles it, and the wrapper exits with the create
status. An `inspect` failure is reported like an unconfirmed collision today:
exit with the create status, no retry.

Alternative: retry on the same label. Rejected: the reference reports the
original failure, and a retry would double the credential-bearing containers.

### Label recovery in cleanup

When `creating` is still set and `recover_container_id` found no ID, cleanup
runs `timeout --kill-after=1s 5s podman ps --all --no-trunc --filter
label=<label>=<token> --format '{{.ID}}'`. Exactly one 64-hex ID, whose label
`inspect` confirms, becomes `container_id` and is removed by the existing
removal path. Several IDs, an invalid ID, a failed lookup or a failed
confirmation keep today's "unresolved" message. The lookup shares the
20-second shutdown deadline.

Alternative: remove every ID the filter returns. Rejected: the label already
identifies one session, so more than one ID means something unexpected, and
the reference also refuses to guess.

### Overlap check

Same Bash rule as Claude and OpenCode: `readlink -m` of the state path,
compared with the workspace mount (the parent in worktree mode) in both
directions, after the tool prerequisites and before the first engine call.
The message is `CODEX_CONTAINER_STATE_DIR must not overlap the workspace:
<path>`.

## Risks / Trade-offs

- [The stricter alignment test or the shared overlap check fails on a Codex
  test fixture] → The adoption suites show it; the fixture is adapted in this
  change and recorded in `docs/validation.md`.
- [A legitimate toolchain sets a now-protected variable] → `launch-env`
  warns and leaves it out; the operator forwards it explicitly.
- [The extra lookup slows an interrupted shutdown] → It is bounded by the
  shared shutdown deadline.

## Migration Plan

Adopt on branch `adopt-sandbox-ref-18`, run the suites, merge with `--no-ff`.
The operator pushes and reruns `--container-setup` on the three hosts.
Rollback before the operator setup is a revert of the merge.
