# Design

## Context

`codex-container.sh` builds `podman_args` around line 535. For every Codex
and shell container it passes, among others:

- `--read-only`, with automatic read-only tmpfs provisioning enabled;
- `--tmpfs '/dev:rw,nosuid,noexec,mode=755,size=65536k'`;
- `--mount type=devpts,destination=/dev/pts`;
- `--mount type=tmpfs,destination=/dev/shm,ro=true`;
- `--mount type=tmpfs,destination=/run/secrets,ro=true`;
- the Codex tmpfs mounts: executable `/tmp` and `/var/tmp` (512 MiB), `/run`
  (32 MiB), and `/codex-home` in shared-state mode.

The same layout was fixed in the Claude reference. Its validation record
(claude-container `docs/validation.md`, "Engine-provided `/dev` for
pseudo-terminals") measured, on this host:

- the explicit `devpts` is `mode=600,ptmxmode=000`, and allocation fails;
- adding `--device /dev/ptmx` does not help: the engine replaces it with a
  `pts/ptmx` link;
- Podman rejects `ptmxmode` as a `devpts` mount option;
- the engine's `devpts` is `mode=620,ptmxmode=666`, and `/dev/pts/0` opens.

The defect was rechecked here with the Codex image
`localhost/codex-cli:adopt-ref-11` and this launcher's `/dev` arguments:
"out of pty devices".

Qualification digests the launcher (`agent/profile.json` `wrapper`, part of
`code_files`).

The existing tests are:

- `tests/test_wrapper.py`:
  - the tmpfs list (around line 659) includes the `/dev` entry;
  - a count of 5 `--tmpfs` arguments (around line 866);
  - `DEVICE_MOUNTS` with `assert_device_and_secret_mounts` (around
    line 874).
- `tests/test_runtime.py`: the `shell()` helper runs the wrapper through a
  PTY (`terminal_shell`).

## Goals / Non-Goals

**Goals:**
- The same launcher, test and documentation behavior as the Claude
  reference, with the Codex temporary mounts unchanged.

**Non-Goals:**
- Shared code. The proxy keeps `--read-only-tmpfs=false`.
- Any change to the Codex tmpfs sizes or exec policy.

## Decisions

1. **Leave `/dev` to the engine**, as in the reference. Remove the `/dev`
   tmpfs and the `devpts`, keep `--read-only`, the `/dev/shm` mask and the
   `/run/secrets` mask. Use the reference comment wording, so that the
   launchers read the same. The alternatives (`ptmxmode`, `--device
   /dev/ptmx`, keeping no PTYs) were rejected in the reference for the
   reasons above.

2. **Spec.** Remove "Terminal-compatible device mounts" and add "Engine-provided
   device mounts allow pseudo-terminals", with the reference's scenarios plus
   the existing Codex scenario "Temporary mounts keep their Codex policy".
   OpenSpec cannot drop the "Executables cannot run from /dev" scenario from
   a modified requirement.

3. **Tests.**
   - `tests/test_wrapper.py`:
     - `DEVICE_MOUNTS` keeps only the `/dev/shm` and `/run/secrets` masks;
     - `assert_device_and_secret_mounts` also asserts that there is no
       `--tmpfs` for `/dev` and no `devpts` or `/dev` `--mount`;
     - the tmpfs list loses its `/dev` entry, and the tmpfs count becomes 4.
   - `tests/test_runtime.py`: add `test_pseudo_terminals_and_device_masks`,
     the reference probe run through `self.shell()`: `pty.openpty()`, a
     slave under `/dev/pts/`, and empty, unwritable `/dev/shm` and
     `/run/secrets`. It must fail on the current launcher and pass after the
     fix.

4. **Documentation.**
   - `README.md` (around line 653): the engine provides `/dev` and a
     `devpts` that allows pseudo-terminals, and an explicit `devpts` would
     get `ptmxmode=000`. On Podman 5, `/dev` is writable but needs
     capabilities to create devices; on Podman 4.9 it is read-only. The
     `/dev/shm` sentence stays.
   - `AGENTS.md` (around line 216): do not mount `/dev` or `devpts`
     explicitly, only the `/dev/shm` mask.
   - `docs/validation.md`: a record with the results and pending operator
     setups.

## Risks / Trade-offs

- [On Podman 5, `/dev` is writable and executable] → `nosuid` remains,
  devices need the dropped capabilities, and `/dev` is ephemeral. Codex's
  `/tmp` and `/var/tmp` are already executable, so the exposure does not
  grow.
- [`bwrap --dev /dev` in the Codex sandbox test] → bwrap mounts its own
  `devpts`, so it does not depend on the outer layout. Covered by
  `test_tools_and_codex_sandbox_without_capabilities` in the default
  runtime run.
- [The Rocky host cannot be reproduced here] → The operator reruns setup and
  a session there. The reference already passed on that host.

## Migration Plan

1. Merge on `main` after validation. The operator pushes it.
2. On each host, run `--container-setup` (the launcher digest changed).
3. Rollback: revert the merge and rerun setup.
