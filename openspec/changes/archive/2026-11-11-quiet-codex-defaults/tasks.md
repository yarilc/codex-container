# Tasks

## 1. Quiet restricted launches

- [x] 1.1 Measure first. Start Codex 0.167.0 in a PTY, in a container with `--network=none`, a disposable `CODEX_HOME` and the protected `-c` overrides, with and without `--no-daemon`. Record whether the embedded-mode notice appears. If `--no-daemon` does not suppress it, stop and report to the operator.
- [x] 1.2 Add the protected `--no-daemon` as the first argument after `/usr/local/bin/codex` in offline and provider launches (not shell, not unrestricted). Update the help. Update the `test_wrapper.py` expectations for the protected argument list, including the ordering before operator arguments and its absence in shell and unrestricted launches.

## 2. Account profile with the documentation host

- [x] 2.1 Add `developers.openai.com` to `account.hosts` in `agent/profile.json` and to `openai-account` in `agent/policies/default.json`. Remove `openai-account-docs`. Move the revision to `openai-2026-11-11-v1` and update the tested notes. Verify:
  - the policy against the profile rules;
  - `tests/test_agent_profile.py` and `tests/test_network_policy.py`;
  - the key-forwarding test, which follows the policy's `authentication`.
- [x] 2.2 Update the network runtime tests:
  - drop the controlled `account-docs` profile;
  - the documentation host passes under `controlled-account` and `controlled-api-docs`, and is denied under `controlled-api`;
  - the opt-in real MCP check compares `openai-account` (reaches the server) with `openai-api` (denied).

## 3. Documentation and verification

- [x] 3.1 Update:
  - **wrapper help:** the protected `--no-daemon`, the account hosts and the residual-exfiltration hosts;
  - **README:** the profile table and extension text, "Expected notices" (now suppressed by `--no-daemon`), the residual-exfiltration hosts and the migration note (rerun setup or `--container-qualify`);
  - **`docs/network-contract.md`:** the profiles, the revision and the protected arguments.

  Verify with markdownlint and `git diff --check`.
- [x] 3.2 Final verification:
  - `bash -n` and ShellCheck (no new findings);
  - `bash tests/run-runtime.sh` with `--wrapper`, `--shared`, `--network-policy` and `--network`;
  - the opt-in real MCP check (`SANDBOX_EXTERNAL_TESTS=1`);
  - an interactive restricted TUI launch through the wrapper with no notice;
  - `openspec validate quiet-codex-defaults --strict`.

  Record in `docs/validation.md`.

## Workflow follow-up

- Archive `add-openai-docs-profile` first, then this change. Commit and merge into `main`; the user pushes.
