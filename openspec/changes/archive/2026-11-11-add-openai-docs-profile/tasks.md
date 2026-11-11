# Tasks

## 1. Measure and define the profiles

- [x] 1.1 With the installed Codex 0.167.0, a disposable `CODEX_HOME` declaring `[mcp_servers.openaiDeveloperDocs]` with `url = "https://developers.openai.com/mcp"`, and a logging CONNECT proxy (as for the account inventory), record:
  - whether the MCP client uses `HTTPS_PROXY`;
  - every CONNECT authority of the initialize and tool-list calls.

  If the client bypasses the proxy, stop and report to the operator.
- [x] 1.2 Add `openai-account-docs` and `openai-api-docs` to `agent/policies/default.json` with the base hosts plus the measured documentation hosts. Move the revision to `openai-2026-11-10-v1` and add the measurement to the sources and the tested notes. Verify the policy against the profile rules, `tests/test_network_policy.py` and `tests/test_agent_profile.py`.

## 2. Wrapper

- [x] 2.1 Forward `OPENAI_API_KEY` for `openai-api` and `openai-api-docs`. Update the help: the extension profiles, how to select them, and the residual-exfiltration hosts. Add `test_wrapper.py` cases:
  - every profile whose policy `authentication` is `api` forwards the key, and every other profile does not;
  - the help names both extension profiles.

## 3. Runtime acceptance

- [x] 3.1 Extend the per-agent network runtime tests with controlled copies of the extension profiles and the TLS fixture:
  - the documentation hosts pass under `openai-*-docs`;
  - they are denied under the base profiles;
  - another MCP-like host stays denied.
- [x] 3.2 With a disposable `CODEX_HOME` declaring the documentation MCP server, launch provider mode through the wrapper with `openai-account-docs` and with `openai-account`. Record:
  - whether the MCP client initializes, or fails only for lack of credentials, under the extension profile;
  - the denial under the base profile, with the denied host in the sanitized log.

  No account credentials are used.

## 4. Documentation and verification

- [x] 4.1 Update the README: the profile table, selection for direct and managed launches, the residual-exfiltration hosts, and a troubleshooting section for the embedded-mode notice and denied MCP servers. Update `docs/network-contract.md` (profiles and the revision) and `CHANGELOG.md` (requalification needed). Verify with markdownlint and `git diff --check`.
- [x] 4.2 Final verification:
  - `bash -n` and ShellCheck;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--network-policy` and `--network`;
  - `openspec validate add-openai-docs-profile --strict`.

  Record the measurements and results in `docs/validation.md`, separately from the operator's uncommitted smoke-check section already in that file.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main`; the user pushes.
- Possible later shared change: offer extension profiles in setup.
