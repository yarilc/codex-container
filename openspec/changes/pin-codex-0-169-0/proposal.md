## Why

The image pins Codex 0.167.0 and OpenSpec 1.16.0. On 2026-11-18 the six
repositories agreed on a rule: pin the newest stable release that was at
least 72 hours old at that time. For Codex that is **0.169.0** (2026-11-13),
because 0.169.1 and 0.170.0 were too new. For OpenSpec it is **2.0.0**.

## What Changes

- **`Containerfile`**: `CODEX_VERSION` moves from `0.167.0` to `0.169.0`, and
  `OPENSPEC_VERSION` from `1.16.0` to `2.0.0`. The base digest does not change.
- **`agent/policies/default.json`**: `tested.cli` becomes 0.169.0, with the
  dates of the new static inventory and of the documentation-MCP measurement.
  The policy gets a new revision only if the allowed hosts change.
- **Tests that name the version**:
  - `tests/test_image_pins.py`: the diverging-CLI mutation and the OpenSpec
    version-range mutation;
  - `tests/test_network_runtime.py`: the version assertion and the comment on
    the Bubblewrap/Netlink measurement;
  - `tests/test_setup_runtime.py`: two version assertions.
- **Documentation**: the version-specific measurement notes in `README.md` and
  `docs/network-contract.md`, and a dated entry in `docs/validation.md`.
- **Revalidation**: a new inventory of 0.169.0 for `openai-account`,
  `openai-api` and `openai-api-docs`. It includes the documentation MCP and the
  Codex command-sandbox behavior under the guard.
- **Visible upstream change to check**: Codex 0.169.0 keeps project
  configuration and MCP servers disabled in untrusted directories under
  `codex exec`, and adds `--trust`. The wrapper's documented documentation-MCP
  setup (`codex mcp add`) is user-level configuration. The check confirms that
  it still works.
- **BREAKING (inside the image)**: OpenSpec 2.0 no longer generates `/opsx:*`
  command files. Codex reaches the skills as `$openspec-*`.

No shared launcher file changes and no new reference tag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None expected. If the inventory finds a new host that a profile requires, a
`network-egress` delta is added before implementation goes on. Until then
`skip_specs: true` applies.

## Impact

- **Files**:
  - `Containerfile` and `agent/policies/default.json`;
  - `tests/test_image_pins.py`, `tests/test_network_runtime.py` and
    `tests/test_setup_runtime.py`;
  - `README.md`, `docs/network-contract.md` and `docs/validation.md`.
- **Image identity**: the image changes. The operator reruns
  `--container-setup` on the three hosts.
- **Deferred**: authenticated account and real-key checks stay with the
  operator.
