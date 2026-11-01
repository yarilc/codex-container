# Design

## Context

See `proposal.md` for motivation and the three delta specs for acceptance behavior. The wrapper currently uses `podman run --rm --interactive --tty`, derives a name from a running-only listing through process substitution, and builds for every unsuccessful image-existence check. It already verifies the launch engine, optional delegation service, and private state before image operations.

`tests/test_wrapper.py` logs synthetic calls but only models `run` as a session. `tests/test_runtime.py` uses a PTY for shell sessions and has no pipeline or lifecycle assertions. The current Containerfile installs packages without COPY or ADD. Existing validation records explicitly leave real-engine checks incomplete; this proposal does not change that evidence.

## Goals / Non-Goals

**Goals:** Keep application execution separate from reservation; retain authoritative ownership across handled signals; preserve input, arguments, and exit statuses; express finite storage and minimal build inputs with existing tooling.

**Non-Goals:** A general container supervisor, recovery after host or engine loss, additional mount access, application-level nonterminal support, or configurable resource profiles. Existing workspace and Podman-access requirements remain authoritative and need no delta.

## Decisions

### 1. Reserve with create and retry only verified collisions

Read `podman ps --all --format '{{.Names}}'` into a checked variable. Use the existing physical-directory prefix and sanitization. Accept one to nine decimal digits, convert with explicit base ten, and start above the greatest supported index. The nine-digit input bound follows the references and avoids arithmetic overflow; generated indices can exceed that input bound after incrementing. A collision still remains safe because reservation is atomic.

Attempt `podman create --name ...` at most 20 times. After a failed create, retain its diagnostic and inspect candidate existence: status 0 confirms a collision; status 1 means no collision and the original creation failure is returned; other statuses are verification failures, never evidence for retry. Do not parse localized error strings or use `--replace`. The sequence of create attempts, rather than an application or attach status of 125, controls retrying.

List-then-run alone leaves a race. Fully random names would remove the familiar directory/index scheme. A global lock would unnecessarily serialize otherwise independent callers and would not coordinate non-wrapper clients.

### 2. Use an explicit ownership and interruption state

Model the invocation with states `unreserved`, `creating`, `reserved`, `attached`, and `finished`, plus a pending interruption and a primary exit status. Register traps before creation and use a private temporary directory created with a scoped umask for creation diagnostics and a client-side CID file. Retain the successful full container ID for all lifecycle operations; never infer ownership from a candidate name.

Run the creation client as a tracked child with stdin disconnected so it cannot consume application input. During creation, signal traps record the first pending interruption without exiting immediately. Reap the child even if a Bash wait is interrupted, reconcile its exit result and CID file, and only then honor the interruption. If creation succeeded, adopt the ID and clean it up without starting the application. If it failed, do not adopt a competing container. Preserve owned identity until removal is attempted. A CID file in a private directory closes the interval between the client producing its result and the parent assigning a shell variable.

Retain `--rm` for normal engine-side auto-removal, and use an idempotent EXIT cleanup as the fallback for reserved-but-unstarted containers, attach errors, and interruptions. Treat an already absent ID as success. When removal fails, print a diagnostic with the full ID and retain the primary status. Remove only this invocation's temporary files. Suppress recursive signal handling during final cleanup.

Using only a synchronous command substitution plus an immediate exit trap risks losing the successful create result. Looking up the name during cleanup risks removing a container created by somebody else.

### 3. Attach through a tracked client and bound interruption handling

Use `podman start --attach --interactive` for the reserved ID as a background client, explicitly restoring stdin with `<&0`. Disable attached-client signal proxying where the wrapper handles the same signals, so a signal delivered to the process group is not forwarded twice. Wait in the parent so traps remain responsive. Capture wait results in conditionals compatible with `set -Eeuo pipefail`.

For an uninterrupted session, propagate the attached application result, including 125, and never re-enter creation. For a wrapper TERM/INT/HUP, select status 143/130/129 and forward the corresponding signal to the running ID. Allow a five-second grace period, then force owned cleanup. Bound signal/removal operations and client reaping as well: use existing coreutils timeout support for engine control commands, and a bounded wait/watchdog for the tracked client, terminating and reaping that client if needed. Use a five-second control-command deadline and a final client-reaping deadline of five seconds; the grace period is not a promise that the entire shutdown completes within five seconds. Report engine failure instead of claiming successful removal.

A signal received between reservation and start prevents start. A signal during start triggers owned shutdown rather than a retry. Creation reconciliation assumes the engine remains responsive; cleanup cannot be guaranteed after service loss or forced client termination with an unknown engine outcome. No cleanup guarantee is made for SIGKILL.

### 4. Decide TTY at creation while preserving interactive input

Always retain interactive stdin, adding `--tty` only for `[[ -t 0 && -t 1 ]]`. Apply this at create time for both entrypoints; start cannot change a container's terminal configuration. Test all four stdin/stdout terminal combinations. Do not add shell command construction or modify Codex arguments. Preserve shell mode's existing behavior of ignoring Codex arguments.

Keeping `--tty` unconditionally breaks pipelines. Removing `--interactive` for redirected input would instead discard the data that nonterminal commands need.

### 5. Separate explicit builds from image-existence outcomes

Keep the current preflight ordering. An explicit build proceeds directly after preflights. Otherwise branch on the captured image-existence status: 0 uses the image, 1 builds, any other value emits an inspection diagnostic and exits. Preserve the underlying nonzero inspection/build status where possible. Build failure prevents reservation. Both modes and all access/YOLO combinations share this path.

### 6. Add only the two agreed tmpfs capacities

Add `size=512m` to `/tmp` and `size=32m` to `/run`; retain every existing mount option, including explicit exec for `/tmp` and the current execution policy for `/run`. Keep `/var/tmp`, ephemeral home, read-only root, persistent state, ownership, and workspace selection unchanged. These are maximum filesystem capacities, not preallocated memory or total process-memory limits. Fixed values avoid a new configuration surface before workload evidence justifies it.

### 7. Default-deny application build inputs

Add `.containerignore` with an exclude-all rule and an explicit inclusion for the root Containerfile. Podman's ignore-policy metadata remains available to the builder. Do not add COPY/ADD, change image packages, or alter runtime mounts. A default-deny policy also covers previously unknown credentials or scratch files without maintaining an incomplete blacklist.

Test actual Podman filtering using a disposable context containing dummy sensitive files at root and nested paths. Use a temporary verification Containerfile that copies the permitted context and asserts absence of sentinels; do not modify the production Containerfile. Test the production build separately. Future local source inputs must be deliberately included with the corresponding COPY/ADD change.

## Risks / Trade-offs

- Signal and wait races can leave containers or children behind. Mitigate with deterministic test barriers around creation and attachment, full-ID assertions, pending-interruption handling, and real engine tests.
- Service loss can make create results or removal unverifiable. Fail with diagnostics, bound shutdown control calls, and document residual cleanup; never remove by guessed name.
- Auto-removal can race explicit cleanup. Treat already absent IDs as success and preserve the application result.
- Small tmpfs capacities can break large temporary builds. Verify the exact capacities and execution behavior, document storage choices, and revise values only through an explicit later decision.
- A minimal context breaks future unlisted local build inputs. Document the inclusion policy and test both filtering and the production build.
- Mocked Podman cannot establish signal delivery, terminal behavior, concurrency safety, or mount enforcement. Keep opted-in engine checks and unavailable checks separate in `docs/validation.md`.

## Migration Plan

Implement and verify the wrapper lifecycle first, then the image and storage changes within this single change. Update help, README, repository runtime guidance, and the validation record before marking associated tasks complete. No state migration is needed. Existing stopped containers are retained and now affect new indices.

Use disposable private state with no Codex credentials for real-engine checks. Exercise both local and explicit same-host Unix launch connections when available, preserving absolute bind paths. Do not close unavailable real-engine tasks as passed. Synchronization and archival happen after implementation and review, not during proposal generation.

Rollback restores the prior wrapper and removes the new ignore policy; existing persistent state and workspaces need no conversion. Previously created residual containers require explicit identification and removal by their owners.
