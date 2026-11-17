# Proposal

## Why

`sandbox-ref-22` added the shared Bash launcher core (`launcher/core.sh`), and `sandbox-ref-23` removed the Claude identifiers from its shared tests. `sandbox-ref-24` reports an inaccessible state directory with the wrapper's diagnostic, a lost behavior this adoption found (task 2.3). Claude already runs on the core. Codex still uses its own 1044-line `codex-container.sh`, a family-B launcher whose signal model, temporary storage and environment differ from the core's. Until Codex adopts the tag, its launcher keeps diverging from the reference, and the 72 Codex cases marked "to verify at adoption" in the reference test map stay open.

## What Changes

- Adopt `sandbox-ref-24` from `sandbox-ref-21` with `tools/propagate.py`, in two steps: `sandbox-ref-21` to `sandbox-ref-23`, then `sandbox-ref-23` to `sandbox-ref-24` after the reference fix. This copies `launcher/core.sh`, `tests/test_launcher.py`, `tests/fake_podman.py` and the launcher fixtures, plus the changed shared files (`network/*`, `setup/*`, `tests/test_alignment.py`, `tests/test_setup.py`, ...). It also moves the manifest and the current-state references to the tag. `tests/test_reference_copy.py` treats `launcher/` as a closed directory (lesson from the Claude adoption).
- Replace `codex-container.sh` with the thin entry script. The entry script is identical to the reference's apart from its name.
- Add `agent/launcher.sh`, which holds the Codex profile data and three hooks:
  - `agent_command_args` adds, in offline and provider sessions only, the protected `--no-daemon -c sandbox_mode="danger-full-access"`. Provider sessions also get the ten protected `-c` overrides that disable optional traffic.
  - `agent_approval_bypass` turns `CODEX_YOLO` into `--yolo`.
  - `agent_help` documents `CODEX_YOLO`.

  The agent part declares a credential entry for every policy profile of the default policy: `openai-api` and `openai-api-docs` get `OPENAI_API_KEY`, `openai-account` gets none.
- Before the old launcher is deleted, run Codex's current `tests/test_wrapper.py` against the new core. For each failing case, decide one of three outcomes:
  - it is a recorded visible change;
  - it is a lost behavior, which is fixed in the reference with a shared case, and the adoption then moves to the new tag;
  - it is Codex-only behavior, which stays in the reduced `tests/test_wrapper.py`.
- Reduce `tests/test_wrapper.py` to Codex's hook and data tests. Update the wrapper-owned runtime tests:
  - `tests/run-runtime.sh`: `--wrapper` also runs `test_launcher.py`;
  - temporary storage in `tests/test_runtime.py`;
  - the installation files in `tests/test_network_runtime.py`, `tests/test_setup_runtime.py` and `tests/test_setup_wrapper.py`.
- Visible changes for Codex users, all from the contract's "Visible changes" list. Breaking changes are allowed: the project has no release.
  - **BREAKING**: a missing `CODEX_CONTAINER_NETWORK` selects `provider`. Without the provider settings, the launch still stops with setup guidance.
  - **BREAKING**: `--container-build` without Codex arguments validates every setting, builds and exits. A stale image is refused until it is rebuilt.
  - **BREAKING**: shell mode passes its arguments to Bash.
  - **BREAKING**: `/tmp`, the ephemeral home and `/run` are `noexec` and `/var/tmp` is `noexec`. Codex does not declare executable temporary storage unless the adoption shows that it needs it (contract U7). The ephemeral home becomes a 512 MiB tmpfs.
  - **BREAKING**: `CODEX_HOME` and `CODEX_CONTAINER_STATE_DIR` must be absolute paths without colon, CR or LF, checked before the engine. A relative `CODEX_HOME` is refused.
  - **BREAKING**: signal handling follows the shared core (U9). A TERM, INT or HUP starts shutdown at once, also during creation, within one 20-second deadline. The family-B "first signal recorded, exit at the next checkpoint" model and its separate 5-second creation phases end.
  - New: `CODEX_CONTAINER_ENV_VARS` and `CODEX_CONTAINER_READONLY_STATE`.
  - Every session gets `TERM`, `COLORTERM`, `LANG` and `LC_ALL` when set, `USER`, `EDITOR=nano`, `VISUAL=nano` and `CONTAINER_NAME`. Unrestricted sessions also forward the proxy variables and run with `--init`. Delegated sessions get private tmpfs storage for nested Podman.
  - Engine queries are bounded by timeouts, and builds use `--format docker`.
  - Provider help lists the hosts of the two base profiles from the default policy. The `openai-api-docs` hosts stay documented in the README and the network contract.
- Update the README, `docs/setup.md`, `docs/network-contract.md` and `docs/validation.md`. The help text now comes from the core.

## Capabilities

### New Capabilities

- `shared-launcher`: Codex's launcher is the shared core with a thin entry script and the Codex agent part. The agent part stays consistent with the profile, and its hooks and data are tested by Codex's own tests.

### Modified Capabilities

- `container-session`:
  - provider default with setup guidance;
  - qualification checks with the resolved mode;
  - shared signal and creation shutdown (U9);
  - YOLO through the agent hook;
  - session environment, shell arguments, `--init` and `CONTAINER_NAME`;
  - extra variables by name;
  - bounded engine queries;
  - first-user guidance without the migration history.
- `container-isolation`:
  - the new temporary storage options and the tmpfs home;
  - state paths checked before the engine;
  - private, contained isolated-home children;
  - read-only state.
- `container-podman-access`: private nested-Podman tmpfs mounts in delegated sessions.
- `container-setup`:
  - runtime builds always go through the wrapper's build-only operation;
  - the installation contains the core and the agent part.
- `network-egress`:
  - provider is the default mode;
  - credential and extra-variable rules per policy profile;
  - qualification and preflight bind the core and the agent part;
  - profile fields;
  - the disclosure is printed from the policy.
- `runtime-image`:
  - build-only operation;
  - stale-image refusal;
  - build format;
  - image-name checks.

## Impact

- **Code:**
  - `codex-container.sh` shrinks from 1044 lines to the thin entry script;
  - new `agent/launcher.sh`;
  - shared files copied from the tag;
  - wrapper-owned tests and docs updated.
- **Profile:** `agent/profile.json` needs a new field only if the adoption shows that Codex needs executable temporary storage (`native.exec_tmp`). It already uses the default `native.exec=/usr/local/bin/codex`.
- **Qualification:** the qualification identity now includes the core and the agent part. Every installation needs `--container-setup` again, and the operator runs it on the three reference hosts.
- **Other wrappers:**
  - Antigravity and Pi adopt `sandbox-ref-24` in their own changes, and OpenCode after them.
  - If this adoption finds a lost behavior, a reference fix and a new tag come first.
