# Proposal

## Why

The operator wants the default restricted Codex session to be useful and quiet, while the guard stays the boundary. Two defaults fall short today:
- **The embedded-mode notice.** Every `offline` and `provider` launch prints `Running without the shared background server: command-line configuration overrides (-c, --enable, --disable, or --search) requires embedded mode.` The protected `-c` overrides force embedded mode, and the shared background server cannot run under the guard anyway, because it needs a Unix listener.
- **The documentation MCP.** It is denied under the default account profile. `add-openai-docs-profile` admits it only through an explicitly selected `openai-account-docs` extension.

On 2026-11-11 the operator decided:
- launch Codex with `--no-daemon` in the restricted modes;
- add `developers.openai.com` to the base `openai-account` profile, which setup proposes by default;
- remove `openai-account-docs`.

This change builds on the unarchived `add-openai-docs-profile` and is archived after it.

## What Changes

- **Restricted launches add `--no-daemon`.** Offline and provider Codex launches pass the protected `--no-daemon` before the protected `-c` overrides, so Codex runs embedded explicitly and prints no notice. Shell sessions and `unrestricted` launches are unchanged. The guard, the `-c sandbox_mode="danger-full-access"` override and the other protected overrides stay as they are.
- **Account profile includes the documentation MCP.**
  - `openai-account` gains `developers.openai.com:443`: the `account` method's hosts in `agent/profile.json` and the profile in `agent/policies/default.json` both list it.
  - `openai-account-docs` is removed.
  - The policy revision moves to `openai-2026-11-11-v1`.
  - Existing provider qualifications need `--container-qualify` (or setup) once.
- **API profiles unchanged.** The operator did not ask to change the API-key method: `openai-api` stays its exact default, and `openai-api-docs` stays the opt-in extension with the documentation host.
- Documentation and tests follow:
  - help, README, network contract and validation record;
  - wrapper, policy and network runtime tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`:
  - the OpenAI profiles requirement: `openai-account` includes the documentation host, and the `openai-account-docs` extension is removed;
  - the native-sandbox requirement: restricted launches add the protected `--no-daemon`;
  - the optional-traffic requirement: the documentation MCP is admitted under `openai-account` and `openai-api-docs`, and the notice is suppressed rather than documented;
  - the residual-exfiltration disclosure: the hosts for `openai-account`.

## Impact

- **Files:**
  - `codex-container.sh`;
  - `agent/profile.json` and `agent/policies/default.json`;
  - `tests/test_wrapper.py`, `tests/test_network_runtime.py` and possibly `tests/network_tls_fixture.py`;
  - the README, `docs/network-contract.md` and `docs/validation.md`.
- **No change** to `network/`, `setup/` or the shared tests, so no new reference tag. The shared validator already accepts the account method with three hosts.
- **Users:**
  - account users in provider mode now reach the documentation MCP by default;
  - the residual-exfiltration channel of `openai-account` gains an OpenAI-operated host;
  - an operator who wants only the sign-in and model hosts uses offline mode or an explicit custom profile;
  - managed installations pick up the new profile after rerunning setup or qualification.
