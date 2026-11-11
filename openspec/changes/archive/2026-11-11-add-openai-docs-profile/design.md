# Design

## Context

See `proposal.md`. Observed:
- **Base profiles are exact.** `network/policy.py` (shared, `sandbox-ref-9`) rejects any destination outside the authentication hosts for a base profile (`openai-api`, `openai-account`), with "use a new profile for extensions". Extension profiles are allowed. They must contain the authentication hosts of their `authentication` method, and may add other hosts on any port, with no wildcards and no local address exceptions.
- **The wrapper selects the profile by name.** `codex-container.sh` forwards `OPENAI_API_KEY` only when `CODEX_CONTAINER_NETWORK_PROFILE` is exactly `openai-api`.
- **Setup and the managed launcher.** Setup saves the base profile of the chosen method. The managed launcher (`setup/launch.py`, shared) applies saved values only for variables absent from the environment, so an exported `CODEX_CONTAINER_NETWORK_PROFILE` takes precedence. The qualification identity binds the selected profile and the policy file.
- **Codex 0.167.0 MCP.** The CLI's own hint registers `openaiDeveloperDocs` with `--url https://developers.openai.com/mcp`, a streamable HTTP transport. Whether it honors `HTTPS_PROXY`, and which hosts the server redirects to, has not been measured.
- **Protected overrides.** Provider sessions pass `features.apps=false`, `features.plugins=false`, `features.remote_plugin=false` and `features.plugin_discovery_prefetch=false`. None of them disables user-declared `mcp_servers`, which is why the MCP client started and was denied.
- **The embedded-mode notice** comes from the Codex TUI (`tui/src/daemon_startup.rs`) whenever `-c` overrides are present. The `--no-daemon` flag exists, but changing the arguments is out of scope.

## Goals / Non-Goals

**Goals:**
- An opt-in, explicitly selected profile pair that admits only the documentation MCP hosts in addition to the base hosts.
- Base profiles, setup defaults and existing qualifications for base profiles are unchanged.
- The disclosure and documentation name the new hosts.

**Non-Goals:**
- Changing the shared policy code or setup, which would need a new reference tag.
- Silencing the embedded-mode notice. The operator chose documentation.
- Allowing any other MCP server or OpenAI host.

## Decisions

### Two extension profiles, measured hosts

`openai-account-docs` (authentication `account`) and `openai-api-docs` (authentication `api`) each list their base hosts plus the documentation hosts. Task 1.1 measures the documentation hosts:
1. run the MCP client against a logging CONNECT proxy, as done for the account inventory;
2. start with `developers.openai.com:443`;
3. add any redirect or asset host the initialize and tool-list calls need, but no CDN wildcard.

If the client bypasses the proxy, the extension is useless and the change stops for the operator.

The policy revision moves from `openai-2026-11-09-v1` to `openai-2026-11-10-v1`, with the sources and the tested CLI unchanged except for the measurement note.

Rejected alternatives:
- **Add the host to the base profiles.** The shared code refuses it, and it would silently widen every existing installation.
- **A separate `docs` profile combined at runtime.** One profile per session is the shared model.

### Explicit selection, no setup change

Operators who want the documentation MCP export `CODEX_CONTAINER_NETWORK_PROFILE=openai-account-docs` (or `openai-api-docs`) and run `--container-qualify` once. Managed launches then use it, because exported values win. The README shows both the direct and the managed form. Offering extension profiles in setup is a possible later shared change.

### Key forwarding by profile family

The forwarding test becomes `openai-api|openai-api-docs`. A test checks that every profile in the policy whose `authentication` is `api` forwards the key and that every other profile does not. This keeps the list in step with the policy.

### Documentation of the two notices

A README troubleshooting section explains:
- the embedded-mode notice (expected in restricted modes; the shared server needs a Unix listener that the guard denies);
- a denied MCP server under a base profile. Set `enabled = false` for that server in `config.toml`, or select a documentation extension profile.

## Risks / Trade-offs

- **[Wider allowlist]** → Opt-in only, separately qualified, and named in the residual-exfiltration disclosure. The endpoint is OpenAI-operated documentation, not an arbitrary host.
- **[The MCP server's hosts change in a later Codex or server release]** → The inventory is dated and pinned to Codex 0.167.0. A missing host fails closed and is visible in the denial log. The update procedure remeasures it.
- **[Existing provider qualifications become stale]** → The policy file changes, so `--container-qualify` is needed once. `CHANGELOG.md` and the README migration note say so.

## Migration Plan

1. Rerun `--container-qualify`, or setup, after updating, because the policy revision changed.
2. To use the documentation MCP: export the extension profile and qualify it.
3. Rollback: check out the previous `main` merge; base-profile users are unaffected either way.
