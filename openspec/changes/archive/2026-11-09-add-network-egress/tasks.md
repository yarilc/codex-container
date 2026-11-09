# Tasks

## 1. Copy the shared components from `sandbox-ref-2`

- [x] 1.1 Create branch `add-network-egress` from `main`. Unpack `network/` (without `bin/` and `__pycache__`), `setup/diagnostics.py` and the shared tests listed in Claude's `tests/test_alignment.py`, except `test_alignment.py` and `test_setup.py`, using `git -C ../claude-container archive sandbox-ref-2`. Verify with `diff -r` against a `sandbox-ref-2` worktree of Claude: no differences.
- [x] 1.2 Add the per-agent `tests/test_reference_copy.py`:
  - a SHA-256 manifest of every copied file at `sandbox-ref-2`;
  - failure on a changed, missing or extra file in `network/`;
  - a scan for the profile identifiers;
  - an optional `diff -r` against a sibling checkout at the tag.
  Verify that it passes, and that it fails on an injected byte change and on an injected `codex` literal, each made in a scratch copy.

## 2. Measure the Codex-specific unknowns

- [x] 2.1 Static inventory of the installed `@openai/codex@0.167.0`: list the URLs and hosts the CLI contains, and check the official Codex authentication documentation. Record in `docs/validation.md` (dated, with the CLI version):
  - the candidate `openai-account` hosts;
  - whether device-code login is supported, and its arguments;
  - the API-key variable.
- [x] 2.2 Identify the 0.167.0 `-c` keys or variables for update checks, analytics, feedback, OTEL export and remote MCP or connectors, and verify each with `codex --help`, the package configuration schema or a credential-free run. Record each supported control and each missing one.
- [x] 2.3 With an operator-built guard (task 3.2), run a disposable `localhost/codex-cli` container with `--cap-drop=all`, no-new-privileges and the guard in offline mode. Run `codex sandbox linux` or an equivalent credential-free command execution, through both the Landlock and the Bubblewrap paths. Record the outcome and the chosen configuration from design.md in `docs/validation.md`.
- [x] 2.4 Run the guard runtime fixtures with Codex's executable `/tmp`, `/var/tmp` and `/codex-home` tmpfs layout. Verify that layout validation passes. If it fails, stop and report the shared-code finding rather than patching `network/`.

## 3. Agent profile, policy and operator artifacts

- [x] 3.1 Write `agent/profile.json` with the values from design.md and the measured account hosts and login arguments. Write `agent/policies/default.json` with `openai-api` (`api.openai.com:443`) and `openai-account`, revision `openai-2026-11-09-v1`, `source_date`, `sources` and `tested.cli` `0.167.0`, with authentication marked unverified. Verify that `python3 -I network/agent_profile.py` validation and `tests/test_agent_profile.py` and `tests/test_network_policy.py` pass.
- [x] 3.2 Build the guard toolchain image `localhost/codex-guard-toolchain:development`. Run `CODEX_CONTAINER_MAINTENANCE=1 bash network/build-guard.sh` into a protected native `network/bin` of a disposable installation. Build `localhost/codex-egress` from `network/Containerfile` and record its image ID. Verify the guard SHA-256 manifest and `bash tests/run-runtime.sh --guard`.
- [x] 3.3 Run the copied shared suites in the runner: `test_network_policy`, `test_mux`, `test_tls_client_hello`, `test_tls_proxy`, `test_platform`, `test_qualification`, `test_guard`, `test_session`, `test_network_feasibility` and `test_agent_profile`. They must all pass without edits to shared files.

## 4. Runtime image

- [x] 4.1 Add `COPY network/relay.py network/mux.py /opt/sandbox-egress/` to `Containerfile`, and admit only these two files plus `Containerfile` and `.containerignore` in `.containerignore`. Extend `tests/test_image_pins.py` so it requires `CODEX_VERSION` to equal the policy's `tested.cli` and names both versions on a mismatch. Verify the pin tests, including an injected divergence, and a rebuilt image with `codex --version` reporting 0.167.0.

## 5. Wrapper integration

- [x] 5.1 Mode admission:
  - parse `CODEX_CONTAINER_NETWORK`; an unset or empty value stops before engine calls, naming the three values and `unrestricted` as the previous behavior;
  - unknown values fail;
  - `CODEX_CONTAINER_PODMAN=1` is rejected in restricted modes;
  - help keeps its existing behavior and gains the new variables, the migration notes and the provider disclosure.
  Verify with `test_wrapper.py` cases for each combination of Codex, shell, build, worktree and YOLO.
- [x] 5.2 Maintenance gate: image builds, automatic or explicit, require exact `CODEX_CONTAINER_MAINTENANCE=1`. Without it, the wrapper stops before any pull or build. Restricted preconditions are checked before image operations. Verify with fake-engine cases for: image present, absent with and without authorization, explicit build with and without authorization, inspection error, and an invalid policy with authorization.
- [x] 5.3 State and CA:
  - `CODEX_CONTAINER_STATE_DIR` gives an isolated private `/codex-home` and conflicts with a nonempty `CODEX_HOME`;
  - it rejects escaping `.codex` and `ca` paths, and repairs nothing;
  - `CODEX_CONTAINER_TRUST_HOST_CA` and `CODEX_CONTAINER_CA_BUNDLE` give a read-only `/codex-home/ca/bundle.pem` plus the four variables.
  Verify with `test_wrapper.py` cases for: both state modes, the conflict, privacy failures, an escaped symlink, CA off, `1` and `maybe`, an explicit or missing bundle, and no default bundle.
- [x] 5.4 Restricted preparation, in the Claude order:
  - platform queries;
  - `session.py prepare` with the workspace, state and `/codex-home` writable and mount targets;
  - the immutable runtime image ID;
  - proxy image acquisition only under maintenance and a digest;
  - `qualify.py check`;
  - `session.py start`, then `agent-args`, then container creation with the restricted arguments;
  - `session.py stop` within the remaining shutdown budget, terminating an in-flight `start` by process group.
  Verify with fake-engine `test_wrapper.py` cases for argument assembly, the order of operations, interrupted start, preserved exit status and owned cleanup.
- [x] 5.5 Provider specifics:
  - the profile is selected by `CODEX_CONTAINER_NETWORK_PROFILE`;
  - `OPENAI_API_KEY` is passed only for `openai-api`;
  - optional-traffic controls from task 2.2 are inserted before the user's arguments and are present in shell mode where they are variables;
  - the startup report gives mode, profile and policy revision.
  Verify with `test_wrapper.py` that writable `config.toml` or user `-c` arguments placed after the protected ones cannot remove a protected override, or document precedence if Codex resolves duplicates differently.
- [x] 5.6 Add `--container-qualify` (alone, offline by default, no application command) using `network/qualify.py`, with the Claude argument rules. Verify with fake-engine cases and with `tests/test_qualification.py`.
- [x] 5.7 Unrestricted regression: with `CODEX_CONTAINER_NETWORK=unrestricted` and maintenance where needed, the existing `test_wrapper.py` and `test_runtime.py` lifecycle, delegation, YOLO, budget and workspace cases pass unchanged except for the added mode and maintenance variables. Verify with the full unit suite in the runner.

## 6. Runtime acceptance with real rootless Podman

- [x] 6.1 Adapt `test_network_runtime.py`, `network_tls_fixture.py` and the `tests/run-runtime.sh` modes (`--network-feasibility`, `--network-policy`, `--network`, `--mux`, `--guard`, `--guard-idle` and `--qualification`) to Codex names. Verify that every mode passes on the WSL target with disposable native state.
- [x] 6.2 Offline acceptance through `codex-container.sh`, after `--container-qualify`:
  - no IPv4, IPv6, DNS or UDP egress;
  - host socket and abstract socket denial;
  - loopback and connected pairs work;
  - files persist with caller ownership;
  - Codex's own sandbox outcome from task 2.3.
  Verify through the runtime suite.
- [x] 6.3 Provider acceptance with controlled fixtures:
  - matching CONNECT and SNI pass with certificate verification;
  - mismatched SNI is rejected with zero bytes forwarded;
  - denied authority, redirect, IP-literal and deceptive-suffix requests fail;
  - proxy loss fails closed;
  - CA off and on behave as specified;
  - the proxy budgets and hardening are verified.
  Also check that Codex's HTTPS and streaming requests to a controlled endpoint honor the relay, with no real OpenAI credentials. Verify through the runtime suite.
- [x] 6.4 Concurrency and cleanup: two concurrent Codex provider sessions, plus one Claude restricted session if the sibling installation is available. Verify that their labels and resources are distinct, that each cleans up only its own resources, and that nothing is left over (`podman ps -a`, networks and volumes filtered by `io.codex-container`).

## 7. Documentation and evidence

- [x] 7.1 Update `README.md` with:
  - network modes and migration;
  - maintenance, state, CA and `--container-qualify`;
  - the operator build inputs;
  - provider limits, the residual exfiltration disclosure for the OpenAI hosts and the hosted-tools boundary;
  - the documented qualification behaviors (reboot, unidentifiable LSM policy, empty release inventory);
  - the browser sign-in limitation.
  Update `AGENTS.md` with the shared-file rule and the test commands. Verify with markdownlint on the changed files and `git diff --check`.
- [x] 7.2 Add `docs/network-contract.md` (reference tag and commit, intentional differences limited to `agent/` and per-agent files, mode and profile contract, limits, port status). The copied `network/README.md` stays unchanged. Verify that the file exists, that its links resolve, and that markdownlint passes.
- [x] 7.3 Record in `docs/validation.md`:
  - the target, Podman version, guard digest, image IDs and test results by mode;
  - the measured host inventory and the Codex sandbox outcome;
  - operator-run authenticated checks (API key and account login, request, refresh, streaming), marked unavailable until the operator runs them.
  Verify that every claim in the README has a matching evidence entry.
- [x] 7.4 Final verification:
  - `bash -n codex-container.sh` and ShellCheck;
  - the full unit suite in the runner;
  - all runtime modes;
  - `openspec validate add-network-egress --strict`;
  - `git diff --check`.
  Update `todo.md` items N01–N14 (Codex part) and C02–C08 and C12 with their status and the evidence location.

## Workflow follow-up

- Operator-run authenticated checks (API key and ChatGPT account through `openai-account`) before declaring a profile verified; results go into `docs/validation.md`.
- `/opsx:archive`, then commit and merge into `main`; the user pushes.
- Next change: `add-container-setup` (C09, `setup/`, `test_alignment.py`, `test_setup.py`, `docs/setup.md`, the missing-setup message, the parity table in all five repositories).
