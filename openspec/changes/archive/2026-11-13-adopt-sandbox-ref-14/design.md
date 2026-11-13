# Design

## Context

Codex `main` (`3a4d5ab`, even with `origin/main`) pins `sandbox-ref-12`. The
dry run of `tools/propagate.py ../codex-container sandbox-ref-12
sandbox-ref-14` (expected, as for OpenCode) reports:

- six modified files (including `tests/test_qualification.py`) and two
  added files, nothing removed or "not adopted";
- the manifest moving to commit `f06c885`;
- four documents (`README.md`, `AGENTS.md`, `docs/setup.md`,
  `docs/network-contract.md` with seven references);
- the runner modes `--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--guard`, `--network` and `--wrapper`.

A first apply adopted `sandbox-ref-13` on branch `adopt-sandbox-ref-13`. It
holds the uncommitted launcher, test and documentation port (tasks 2.1–4.1).
It also showed that, with that tag, `--qualification` fails (shared fixture,
fixed in `sandbox-ref-14`). `--wrapper` fails too, because the Codex runner
runs the wrapper suite with the image's world-writable `/tmp`.

The reference launcher change is in claude-container commit `e45957f`
(`claude-container.sh`, design decision 5 of `add-toolchain-library`).
Relevant Codex differences:

- **State:** `CODEX_CONTAINER_STATE_DIR` (isolated, mounted at
  `/codex-home`) or `CODEX_HOME` (default `~/.codex`, mounted at
  `/codex-home/.codex` over a writable tmpfs `/codex-home`). The profile has
  no `shared_dirs`. The variable names are `state_dir` and `CODEX_DIR`.
- **Arguments:** the run arguments are `podman_args`, not
  `container_args`; the runtime image identity is captured with
  `capture_engine_info image inspect`.
- **Temporary storage:** `/tmp` and `/var/tmp` are `exec` in Codex, unlike
  the reference, so tools that execute from their temporary directory work
  without `GOTMPDIR` under the workspace.
- **Agent instructions:** Codex reads `AGENTS.md` (project or
  `$CODEX_HOME/AGENTS.md`), not `CLAUDE.md`.
- **Protected variables:** the shared module protects `CODEX_HOME`,
  `CODEX_YOLO`, `OPENAI_API_KEY` and every `CODEX_CONTAINER_*` name from the
  profile.
- **Base:** the Codex `Containerfile` has one digest-pinned `FROM`, the same
  `node:22-bookworm-slim@sha256:4b15…` as the reference, so toolchains
  verified by another wrapper keep their default environment here.

## Goals / Non-Goals

**Goals:**
- Codex adopts `sandbox-ref-14` byte for byte, and its parity table matches
  claude-container's.
- Every runner mode the tool lists passes, `--wrapper` included.
- Codex sessions mount the shared library and get the default environment
  exactly as reference sessions do.

**Non-Goals:**
- Any change to shared files, the guard, the proxy or the policy.
- Copying the six example recipes or their opt-in network test.
- Making `/tmp` `noexec` to match the reference.

## Decisions

1. **Adopt with the documented procedure, regenerating the branch.**
   - The tool refuses a dirty tree and a manifest that names another tag, so
     the `sandbox-ref-13` branch cannot be moved forward in place.
   - The wrapper port is saved first as a patch, limited to the wrapper-owned
     files (`codex-container.sh`, `tests/test_wrapper.py`,
     `tests/test_runtime.py`, `tests/test_network_runtime.py`, `README.md`,
     `AGENTS.md`, `docs/setup.md`). The patch is taken against a
     reproduction of the tool's own `sandbox-ref-13` output, so it carries
     no tag references.
   - Then the branch `adopt-sandbox-ref-13` is discarded (the change
     directory is stashed), `--apply` runs `sandbox-ref-12` →
     `sandbox-ref-14` on `adopt-sandbox-ref-14`, and the patch is applied
     with `git apply --3way`.
   - The wrapper port is committed on the same branch and merged once with
     `--no-ff`. One branch keeps the shared code and its launcher
     integration together, so `main` never has a qualified module that the
     launcher does not use, and never carries `sandbox-ref-13`.
2. **Port the reference launcher block literally, renaming only.** The
   dispatch, `toolchains_enabled`, the `launch-env` call and parser, the image
   `PATH` inspection and the mount are taken from `e45957f`, with
   `CLAUDE_CONTAINER_*` → `CODEX_CONTAINER_*`, `container_args` →
   `podman_args`, and the `--avoid` list built from `state_dir` or
   `CODEX_DIR`. The image `PATH` is read with `podman image inspect` after the
   runtime image is resolved, as in the reference. Alternative: a Codex
   specific variant. Rejected: identical behavior across wrappers is the point
   of the shared library.
3. **Tests mirror the reference cases.** `tests/test_wrapper.py` gains the
   dispatch, private creation, unsafe library, disable, appended environment,
   restricted mount-target and unsafe-workspace cases. The fake engine answers
   `.Config.Env` inspections, and the control log records the helper
   arguments when the existing fake does not already. `tests/test_runtime.py`
   gains the archive and image sources, failing check, read-only mount,
   `node`/`python3` not shadowed, and the disabled mount; the network runtime
   suite gains the live add during an offline session. Each adaptation to
   existing Codex fixtures (for example the volume count or the files copied
   into a fake installation) is made where a new case requires it.
4. **Documentation links the example recipes.** The README section states the
   same rules as the reference, adapted to Codex, and links
   claude-container's `docs/toolchains/` and README table for the verified
   examples. The recipes do not depend on the agent: they were verified on
   the same base image.

5. **Private temporary storage for the test runner**, as in the reference
   since `sandbox-ref-14`.
   - `tests/run-runtime.sh` mounts a private executable tmpfs at
     `/sandbox-test-tmp` (`0700`, `U=true`, 1 GiB) and sets
     `SANDBOX_TEST_TMPDIR` to it.
   - `tests/test_wrapper.py` creates its temporary directory under
     `SANDBOX_TEST_TMPDIR` when it is set. Outside the runner, the variable
     is unset and the default temporary directory is used, as before.
   - The shared suites that already read `SANDBOX_TEST_TMPDIR`
     (qualification, session, setup, toolchains) then run on it in every
     mode, so every mode is rerun.

## Risks / Trade-offs

- [A Codex fixture assumes two volumes or a fixed file set] → The wrapper
  suite catches it; the fixture is updated in the same branch.
- [Unsafe-workspace launches from the home directory now stop] → As in the
  reference: the home contains the default library. The README documents
  `CODEX_CONTAINER_TOOLCHAINS_DIR` and `CODEX_CONTAINER_TOOLCHAINS=0`.
- [Hosts without host Python 3] → Restricted launches already require it.
  For unrestricted launches the error names `CODEX_CONTAINER_TOOLCHAINS=0`.
- [The patch does not apply cleanly after the new `--apply`] → `--3way`
  resolves it against the shared base. Any remaining conflict is limited to
  wrapper-owned files and is resolved by hand, then reviewed with
  `git diff`.
- [Qualification reports become stale] → The operator reruns
  `--container-setup` on the three hosts.

## Migration Plan

1. Merge `adopt-sandbox-ref-14` with `--no-ff`. The operator pushes it.
2. Rerun `--container-setup` on this host, the Rocky Linux 9 lab host and the
   newer WSL host. With the Temurin 21 toolchain already in the library,
   check `java -version` in a Codex session and run
   `codex-container --container-toolchain verify java21`.
3. Record the results, then archive with the spec sync.
4. Rollback before the push: reset `main` to `3a4d5ab`. The library on disk
   is ignored by the older launcher.
