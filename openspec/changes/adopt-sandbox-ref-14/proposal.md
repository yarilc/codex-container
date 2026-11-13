# Proposal

## Why

claude-container published `sandbox-ref-13` with the operator-managed
toolchain library (change `add-toolchain-library`). The library is one host
directory shared by all five wrappers and mounted read-only at
`/toolchains`, so a restricted session can use Java, Go or another
relocatable toolchain without Podman access, an unrestricted network or a
rebuilt image.

`sandbox-ref-14` (change `fix-qualification-fixture-setup`) fixes the shared
qualification runtime fixture, which did not install `setup/` and failed six
`--qualification` tests since `sandbox-ref-13`. The failure was found while
this change first adopted `sandbox-ref-13`; Codex therefore adopts
`sandbox-ref-14` directly and never carries `sandbox-ref-13`.

Codex is on `sandbox-ref-12`. Without this change:

- its shared files diverge from the reference and its parity table falls
  behind;
- Codex sessions cannot see the library the operator already maintains for
  Claude Code.

The shared module `setup/toolchains.py` is agent-agnostic, but the launcher
integration (dispatch, mount, environment, help text) is wrapper code and must
be ported by hand.

## What Changes

- **Adopt `sandbox-ref-14`** with `tools/propagate.py` (`sandbox-ref-12` →
  `sandbox-ref-14`). The tool copies eight shared files byte for byte:
  - added: `setup/toolchains.py`, `tests/test_toolchains.py`;
  - modified: `network/agent_profile.py` (the `TOOLCHAINS` and
    `TOOLCHAINS_DIR` suffixes), `network/control.py` (trusted
    `setup/toolchains.py`), `network/qualification_records.py`
    (`SHARED_CODE`), `setup/common.py` (`MANIFEST`), `tests/test_alignment.py`
    (`SHARED_TESTS`), `tests/test_qualification.py` (the fixture installs
    `setup/common.py` and `setup/toolchains.py`).

  It also moves the reference manifest and the current-state references to
  the tag.
- **Port the launcher integration to `codex-container.sh`:**
  - `--container-toolchain add|list|remove|verify` as the first argument,
    dispatched to the shared module before the network mode is read;
  - `CODEX_CONTAINER_TOOLCHAINS` (`0`/`false`/`no` omits the mount) and
    `CODEX_CONTAINER_TOOLCHAINS_DIR`, with the existing `boolean` helper;
  - the library checked by `launch-env` against the workspace and the Codex
    state (`CODEX_CONTAINER_STATE_DIR` or `CODEX_HOME`), then mounted at
    `/toolchains` with `ro,nosuid,nodev`;
  - `--mount-target /toolchains` for restricted sessions;
  - default toolchain `PATH` entries appended after the runtime image's
    `PATH`, plus their variables;
  - help text for the option and both variables.
- **Tests:** wrapper cases with the fake engine and real-engine runtime cases,
  ported from the reference.
- **Test runner:** `tests/run-runtime.sh` gives the suites a private
  executable tmpfs as `SANDBOX_TEST_TMPDIR`, and `tests/test_wrapper.py`
  creates its fixtures there, as in the reference since `sandbox-ref-14`.
  Without it `--wrapper` fails, because the image's world-writable `/tmp` is
  refused as an ancestor of the toolchain library.
- **Documentation:** a README "Toolchains" section adapted to Codex (the
  `AGENTS.md` instruction line, Codex's executable `/tmp`, shared-state
  paths), the help-related parts, `AGENTS.md` and `docs/setup.md`
  (requalification). The example recipes stay in claude-container and are
  linked, not copied.
- **BREAKING (installation):** the launcher and the qualified shared code
  change, so restricted installations rerun `--container-setup`.

## Capabilities

### New Capabilities

- `toolchain-library`: the shared library, the `--container-toolchain`
  command, and the read-only `/toolchains` mount and default environment in
  Codex sessions.

### Modified Capabilities

None. Existing requirements do not enumerate the session mounts exhaustively.

## Impact

- The eight shared files, `tests/test_reference_copy.py`, `README.md`,
  `AGENTS.md`, `docs/setup.md`, `docs/network-contract.md` (parity cells),
  `docs/validation.md`.
- `codex-container.sh`, `tests/test_wrapper.py`, `tests/test_runtime.py`,
  `tests/test_network_runtime.py`, `tests/run-runtime.sh`.
- Out of scope: registry network access for toolchain dependencies (the
  planned proxy ACL CLI), copying the example recipes, and the other three
  wrappers (their own changes).
