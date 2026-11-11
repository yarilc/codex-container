# Design

## Context

See `proposal.md`. This change starts from the working tree of the unarchived `add-openai-docs-profile`, which adds `openai-api-docs` and `openai-account-docs` under revision `openai-2026-11-10-v1`.

Observed:
- **Notice source.** Codex 0.167.0 prints the embedded-mode notice from `tui/src/daemon_startup.rs` when command-line overrides are present.
- **`--no-daemon`.** Codex documents it as "Run without the shared background server, even if it is already running". It is accepted before `exec`, `login --help` and `mcp list` (exit 0). Whether it suppresses the notice in the interactive TUI has not been measured.
- **Profile mapping.** `agent/profile.json` maps each method to its `policy_profile` and its required `hosts`.
  - Setup saves the method, and the managed launcher derives the profile from it.
  - The shared validator requires a base profile to equal exactly its method's hosts.
  - It requires every profile of that method to contain those hosts.

  Adding `developers.openai.com` to the `account` hosts and to `openai-account` is therefore valid. `openai-account-docs` would duplicate `openai-account` and is removed.
- **The measured documentation MCP host.** Under Codex 0.167.0 it is only `developers.openai.com:443` (2026-11-10).
- **The account profile's identity.** It is part of the qualification identity: the policy file and the profile both change, so existing qualifications become stale.

## Goals / Non-Goals

**Goals:**
- A quiet default restricted session: no embedded-mode notice, and the documentation MCP working for account users.
- The guard, the protected overrides and the exact-profile model unchanged.

**Non-Goals:**
- Changing the API-key method's default; the operator asked only about the account profile.
- Changing shared code or setup, or adding a new tag.
- Silencing other Codex output.

## Decisions

### `--no-daemon` as the first protected argument

The restricted application becomes:

`/usr/local/bin/codex --no-daemon -c sandbox_mode="danger-full-access" [provider overrides] <operator arguments>`

`--no-daemon` is a global flag, accepted with subcommands, so it is safe before any operator arguments. It is added only in `offline` and `provider`, not in shell mode or `unrestricted`. In `unrestricted` the shared server can work, and no overrides force embedded mode.

Task 1.1 measures the TUI first. Codex is started in a PTY in a restricted-like container with the overrides, with and without `--no-daemon`, and the test asserts that the notice is absent only with the flag. If the flag does not suppress the notice, the change stops for the operator.

Rejected alternative: **moving the overrides to `/etc/codex/managed_config.toml`.** It needs a measurement that Codex treats it as non-overridable. The daemon still cannot run under the guard, so Codex would print a different notice ("Cannot use the shared background server").

### Documentation host in the account profile

- **`agent/profile.json`:** `account.hosts` gains `developers.openai.com`.
- **`agent/policies/default.json`:**
  - `openai-account` gains the destination;
  - `openai-account-docs` is removed;
  - the revision becomes `openai-2026-11-11-v1`, and `tested.cli` notes that the account profile includes the documentation MCP.

`openai-api` and `openai-api-docs` are unchanged. The wrapper's key forwarding already depends on the profile's `authentication`, so no wrapper change is needed beyond the arguments.

The tests change accordingly:
- `test_network_runtime.py` drops the controlled `account-docs` copy;
- it expects `developers.openai.com` to pass under `controlled-account` and to be denied under `controlled-api`;
- the opt-in real MCP check compares `openai-account` (reaches the server) with `openai-api` (denied).

### Documentation

The help and README describe:
- `--no-daemon` as a protected argument, and why;
- the account profile with three hosts;
- the API extension.

The README "Expected notices" text changes from "the notice is expected" to "the wrapper passes `--no-daemon`, so Codex runs embedded without a notice". The residual-exfiltration text names `developers.openai.com` for `openai-account`. A migration note says to rerun setup or `--container-qualify`.

## Risks / Trade-offs

- **[The account profile's allowlist grows by default]** → An OpenAI-operated documentation service only, chosen by the operator; disclosed in help, README and the contract. Offline remains the channel-free mode.
- **[A future Codex changes `--no-daemon` semantics]** → The runtime check asserts the absence of the notice and a working launch; the update procedure reruns it.
- **[Existing qualifications become stale]** → One `--container-qualify` or setup rerun, stated in the README migration note.

## Migration Plan

1. Rerun setup, or `--container-qualify` with the current environment, after updating.
2. Rollback: check out the previous `main` merge; base API users are unaffected.
