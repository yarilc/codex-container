# Design

## Context

Codex adopted `sandbox-ref-28` on 2026-11-22. That adoption was validated on
WSL (ABI 3), with every runner mode, and on the Windows Podman machine. The
range to `sandbox-ref-36` holds these tags:

| Tag | Reference change or fix |
| --- | --- |
| `ref-29` | `replace-podman-delegation-with-session-engine` and `simplify-toolchain-provisioning` |
| `ref-30` | the engine's chroot capability, for builds and new layers |
| `ref-31` | the engine base pinned to an `-immutable` tag |
| `ref-32` | engine labels read on every Podman version |
| `ref-33` | a restricted session's interfaces checked in its network namespace |
| `ref-34` | `set-process-limits-inside-containers` |
| `ref-35` | `fix-runtime-test-portability` |
| `ref-36` | `support-nested-systemd-containers` and `declare-engine-image-capabilities` |

Claude crossed the same range in three adoptions (`ref-34`, `ref-35`,
`ref-36`). Its changes to its own tests and documentation are the worked
example for Codex.

**Dry run, 2026-11-26.** `python3 -I tools/propagate.py ../codex-container
sandbox-ref-28 sandbox-ref-36` gave the proposal's file plan. It also printed:
- **Runner entries:** `--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--wrapper`, the default runtime mode,
  `--network-feasibility`, `--guard` and `--network`, all in full.
- **Preparation:** the engine image, with `localhost/codex-cli:latest` and
  `localhost/codex-guard-toolchain:development` as the images needed.
- **Manual step:** the Windows validation script.
- **19 review lines.** Two are hand-written lists made stale by added files:
  - `AGENTS.md:39`, the list of shared tests;
  - `tests/test_network_runtime.py:58-59`, the files the network fixture copies
    into its installation, without `setup/engine.py` and `launcher/engine/`.

  The other 17 only mention a shared file.
- **Nine reference changes.**
  - `add-read-only-dependency-mirror` is not in the tag: it held only a
    proposal there.
  - `keep-parity-history-in-propagation` touches only reference files.
  - `fix-windows-agent-guidance` is already in Codex's `container-setup`.
  - The other six carry the spec deltas of this change.

**What Codex adds to the shared code:**
- **Test cases that still delegate:**
  - `tests/test_wrapper.py`: the YOLO × delegation grids;
  - `tests/test_runtime.py`: the child bind case, the containerized caller
    with a remapped socket, the delegated variants of the budget and the
    tools cases;
  - `tests/test_network_runtime.py`: the restricted refusal grids;
  - `tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`: the setup
    question.
- **The `ref-35` assumptions,** which Claude fixed in its own copies:
  - the budget test always reads `cpu.max`;
  - the terminal case always runs;
  - the setup test answers the CA prompt with the Debian bundle path;
  - the setup test removes only the recorded runtime image.
- **The runner `tests/run-runtime.sh`:**
  - it selects its socket through `CODEX_CONTAINER_PODMAN_SOCKET`;
  - its `--shared` list names 13 of the tag's 17 shared test modules. It lacks
    `test_engine` (new), `test_toolchains`, `test_windows_bootstrap` and
    `test_windows_enter`. `test_setup` has its own mode.
- **The specs.** Codex's specs are worded for Codex and differ from Claude's
  in `container-isolation`, `container-podman-access`, `network-egress` and
  `workspace-mounts`. Codex has `container-session` where the reference has
  `container-launcher`. Codex's `container-podman-access` also holds the
  launch-engine requirements that the reference keeps in `container-launcher`.

The runtime image's build context is `Containerfile`, `.containerignore`,
`network/relay.py` and `network/mux.py`. None of them changes in the range.

## Goals / Non-Goals

**Goals:**
- Codex runs on the `sandbox-ref-36` shared files. Its tests, documentation
  and specs no longer describe delegation.
- The operator validates the adoption with one runner line on WSL. The runner
  writes full logs to one archive. Two further steps follow: the Windows
  script and one real session.

**Non-Goals:**
- No porting of the reference's systemd and cgroup delegation runtime cases,
  its systemd sample recipe or the recipe's pin check, as for Claude. The
  reference's `ref-36` runs on both hosts are their evidence.
- No runner support for running from inside a Codex session, and no copy of a
  checkout that others can write. The operator's clones are native. A later
  change can take both from the reference's runner.
- No Rocky run. One host is the rule (`docs/propagation.md`, step 3), and
  Codex was validated on WSL.
- No fix of `tools/propagate.py` here. It belongs to `sandbox-container` (see
  Risks).

## Decisions

1. **Copy with the tool, and prove the copy by hash.** `tools/propagate.py`
   applies the dry run's plan in one step from `ref-28`. The intermediate tags
   are not adopted one by one, because each would need its own validation.
   `tests/test_reference_copy.py` proves byte identity with `ce2c9d2`.

2. **Codex's tests take Claude's rewrite, applied to Codex's own cases.**
   Claude's diff from its `ref-28` state to `ref-36` is the model. Codex's
   files keep their own cases: Codex's sandbox, the Responses API fixture and
   the protected `-c` arguments.
   - **`tests/test_wrapper.py`:**
     - the YOLO grid runs YOLO × shell mode and checks that no
       `podman.sock` is mounted;
     - the exact opt-in grid becomes a refusal grid: only `1` stops the
       launch, with "host Podman delegation was removed", and other values
       are ignored;
     - the help case checks the migration line;
     - the `AF_UNIX` socket fixture goes.
   - **`tests/test_runtime.py`:**
     - **Delegation:** the image environment case checks the refusal. The
       budget, tools and help cases drop their delegated variants.
       `test_child_container_host_bind` goes; the engine cases cover nested
       binds.
     - **Containerized caller:** `test_containerized_caller_with_remapped_socket`
       keeps its launch context, a wrapper inside a container on a remapped
       launch socket. It no longer delegates, and it checks that the session
       has no socket.
     - **Engine cases:** the reference's `SessionEngineTests` (four cases) and
       `test_process_rlimit_counts_per_container` are added, with
       `localhost/codex-cli-engine:latest`.
   - **`tests/test_network_runtime.py`:**
     - **Installation:** the installation copies `setup/engine.py` and
       `*engine.INPUTS`, as the reference does, and the engine's seccomp
       profile when the engine image exists.
     - **Refusal cases:** they become the leftover opt-in cases.
     - **Engine cases:** the reference's engine cases are added, and so is the
       proxy case beside a crowded container.
     - **`ref-35` budget rule:** the budget test checks each budget as the
       engine enforces it, through `engine_budgets()`.
     - **`ref-35` terminal case:** it runs in its own subtest and skips with
       `terminal_skip_reason()`.
   - **`tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`:**
     - the delegation question and `podman: False` go;
     - the setup test copies the runner's CA bundle into the test state;
     - it removes the engine, guard and proxy tags of its releases;
     - its proxy shim routes only ID lookups.
   - **Rejected: copying Claude's test files with names replaced.** They lack
     Codex's own cases, and Codex's structure differs, for example in its
     restricted test class.

3. **Widen the launch windows of the interrupted creation case, and keep the
   shutdown bound.**
   - **What happened to Claude:** in its full `--network` run on WSL at
     `ref-35`, every subtest of
     `test_interrupted_and_failed_creation_recovers_both_roles` failed. The
     launches missed the 15-second window to reach `create` and the
     25-second window to exit, and the late launches left a session
     directory and two proxies behind. Alone, the test passed.
   - **Codex:** it has the same test and runs the full `--network`.
   - **Change:**
     - reaching the intercepted `create` gets 60 seconds;
     - the `before` and `after` phases get 90 seconds to exit;
     - after the signal, the interrupt phase still has 25 seconds, which keeps
       the 20-second shutdown deadline of "Bound interrupted container
       creation" under test;
     - a launch that times out is killed before the subtest fails, so later
       subtests start clean.

4. **The runner keeps its structure.** `tests/run-runtime.sh`:
   - **Socket:** it drops `CODEX_CONTAINER_PODMAN_SOCKET`. The socket comes
     from a Unix `CONTAINER_HOST`, else from the runtime directory, as
     before.
   - **`--shared` list:** it gains `test_engine`, `test_toolchains`,
     `test_windows_bootstrap` and `test_windows_enter`. None of them writes
     into the checkout, which this mode mounts read-only.
   - **Why the list matters:** the checklist runs `--shared` in place of the
     host unit tests, so without these modules the run would pass without
     running the changed engine, toolchain and bootstrap tests.
   - **Rejected: making `--shared` a discovery.** `--shared` is the
     documented "copied shared suites" mode, and a discovery would also run
     Codex's own suites with the read-only checkout.

5. **Specs: the reference's deltas, adapted to Codex's text.**
   - **Same text as the reference:** where Codex's requirement equals the
     reference's text at `ref-28`, the delta takes the reference's current
     text, with `CODEX_CONTAINER_` names.
   - **Codex's own wording:** the delta applies the same edit to Codex's
     text.
   - **Removed scenarios:** `openspec` rejects a MODIFIED block that drops a
     scenario. A requirement that loses its delegated scenario is therefore
     removed and restated under a new name: "Every session drops
     capabilities and privilege gains" becomes "Sessions drop all
     capabilities and privilege gains". Elsewhere the scenario keeps its name
     with new content, as the reference does.
   - **Retired capability:** `container-podman-access` is retired
     (`retire_capabilities: true`).
   - **Moved requirements:** its four launch-engine requirements move to
     `container-session` without their delegated parts. `container-session`
     also takes the reference's "Leftover delegation opt-in is refused".
   - **New capability:** `session-container-engine` is the reference's main
     spec, with `CODEX_CONTAINER_TOOLCHAINS`.
   - **Known warnings:** the strict check of the change warns that "Fixed
     engine hardening exceptions" is over 500 characters, as in the reference
     and Claude. After the sync, seven more requirements of Codex's main specs
     are over 500 characters, because they take the reference's text, which is
     over 500 characters there too (task 2.7).
   - **Rejected:** adding the reference's `container-launcher` beside
     `container-session`. It would duplicate a dozen Codex requirements under
     other names.

6. **Documentation: the reference's text, with Codex's names.**
   - **`README.md`:**
     - **Launch service:** "Optional host Podman API access" becomes "Enable
       the launch service", as in Claude: restricted launches still need the
       service. The delegation socket selection and verification go.
     - **Removed:** the delegation examples, the YOLO × Podman table and the
       delegation column of the network table.
     - **"Container tests" (new section):** the core's refusal names it
       (`README: Container tests`). Its source is Claude's section, which has
       the reference's text.
     - **Toolchain section:** catalog names, image entries and Windows paths.
     - **Engine items:** the budgets, the hardening exceptions with the
       startup step and the label, "Systemd containers and nested limits" and
       the read-only `/sys`.
     - **Security statements:** they drop the socket.
     - **Runner:** the runner section drops the delegation socket.
   - **`AGENTS.md`:**
     - the delegation rules become the engine rules;
     - the shared test list gains the tag's modules;
     - it takes the reference's terminal check paragraph.
   - **`docs/setup.md`:** no delegation question, schema 3 preferences and the
     engine image.

7. **Validation: one runner line on WSL, then two operator steps.**
   - **Runner:** from `sandbox-container` on WSL, beside the native clone on
     the branch, the operator runs `bash tools/adoption-run.sh
     ../codex-container sandbox-ref-28 sandbox-ref-36`. The runner checks the
     images and the free space, rebuilds `localhost/codex-cli-engine:latest`,
     runs every entry to its own log and packs the archive.
   - **Sample image:** the pinned alpine sample image must be in the engine
     first. Otherwise `SessionEngineTests` skips with "prepare …", which the
     runner marks `NOT PREPARED` and fails.
   - **Windows:** the operator runs `.\tools\windows-validate.ps1` with the
     Windows checkout on the branch, on Windows PowerShell 5.1. It covers the
     changed bootstrap and a session with library images in the Podman
     machine.
   - **Real use:** on WSL, the operator reruns `codex-container
     --container-setup` from the branch and opens one session with library
     images.
   - **Cost:** the tag touches every component, so this is the full matrix
     on one host, about an hour of suites. It replaces the two-host matrix of
     earlier adoptions and three separate adoptions.

## Risks / Trade-offs

- **[Risk] The full `--network` meets a host slowdown, as Claude's did.** →
  Decision 3 widens the launch windows. A failure the test does not show alone
  is rerun with `--only network` into a new archive, and both archives are
  recorded.
- **[Risk] A shared defect appears only with Codex.** → The change pauses: fix
  in `sandbox-container`, tag, and adopt that tag on a fresh branch
  (`docs/propagation.md`, step 3).
- **[Risk] A Codex wording keeps a delegation statement after the spec
  sync.** → Task 2.7 scans the main specs that the archive would produce, and
  the README and AGENTS, for delegation wording. It allows only the
  migration, the refusal and cgroup controller delegation.
- **[Trade-off] The reference tool still runs `--shared` as if it were the
  unit discovery.** Antigravity, OpenCode and Pi have the same short list.
  → Here, decision 4 completes Codex's list. A follow-up in `sandbox-container`
  should make the checklist name the changed shared modules that the runner's
  list lacks, before those three adopt.
- **[Trade-off] The systemd cases run only in the reference.** → As for
  Claude: Codex adds only names to the shared engine.
  `SessionEngineTests`, the qualification probe and the Windows script
  exercise Codex's own engine path.

## Migration Plan

1. Merge into `main` after the record.
2. Operators:
   - rerun `codex-container --container-setup`. It builds the engine image,
     migrates saved delegation and requalifies restricted installations;
   - add the images their tests need with `--container-toolchain add`;
   - unset `CODEX_CONTAINER_PODMAN`.
3. **Rollback:** point `current` back to the previous release, as
   `docs/setup.md` describes. That release keeps its schema 2 preferences.
   Setup from the old `main` refuses the schema 3 file of the new release.
