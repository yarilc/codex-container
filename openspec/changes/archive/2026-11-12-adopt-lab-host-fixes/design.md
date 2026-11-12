# Design

## Context

Codex `main` (`04481b1`) pins `sandbox-ref-10`. Running `tools/propagate.py`
(claude-container) from `sandbox-ref-10` to `sandbox-ref-11` reports 21
changed shared files, no added or removed file and nothing "not adopted".
It also reports these runner modes: `--shared`, `--setup`, `--setup-runtime`,
`--qualification`, `--guard` and `--network`.

A trial adoption, since discarded, showed that the shared files alone fail
21 tests in `tests/test_wrapper.py`. `network/session.py` now imports
`network/agent_budgets.py` and queries `{{.Host.CgroupControllers}}`. The
wrapper fixture copies neither that module nor any answer to the query.

The Codex launcher differs from the Claude launcher in ways that this change
keeps:

- it uses `capture_engine_info` instead of `capture_response`;
- the socket query returns rootless state and path on two lines;
- `/tmp` and `/var/tmp` are 512 MiB with `exec`, and `/run` is 32 MiB with
  mode `1777`;
- messages say "session not started".

Its budget inspection (`codex-container.sh` around line 824) requires the
exact `memory cpu pids` triple. Both build calls (lines 457 and 467) have no
secret. The `Containerfile` uses the same digest-pinned
`node:22-bookworm-slim` base and the same plain `apt-get update` as Claude
before `sandbox-ref-11`.

`tests/test_runtime.py` already runs `bwrap --dev /dev` and `codex sandbox`
inside a session. The new device mounts are therefore exercised by the
existing runtime suite.

After the first implementation, the operator's setup on the Rocky host
failed in the qualification gate. Podman reported "chowning container
workdir to container root", requested as `31600276:31600276`, for
`/workspace`. The cause is in the recipe:

- In the Codex image, `/workspace` carries the container start time; in the
  Claude image it carries the build time.
- Claude has a `COPY` after `WORKDIR /workspace`, which creates the directory
  in a layer. Codex declares `WORKDIR` as its last step before `ENTRYPOINT`,
  so the Podman builder never materializes it.
- The shared gate containers (`network/qualify.py`, `Gate.common()`) pass no
  `--workdir`. Podman then creates the missing image workdir and chowns it at
  start, and that chown fails for a domain UID under `--userns=keep-id`.
- Agent containers are not affected, because their `--workdir` is the
  mounted workspace.

OpenCode and Antigravity have the same pattern. Pi declares no `WORKDIR`.

## Goals / Non-Goals

**Goals:**
- Codex adopts `sandbox-ref-11` byte for byte and gets launcher and recipe
  behavior equivalent to the Claude reference for the six lab-host fixes.
- Every Codex-specific mount, size and message stays as it is, except where
  the specs change.

**Non-Goals:**
- Changing the guard's `/run/secrets` rule. It is shared code, and its
  hardening is deferred until after the operator host tests.
- Changing the shared files. If a shared file fails here, the procedure in
  `docs/propagation.md` applies: fix it in claude-container under a new tag.
- OpenCode, Pi and Antigravity.
- Passing `--workdir /` to the gate containers in `network/qualify.py`. That
  is shared code, so it belongs to a claude-container change under a new tag
  and is tracked as a follow-up.

## Decisions

1. **The tool's branch carries the whole change.**
   `propagate.py --apply` creates `adopt-sandbox-ref-11`. The wrapper
   adaptations are committed on that branch, and it is merged once. A
   separate adoption merge would leave `main` with failing wrapper tests.
   Alternative considered: two merges. Rejected, because the intermediate
   state of `main` would be red.

2. **Port the Claude launcher logic and keep Codex idioms.**
   - Controllers come from one `capture_engine_info info --format
     '{{.Host.CgroupControllers}}'` call, validated with the same pattern
     `^\[([a-z_]+( [a-z_]+)*)?\]$`.
   - The launcher builds `budget_args` and expected values. An undelegated
     `pids` controller gets `--pids-limit=-1`.
   - The inspection accepts `0` or `-1` for unenforced pids and `0` for
     unenforced memory and CPU.
   - The query runs in every mode, before the restricted-mode prerequisites.
     The notices use the `codex-container:` prefix.

   Alternative considered: a shared helper for budgets in `network/`.
   Rejected, because the launcher must stay usable without host Python in
   unrestricted mode.

3. **Socket URL:** run `host_socket=${host_socket#unix://}` before the
   absolute-path check, so the existing diagnostic still covers empty and
   relative values.

4. **Device mounts:** drop `--read-only-tmpfs=false` and add:
   - `--tmpfs /dev:rw,nosuid,noexec,mode=755,size=65536k`;
   - `--mount type=devpts,destination=/dev/pts`;
   - `--mount type=tmpfs,destination=/dev/shm,ro=true`;
   - `--mount type=tmpfs,destination=/run/secrets,ro=true`.

   `/dev` stays `noexec` even though Codex `/tmp` keeps `exec`, because
   nothing needs to execute from `/dev`. The reference uses the same layout.
   Alternative considered: keep `--read-only-tmpfs=false` on hosts where it
   works. Rejected, because the result would depend on the engine version.

5. **Build secret:** compute `build_secret=(--secret id=build-ca,src=...)`
   from the already resolved `ca_bundle` and pass it to both `podman build`
   calls. Add `!podman-build-secret*` to `.containerignore`.
   `ca_bundle` is resolved before the build calls, so no reordering is
   needed. Pi needs a reordering, Codex does not.

6. **Recipe:** copy the reference `RUN` prologue and epilogue as they are:
   - the Node.js root export into the bootstrap bundle;
   - the optional `build-ca` append;
   - the `sed` to `https://`;
   - `Acquire::https::CAInfo` on both apt calls;
   - `rm` of the bundle before `npm install`.

   `tests/test_image_pins.py` gains the reference's transport checks, with
   Codex wording.

7. **Wrapper fixtures:**
   - `tests/test_wrapper.py` copies `network/agent_budgets.py` into the fake
     installation;
   - the fake engine answers `{{.Host.CgroupControllers}}` from
     `FAKE_CONTROLLERS`, by default `[cpu memory pids]`;
   - new cases cover partial controllers, unenforced-budget inspection, the
     `unix://` socket, the mounts in every mode and the build secret with
     and without trust.

8. **Image working directory:** add `mkdir -p /workspace` to the package
   `RUN` step that already creates `/codex-home`, and keep
   `WORKDIR /workspace`. The directory is then in a layer, root-owned with
   mode 755, and Podman neither creates nor chowns it.
   `tests/test_image_pins.py` rejects a `WORKDIR` that no build step
   creates.

   Alternatives considered:
   - Move `WORKDIR` before the `COPY`, as in Claude. Rejected, because it
     relies on a builder side effect.
   - A separate `RUN mkdir`. Rejected, because it adds a layer.

## Risks / Trade-offs

- [A read-only `/dev/shm` breaks tools that need POSIX shared memory, such
  as Python multiprocessing semaphores] → This is accepted in the
  reference. The runtime suite and `codex sandbox` verify the common
  tooling. A break is recorded in `docs/validation.md`, and no writable
  `/dev/shm` is added without a new change.
- [A host without delegated `memory` or `pids` lets an agent exhaust host
  RAM or processes for the user] → The notices are printed on every launch
  and in the setup plan. The qualification identity binds the enforced set,
  and the README states the risk.
- [Shared tests may encode Claude-only literals] → `tests/test_alignment.py`
  and the tool's "not adopted" output catch these. A failure caused by the
  wrapper is fixed here; a shared defect stops the adoption.
- [Every installation becomes stale] → The validation record and the README
  tell operators to rebuild and rerun setup.
- [The workdir failure cannot be reproduced on this host, which has no
  domain UID] → Verify that `/workspace` is in the exported layer and that
  its time does not change when a container starts. The operator's Rocky
  setup is the final check.

## Migration Plan

1. Merge `adopt-sandbox-ref-11` into `main` with `--no-ff` after validation.
   The operator pushes it.
2. On each host: `--container-setup` with refresh approved.
3. Rollback: before the push, reset `main` to `04481b1`. After the push,
   revert the merge. Codex then returns to `sandbox-ref-10`.
