# Proposal

## Why

Codex adopted the toolchain library with `sandbox-ref-14`. claude-container
has since published two fixes to the shared `setup/toolchains.py`:

- `sandbox-ref-15`: toolchains cannot set any `XDG_` variable. A wrapper may
  place its state with them, and Podman keeps the last `--env`. Codex sets
  none, but the rule is shared, and Codex's copy must stay identical to the
  reference.
- `sandbox-ref-16`: a comment in the module no longer names an agent.

The dry run of `tools/propagate.py ../codex-container sandbox-ref-14
sandbox-ref-16` lists two modified files (`setup/toolchains.py`,
`tests/test_toolchains.py`), nothing added, removed or "not adopted", and
the manifest moving to commit `1fa091e`.

## What Changes

- Adopt `sandbox-ref-16` with `tools/propagate.py`. The tool:
  - copies the two shared files byte for byte;
  - moves the reference manifest and the current-state references
    (`README.md`, `AGENTS.md`, `docs/setup.md`, `docs/network-contract.md`,
    including the parity cells) to the tag.
- The README "Protected variables" bullet names `XDG_` variables.
- The `toolchain-library` spec gains the protected-variables requirement that
  the reference added in `sandbox-ref-15`.
- No launcher or test change. `setup/toolchains.py` is qualified code, so
  restricted installations rerun `--container-setup`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: session variables, including every `XDG_` variable,
  are protected from toolchains.

## Impact

- `setup/toolchains.py`, `tests/test_toolchains.py`,
  `tests/test_reference_copy.py`, `README.md`, `AGENTS.md`, `docs/setup.md`,
  `docs/network-contract.md`, `docs/validation.md`.
- `main` is one commit ahead of `origin/main` (the archive of
  `adopt-sandbox-ref-14`); that stays as it is.
