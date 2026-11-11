# Proposal

## Why

An operator testing provider mode on 2026-11-10 saw the OpenAI documentation MCP server fail. Their shared `config.toml` declares it, as Codex itself suggests (`codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp`). The error was `error sending request for url (https://developers.openai.com/mcp?source=codex)`.

This is the boundary working as specified: `developers.openai.com` is in no profile, so the proxy denies it. The operator decided on 2026-11-10 to allow it as an explicit choice. The shared policy code (`network/policy.py`) keeps base profiles exact and rejects added hosts ("use a new profile for extensions"), so the hosts go into new extension profiles rather than into `openai-account` and `openai-api`.

The same test also showed `Running without the shared background server: command-line configuration overrides (-c, ...) requires embedded mode`. That message is expected: the protected `-c` overrides select embedded mode, and the shared server could not run under the guard anyway, because it needs a Unix listener. This change documents the message and does not alter it.

## What Changes

- Add two extension profiles to `agent/policies/default.json`, under a new policy revision:
  - `openai-account-docs`: authentication `account`, destinations `auth.openai.com:443`, `chatgpt.com:443` and the OpenAI documentation MCP hosts;
  - `openai-api-docs`: authentication `api`, destinations `api.openai.com:443` and the same documentation hosts.

  The documentation hosts are `developers.openai.com:443` plus any other host the MCP client contacts, as measured with the installed Codex 0.167.0.
- The base profiles stay unchanged and remain the setup defaults. An operator selects an extension profile explicitly with `CODEX_CONTAINER_NETWORK_PROFILE` (exported for managed launches or set for direct ones), then runs `--container-qualify` for it.
- `OPENAI_API_KEY` is forwarded with `openai-api-docs` as with `openai-api`.
- Documentation:
  - **README and wrapper help:** the extension profiles, how to select them, and the residual-exfiltration hosts.
  - **README troubleshooting:** the embedded-mode message, and denied MCP servers under base profiles (disable them with `enabled = false`, or select an extension profile).
  - **Elsewhere:** the contract and the validation record.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`:
  - the OpenAI profiles requirement gains the two extension profiles, explicit selection and key forwarding;
  - the optional-traffic requirement records the documentation MCP as the only remote MCP endpoint an extension profile admits;
  - the residual-exfiltration disclosure names the documentation hosts.

## Impact

- **Files:**
  - `agent/policies/default.json`;
  - `codex-container.sh`: key forwarding and help;
  - `tests/test_wrapper.py`;
  - per-agent network runtime tests;
  - the README, `docs/network-contract.md` and `docs/validation.md`.
- **No change** to `network/`, `setup/` or the shared tests, so no new reference tag.
- **Users:** none unless they opt in. Opting in widens the provider allowlist to an OpenAI-operated documentation service. A prompt-injected agent can send workspace data there as in any MCP query, but it reaches an OpenAI service, not an arbitrary host.
- **Qualification:** the policy revision changes, so existing provider qualifications that bind the policy file require `--container-qualify` again.
