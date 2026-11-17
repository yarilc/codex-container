# Design

## Context

Codex is on `sandbox-ref-21`. Its launcher, `codex-container.sh` (1044 lines), is a family-B launcher. The launcher contract (`docs/launcher-contract.md` in `sandbox-container`) lists where it differs from the core:

- **Signals (U9):** the first signal is recorded and the launcher exits at the next checkpoint. Creation has its own five-second phases, and each shutdown engine call has a fixed 5 s timeout.
- **Temporary storage (U7, L7):**
  - `/tmp` and `/var/tmp` are `exec`;
  - `/run` is executable;
  - the shared-state home is an unbounded executable tmpfs.
- **Environment (phase 5):** no `TERM`, `EDITOR`, `VISUAL` or `USER`.
- **Configuration override:** `CODEX_HOME` may be relative today.
- **Codex-only behavior:**
  - the protected `--no-daemon -c sandbox_mode="danger-full-access"` in restricted sessions;
  - ten provider-only `-c` overrides;
  - `CODEX_YOLO` → `--yolo`;
  - `OPENAI_API_KEY` for `openai-api` and `openai-api-docs`.

The test map (`docs/launcher-test-map.md`) sorts Codex's 85 `tests/test_wrapper.py` cases as follows:

| Kind | Cases | Notes |
| --- | --- | --- |
| Shared | 64 | |
| Rewritten into shared cases | 8 | |
| Duplicates of the reference | 10 | |
| Hooks | 3 | `test_yolo_case_insensitive_and_delegation_independent`, `test_permissions_independent_and_exact_opt_in`, `test_unrestricted_codex_keeps_its_own_sandbox` |

72 cases are marked "to verify at adoption". The rewritten ones depend on U1, U3, U7, U9 and U10:

| Rewritten case | Decision |
| --- | --- |
| `test_missing_mode_stops_before_engine_state_and_other_checks` | U1 |
| `test_explicit_build_and_image_override` | U3 |
| `test_tmpfs_capacities_and_options` | U7 |
| `test_signals_during_creation` | U9 |
| `test_permanently_stalled_creation_signal_matrix` | U9 |
| `test_stubborn_application_and_stalled_cleanup_are_bounded` | U9 |
| `test_provider_order_protected_overrides_and_api_key` | U10; the protected overrides stay a hook test |
| `test_api_key_follows_the_policy_authentication_method` | U10 |

The `tools/propagate.py` dry run from `sandbox-ref-21` straight to `sandbox-ref-23` (2026-11-17) gives this plan:

- **Copy (new files):**
  - `launcher/core.sh`;
  - `tests/test_launcher.py`;
  - `tests/fake_podman.py`;
  - `tests/fixtures/agent/launcher.sh`;
  - `tests/fixtures/shell-agent/launcher.sh`.
- **Update (changed files):**
  - `network/README.md`, `network/agent_profile.py`, `network/control.py`, `network/qualification_records.py`, `network/qualify.py`;
  - `setup/common.py`, `setup/launch.py`, `setup/setup.py`;
  - `tests/fixtures/agent/profile.json`, `tests/sandbox_profile.py`, `tests/test_agent_profile.py`, `tests/test_alignment.py`, `tests/test_network_policy.py`, `tests/test_qualification.py`, `tests/test_setup.py`.
- **Rewrite:** one reference each in `README.md`, `AGENTS.md` and `docs/setup.md`, and eight in `docs/network-contract.md`.
- **Move:** the manifest to `sandbox-ref-23` (`7d14706`).

Task 2.2 found one lost behavior: an inaccessible state directory stopped with a raw `cd: ...: Permission denied`. `sandbox-container` fixed it in `fix-inaccessible-state-diagnostic` and tagged `sandbox-ref-24` (`dd5d82e`). The second propagation, `sandbox-ref-23` to `sandbox-ref-24`, updates `launcher/core.sh` and `tests/test_launcher.py`, the five current-state references and the manifest.

The Claude adoption (`adopt-sandbox-ref-22`, archived 2026-11-17) found four things every adoption needs:
- `tests/test_reference_copy.py` must list `launcher` in `CLOSED_DIRECTORIES`;
- the old `tests/test_wrapper.py` runs against the core only with an adapted harness:
  - the fake engine reports the image's `build-inputs-hash` label;
  - the synthetic installation copies `launcher/` and `agent/launcher.sh`;
- the core prints no help for the approval bypass variable, so the agent part defines `agent_help`;
- U10 holds strictly: real network tests that relied on host keys set them inside the session.

## Goals / Non-Goals

**Goals:**
- Codex runs entirely on the shared core. Its own launcher code is the entry script and `agent/launcher.sh`.
- No Codex launcher behavior disappears without being either a recorded visible change or a shared test.

**Non-Goals:**
- Adopting the core in Antigravity, Pi or OpenCode.
- Changing Codex's image, CLI version, policy inventories or authentication methods.
- Changing reference files inside this repository. A defect found here is fixed in `sandbox-container` and arrives by a tag.

## Decisions

1. **Adopt with the tool, straight from `sandbox-ref-21` to `sandbox-ref-23`.** The dry run must list exactly the plan in "Context". `--apply` switches to the branch `adopt-sandbox-ref-23`. Then add `launcher` to `CLOSED_DIRECTORIES` in `tests/test_reference_copy.py`. That file is wrapper-owned, and the Claude adoption made the same fix. After a lost behavior is fixed in the reference, the tool runs again from the adopted tag to the new one; its changes are carried back onto `adopt-sandbox-ref-23`, and the parity rows it rewrites are restored by hand. Alternative rejected: going through `sandbox-ref-22` first. Its shared tests carry Claude identifiers and fail the alignment test.

2. **Entry script and agent part.**
   - `codex-container.sh` is the reference `sandbox-container.sh`, with only the wrapper name changed in its comment.
   - `agent/launcher.sh` declares:
     - the profile values;
     - `AGENT_EXEC=/usr/local/bin/codex` and `AGENT_EXEC_TMP=0`. These are the profile defaults, so `agent/profile.json` stays as it is unless decision 3 finds a need;
     - `AGENT_SHARED_DIRS=()`;
     - `AGENT_CREDENTIALS=(openai-account= openai-api=OPENAI_API_KEY openai-api-docs=OPENAI_API_KEY)`. The alignment test derives one entry per default-policy profile from its authentication method, so the extension keeps the key exactly as today;
     - `AGENT_POLICY_HOSTS` for the two methods' base profiles;
     - empty session, restricted, provider, unset and reserved arrays. Codex's optional-traffic controls are arguments, not variables.
   - The agent part defines three hooks:
     - **`agent_command_args`:**
       - `restricted=1` → `--no-daemon -c 'sandbox_mode="danger-full-access"'`;
       - provider mode additionally → the ten `-c` overrides, in today's order;
       - unrestricted → nothing.

       The core calls the hook only outside shell mode and the probe. It places `agent_mode_args` before the bypass and the user's arguments, which is today's order.
     - **`agent_approval_bypass`:** `agent_bypass_args=(--yolo)`.
     - **`agent_help`:** documents `CODEX_YOLO`.

   Alternative rejected: moving the `-c` overrides into `AGENT_PROVIDER_ENV`. Codex reads these settings from `config.toml` or `-c`, not from variables. Variables would let the writable `config.toml` win.

3. **Temporary storage stays `noexec` unless Codex shows a need (U7).**
   - **Default:** Codex declares no executable temporary storage. The contract allows the declaration "only if its adoption shows a need".
   - **The check:** task 4.1 runs the rebuilt image in shell sessions with shared, isolated and read-only state. It runs `codex --version`, `codex exec --help` and `codex login status`, and looks for executables that Codex writes under `/tmp` or the home outside `.codex`.
   - **No need found:** `/tmp` becomes `noexec` and the runtime test asserts it.
   - **Need found** (for example Codex's helper links failing on a `noexec` home): the work pauses. The user decides between `native.exec_tmp: true` and accepting the limit. The specs and this design are updated before going on.

   Authenticated Codex runs stay deferred to the operator's real-key checks.

4. **Old tests gate the deletion.**
   - **Setup:** before the old launcher is deleted, the current `tests/test_wrapper.py` (the `sandbox-ref-21` version) runs against the new entry script and core. Its fake engine and the 85 cases stay unchanged. Only the harness is adapted, as in the Claude adoption: the fake reports a matching `build-inputs-hash` label, and the synthetic installation copies `launcher/` and `agent/launcher.sh`.
   - **Outcomes:** every failing case is resolved in exactly one of three ways:
     - **(a) Visible change.** The failure matches a row of the contract's "Visible changes" list, so the case is dropped. This includes U9's signal model and U7's `noexec` storage.
     - **(b) Lost behavior.** The work stops. The behavior and a shared case go into `sandbox-container` through a reference change and a new tag, and this change then adopts that tag instead.
     - **(c) Codex-only behavior.** The case stays in the reduced `tests/test_wrapper.py`.
   - **Passing cases and the record:**
     - Every passing shared or duplicate case is dropped, because `tests/test_launcher.py` covers it.
     - The 72 "to verify at adoption" cases are resolved by name.
     - The result goes into `docs/validation.md` as a table: the case, its outcome, and the shared case or visible-change row it maps to.

   Alternative rejected: deleting the old tests and trusting the map. The map was built by reading tests, not by running them, and family B's signal and creation cases are where the core differs most.

5. **Reduced `tests/test_wrapper.py`.** It uses the shared `tests/fake_podman.py` and the real `agent/launcher.sh`. It covers:
   - **The three hook cases:**
     - YOLO values and delegation independence;
     - exact Podman opt-in with YOLO;
     - unrestricted Codex without overrides.
   - **The protected arguments:** order and content in offline, provider, unrestricted, shell and probe launches, with user arguments containing spaces.
   - **`OPENAI_API_KEY`:**
     - with each policy profile (`openai-api`, `openai-api-docs`, `openai-account`, an operator profile);
     - in offline and unrestricted mode;
     - with a `CODEX_CONTAINER_ENV_VARS` attempt under `openai-account`.
   - **The help:** the provider disclosure in `--container-help` and the `CODEX_YOLO` entry.
   - **Outcome (c):** every outcome (c) from decision 4.

   Real-image behavior stays in `tests/test_runtime.py`.

6. **Wrapper-owned runtime tests follow the reference diff.**
   - `tests/run-runtime.sh --wrapper` runs `test_launcher.py` and `test_wrapper.py`.
   - `tests/test_runtime.py` asserts the 512/512/32/512 MiB capacities and `noexec` on all four mounts, unless decision 3 changes that.
   - `tests/test_network_runtime.py` installs `agent/launcher.sh`, `launcher/core.sh` and `.containerignore`.
   - The `tests/test_setup_runtime.py` shim answers only the `{{.Id}}` inspection.
   - `tests/test_setup_wrapper.py` covers the provider default: a missing mode without settings still gets setup guidance, and an empty override selects provider.
   - Real network tests that need `OPENAI_API_KEY` under an operator profile set a synthetic key inside the session (U10).

7. **Documentation.**
   - **README.** It is rewritten where the launcher changed:
     - help and first steps, with no migration history;
     - network modes and the provider default;
     - temporary storage and home;
     - signals and the 20 s shutdown deadline;
     - `CODEX_CONTAINER_ENV_VARS` and `CODEX_CONTAINER_READONLY_STATE`;
     - credentials;
     - build-only and stale images;
     - the shared components section, which names the core.
   - **`docs/setup.md`.** It follows the provider default.
   - **Parity table in `docs/network-contract.md`.** It is fixed by hand after `--apply`:
     - the reference and Claude rows are copied from their repositories;
     - the Codex row says it adopted `sandbox-ref-24`, with its runtime results;
     - the Antigravity, OpenCode and Pi rows are copied from their repositories.

8. **Validation scope.** The launcher, installation manifest and qualification identity all change, so validation covers the full set:
   - **Unit tests:** the unit discovery in the disposable test container.
   - **Runtime runs:**
     - `--wrapper`, `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`;
     - the default runtime run (`test_runtime.py`) against an image rebuilt with the `build-inputs-hash` label.
   - **Other checks:**
     - `git diff --check`;
     - `tests/test_reference_copy.py` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.

## Risks / Trade-offs

- **[Decision 4 finds a lost behavior]** → Implementation pauses for a reference change and a new tag. The tasks name that branch point, so it is not absorbed into this change. The most likely areas are family-B creation-record checks and the unreapable-client report.
- **[Codex needs executable temporary storage]** → Decision 3 makes it a user decision with evidence, not a silent profile flag.
- **[U9 shortens how long an interrupted creation may run]** → Intended. Recovery by CID record and ownership label stays, and one deadline replaces the separate five-second phases.
- **[Images built before the adoption have no `build-inputs-hash` label and are refused as stale]** → Intended (U8). The test images and the operator's installations are rebuilt with `--container-build` or `--container-setup`.
- **[Installed qualification reports no longer match, because the code identity now includes the core and the agent part]** → The operator runs `--container-setup` on the three reference hosts after the merge.
- **[Help text moves to the core and can drift from the README]** → The README quotes no help text. It describes behavior and points to `--container-help`.

## Migration Plan

1. Commit this change directory on `main`, then dry-run and apply the propagation (branch `adopt-sandbox-ref-23`).
2. Write the entry script and the agent part. Run the old tests (decision 4) and resolve every failure before touching `tests/test_wrapper.py`.
3. Reduce the wrapper tests, update the runtime tests and the documentation, run the temporary-storage check (decision 3), validate, and merge into `main`.
4. The operator pushes, then runs `--container-setup` on the three hosts. The change is archived with spec sync.

Rollback: before the merge, delete the branch. After the merge, revert the merge commit. The installed release stays the previous one until setup runs.
