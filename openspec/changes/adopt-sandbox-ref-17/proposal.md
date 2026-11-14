# Proposal

## Why

Codex is on `sandbox-ref-16`. claude-container has published `sandbox-ref-17`
(change `share-toolchain-env-across-profiles`), which makes the toolchain
library work across wrappers in the same way:

- **Neutral variables:** `DBUS_SESSION_BUS_ADDRESS` joins the variables that
  every wrapper protects. No session has a bus.
- **Profile variables:** previously, if a toolchain in the shared index set a
  variable that only the current wrapper protects, `launch-env` refused the
  whole library. This happens when another wrapper installed the toolchain,
  for example one that sets `CLAUDE_CONFIG_DIR`. `launch-env` now leaves that
  variable out of the session and prints one warning naming the toolchain.

Without this change, Codex's copy of the shared module differs from the
reference. A toolchain installed from another wrapper could also block every
Codex session that uses the library.

The dry run of `tools/propagate.py ../codex-container sandbox-ref-16
sandbox-ref-17` lists:

- two modified files, `setup/toolchains.py` and `tests/test_toolchains.py`;
- nothing added, removed or "not adopted";
- the manifest moving to commit `a23f155`.

## What Changes

- **Adopt `sandbox-ref-17`** with `tools/propagate.py`. The tool:
  - copies the two shared files byte for byte;
  - moves the reference manifest and the current-state references to the tag.
    These are in `README.md`, `AGENTS.md`, `docs/setup.md` and
    `docs/network-contract.md`, including the parity cells.
- **README:** the "Protected variables" bullet describes both groups:
  - the neutral variables, including `DBUS_SESSION_BUS_ADDRESS`;
  - Codex's own variables (`CODEX_CONTAINER_*`, `CODEX_HOME`, `CODEX_YOLO`,
    `OPENAI_API_KEY`), which `add` rejects. When another wrapper installed a
    toolchain that sets one, `launch-env` leaves it out with a warning.
- **Spec:** the `toolchain-library` protected-variables requirement takes the
  reference's text.
- **No launcher change.** `codex-container.sh` reads only the standard output
  of `launch-env`, and the warnings go to standard error, so the session shows
  them as they are. `setup/toolchains.py` is qualified code, so restricted
  installations rerun `--container-setup`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: neutral and profile protected variables. The bus
  variable is protected, and another wrapper's variables in the shared index
  are left out with a warning instead of failing the session.

## Impact

- `setup/toolchains.py`, `tests/test_toolchains.py`,
  `tests/test_reference_copy.py`, `README.md`, `AGENTS.md`, `docs/setup.md`,
  `docs/network-contract.md`, `docs/validation.md`.
- Out of scope: OpenCode and Pi, which get their own changes.
