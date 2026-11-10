# Proposal

## Why

`add-network-egress` gave Codex restricted modes, but preparing them is still a manual operator procedure. A missing mode only names `CODEX_CONTAINER_NETWORK`, and `offline` and `provider` sessions cannot run shell commands unless the user remembers `--sandbox danger-full-access`, because Codex's own sandbox cannot run under the guard. This second Wave 3 change completes the port of `claude-container` `sandbox-ref-2`: guided setup with a managed launcher, the unchanged alignment test, and a restricted-mode default that keeps Codex usable.

## What Changes

- Copy the rest of `setup/` unchanged from `sandbox-ref-2`: `common.py`, `setup.py`, `launch.py` and `smoke.py`. Also copy the shared tests `tests/test_setup.py` and `tests/test_alignment.py`.
- Add `--container-setup`, used alone in an interactive terminal. It runs the shared setup. Setup:
  - asks for the mode, authentication method, state, endpoint, delegation, CA trust, YOLO, budgets and lifetime;
  - discloses the residual exfiltration risk of provider mode and requires its acknowledgement;
  - prepares the images and the guard under maintenance consent;
  - installs a protected release with a managed launcher at `~/.local/bin/codex-container`;
  - runs qualification and a credential-free smoke check;
  - offers ChatGPT device-code login (`codex login --device-auth`) or names `OPENAI_API_KEY`.
- **BREAKING (message only)**: an ordinary launch with an unset or empty `CODEX_CONTAINER_NETWORK` now stops with `setup required:` guidance pointing to `--container-setup`, instead of only naming the variable. Explicit operator modes keep working unchanged.
- **BREAKING (restricted modes)**: in `offline` and `provider`, the wrapper adds a protected `-c sandbox_mode="danger-full-access"` before the user's arguments, like the optional-traffic overrides. Codex's own sandbox cannot run under the guard, so it is disabled there and the guard stays the enforced boundary. `unrestricted` keeps Codex's sandbox. An operator `--sandbox` or `-c sandbox_mode` given after it still wins, as an explicit choice.
- The wrapper passes the application's stderr through the shared `setup/diagnostics.py` filter, as the Claude wrapper does. The filter reclassifies only the known Podman 4.3 restart line.
- Replace the temporary per-agent alignment check with the unchanged `tests/test_alignment.py`. Keep `tests/test_reference_copy.py` as the byte-identity check, extended to the new shared files.
- Add the per-agent `tests/test_setup_runtime.py` and the `--setup` and `--setup-runtime` runner modes.
- Add `docs/setup.md` and update the README, help, AGENTS.md and `docs/validation.md`.
- Add the five-wrapper parity table to `docs/network-contract.md`. Update the Codex row of the table in `claude-container` `docs/network-contract.md` with a documentation-only commit in that repository. OpenCode, Pi and Antigravity receive the table with their own ports.

## Capabilities

### New Capabilities

- `container-setup`: interactive host-side setup covering:
  - the questionnaire and its prerequisites;
  - reviewed mutations and maintenance consent;
  - the protected installation and managed launch preferences;
  - authentication assistance;
  - qualification and smoke readiness;
  - repeatable activation with rollback;
  - the provider acknowledgement;
  - saved budgets.

### Modified Capabilities

- `container-session`: missing-mode admission points to setup; the first-user setup and migration guidance is added.
- `network-egress`:
  - restricted modes disable Codex's own sandbox through a protected override;
  - the missing-mode scenario directs to setup;
  - the alignment check uses the shared `test_alignment.py` across `network/` and `setup/`;
  - the contract documentation includes the parity table.

## Impact

- **Code:**
  - `codex-container.sh`: the `--container-setup` entry point, the setup-required message, the protected `sandbox_mode` override and the diagnostics filter;
  - new copied files: `setup/common.py`, `setup/setup.py`, `setup/launch.py`, `setup/smoke.py`.
- **Tests:**
  - shared `test_setup.py` and `test_alignment.py`;
  - per-agent `test_setup_runtime.py`;
  - updates to `test_wrapper.py`, `test_network_runtime.py`, `test_reference_copy.py` and `run-runtime.sh`.
- **Users:**
  - new users run `bash ./codex-container.sh --container-setup` once and then use the managed launcher;
  - direct operator launches still work with an explicit mode;
  - restricted sessions run Codex commands without Codex's inner sandbox.
- **Other repositories:** one documentation-only edit to `claude-container/docs/network-contract.md` (the Codex row of the parity table).
- **Out of scope:**
  - authenticated provider verification, which stays operator-run;
  - changes to shared files. A defect found in them is fixed in `claude-container` first.
