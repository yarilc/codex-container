# Network policy contract

Status: ported by the `add-network-egress` and `add-container-setup` changes.
Restricted modes, guided setup and the managed launcher are implemented and
verified with synthetic and real rootless runtime suites; the authenticated
OpenAI checks are operator-run and recorded separately in
[the validation record](validation.md). Setup is described in
[docs/setup.md](setup.md).

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md),
with [host-ca-trust](../openspec/specs/host-ca-trust/spec.md) and the session,
isolation, delegation and image specifications in `openspec/specs/`.

## Reference and intentional differences

The shared components are copied unchanged from `sandbox-container` at tag
`sandbox-ref-36` (commit `ce2c9d28873838a4ac541da34edaf7d8b5264be4`):

- `network/` (except the build output `network/bin/`);
- `setup/`;
- `launcher/` (the launcher core `launcher/core.sh`);
- the shared tests listed in that tag's `tests/test_alignment.py`.

The unchanged `tests/test_alignment.py` fails on a profile identifier (`codex`,
`openai`) in a shared file and checks the wrapper against the profile.
`tests/test_reference_copy.py` holds the SHA-256 of every copied file and fails
on a changed, missing or extra file. A defect in a shared file is fixed in
`sandbox-container` first and then copied; this repository never carries a
fork. [network/README.md](../network/README.md) is part of the copy and
describes the shared mechanism in agent-neutral terms.

Intentional differences are limited to per-agent files:

| File | Codex value or behavior |
| --- | --- |
| `agent/profile.json` | `codex-container`, prefix `CODEX_CONTAINER`, labels `io.codex-container.*`, images `localhost/codex-cli`, `localhost/codex-egress`, `localhost/codex-guard-toolchain`, home `/codex-home`, command `codex`, `CODEX_HOME`, `CODEX_YOLO`, no shared host directories |
| `agent/policies/default.json` | `openai-api`, `openai-account` (with the documentation MCP host) and the `openai-api-docs` extension, revision `openai-2026-11-11-v1` |
| `codex-container.sh` | The shared thin entry script; only the wrapper name in its comment differs |
| `agent/launcher.sh` | Codex profile values for the core; `CODEX_YOLO` → `--yolo`; protected `--no-daemon -c sandbox_mode="danger-full-access"` in restricted modes and the ten `-c` optional-traffic overrides in provider mode; `OPENAI_API_KEY` only for `openai-api` and `openai-api-docs`; no executable temporary storage |
| `Containerfile`, `.containerignore` | Codex image; copies `network/relay.py` and `network/mux.py` |
| `tests/test_wrapper.py` (Codex's agent part), `test_setup_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py`, `test_setup_runtime.py`, `run-runtime.sh`, `test_image_pins.py`, `test_reference_copy.py` | Codex names, synthetic Responses API fixture, OpenAI host inventories |

## Modes

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| unset or empty | `provider` (Codex's default); setup guidance without a protected installation or the saved provider settings | Rejected |
| `offline` | Own loopback, pipes and connected socket pairs only | Rejected |
| `provider` | As offline, plus one preconnected channel to an exact-destination proxy | Rejected |
| `unrestricted` (explicit only) | Ordinary runtime networking | Exact opt-in allowed |

A missing or empty mode selects `provider`; without the saved provider settings
it stops with setup guidance before engine queries and state creation, and a
managed empty override never restores the saved mode. Standalone qualification
uses the same default mode and fixed protected controls; it cannot launch an
arbitrary command. Maintenance consent never selects a mode.

Unknown modes fail before image operations. Restricted failures never retry
with unrestricted networking. Workspace and application settings, Codex's own
sandbox and approval settings, YOLO and shell mode cannot broaden the outer
policy. Restricted agents have no direct route, external resolver, UDP/QUIC,
host/LAN/metadata access or proxy administration access. Every agent container,
in every mode, drops all capabilities, enables no-new-privileges and has
verified memory, CPU and process budgets.

Restricted launches follow the shared launcher core's order: arguments; mode and
delegation; budgets and lifetime; engine verification; restricted platform
queries; state; CA; `network/session.py prepare`; image operations under the
maintenance gate; the immutable image ID; `network/qualify.py check`;
`session.py start` and `agent-args`; owned create and start; `session.py stop`
within the remaining shutdown budget.

## Provider profiles

| Profile | Destinations | Status |
| --- | --- | --- |
| `openai-api` | `api.openai.com:443` | Synthetic coverage; real API key unverified |
| `openai-account` | `auth.openai.com:443`, `chatgpt.com:443`, `developers.openai.com:443` | Static inventory and documentation MCP revalidated with Codex 0.169.0 (2026-11-18). Account sign-in, request and refresh await operator verification. |
| `openai-api-docs` | `api.openai.com:443`, `developers.openai.com:443` | Extension of `openai-api`; same documentation MCP measurement |

`OPENAI_API_KEY` is forwarded only to provider sessions whose profile is
`openai-api` or `openai-api-docs`. Base profiles are exact (the shared policy
code refuses added hosts): the account method's hosts include the documentation
MCP host, while the API method's base stays exact and `openai-api-docs` is the
explicit extension; setup proposes only the base profiles. Revision
`openai-2026-11-11-v1` removed `openai-account-docs`; existing provider
installations requalify once. ChatGPT sign-in uses `codex login --device-auth`; the
browser callback is unsupported. Optional traffic (update checks, analytics,
feedback, OTEL export, connectors and remote plugins) is disabled with `-c`
overrides placed before the operator's arguments, which take precedence over
the agent-writable `config.toml`. Remote MCP servers in `config.toml` have no
disable control; the proxy denies them, except the OpenAI documentation MCP
under `openai-account` or `openai-api-docs`. Restricted launches also pass a
protected `--no-daemon`: the shared background server needs a Unix listener the
guard denies, and the flag keeps Codex from printing its embedded-mode notice.

## Limits

- The proxy binds the initial and retried TLS ClientHello server name
  (`tls-clienthello-sni-v2`) to the CONNECT host; TLS 1.2 renegotiation is
  encrypted and not inspected.
- It does not prove exclusive OpenAI application access: the HTTP `Host`,
  shared-service routing and provider-side forwarding stay opaque.
- Allowed services can receive data: an injected agent can send workspace data
  to an allowed host with an attacker's key or account. Only `offline` removes
  this.
- Provider-hosted tools such as web search run outside the local boundary.
- Image pulls and build `RUN` steps happen outside runtime filtering and need
  separate maintenance authorization.
- Qualification reports are local (`locally-qualified`); the release
  acceptance inventory is empty.

## Five-wrapper parity

The same row appears in `sandbox-container/docs/network-contract.md`.

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Sandbox (reference) | Reference (`sandbox-ref-36`, shared launcher core) | Guard, qualification and guided setup integrated; session container engine for image toolchains, with systemd in nested containers, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer, offline and unrestricted modes; no provider mode (no authentication method); provider mechanics covered by the fixture profile and the fixture agent part | WSL ABI 3: all runner modes passed (2026-11-22); `sandbox-ref-29` to `sandbox-ref-31` runner modes in a nested `cgroupfs` engine passed except the recorded budget and explicit-limit tests, `sandbox-ref-32` and `sandbox-ref-33` modes from a session passed except the nested-engine cases, `sandbox-ref-34` all modes from a session passed except the nested-engine cases and the tests that need cgroup limits, and its engine case passed on the machine's engine (2026-11-24), `sandbox-ref-35` all modes passed natively, the terminal tests included (2026-11-25), `sandbox-ref-36` the unit discovery, default, network, qualification, setup and setup runtime modes passed natively, the terminal tests included, and the engine started without a capability error (2026-11-26); Podman machine on Windows: validation script passed on both PowerShell editions (2026-11-21) and on 5.1 with the session engine (2026-11-24), nested systemd: runtime and qualification modes passed on the machine's engine (2026-11-26); native Linux (Rocky 9, Podman 5.8.0, `systemd` with `memory` and `pids`, no IPv6): `sandbox-ref-34` engine budgets and offline engine sessions verified, `sandbox-ref-35` every mode passed with the guarded terminal tests unavailable, and a terminal attached in an interactive session (2026-11-25), `sandbox-ref-36` the same modes as on WSL passed with the guarded terminal tests unavailable, and an unrestricted session started its engine without a capability error (2026-11-26) | Not applicable |
| Claude | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, mandatory bootstrap, multiplexed proxy and guided setup integrated; session container engine for image toolchains, with systemd in nested containers, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-22); `sandbox-ref-34` modes from a Claude session with its engine passed except the nested-engine cases and the tests that need cgroup limits, and the engine and setup runtime cases passed on the machine's engine (2026-11-25), `sandbox-ref-35` unit discovery, guard, network, feasibility and setup runtime modes passed natively, the terminal tests included, with the interrupted-creation case passing alone after timeouts in the full network run (2026-11-25), and `sandbox-ref-36` unit tests of the changed files, setup, setup runtime, qualification and wrapper modes and the engine cases of the runtime and network suites passed natively, the other modes not rerun (2026-11-26); Podman machine on Windows: setup, account login, a Claude session and the validation script on both PowerShell editions passed (2026-11-22), and the validation script on 5.1 with the session engine (2026-11-24); native Linux (Rocky 9, Podman 5.8.0, `systemd` with `memory` and `pids`, no IPv6): `sandbox-ref-35` unit discovery, guard, network, feasibility and setup runtime modes passed with the guarded terminal tests unavailable, and a terminal attached in an interactive session (2026-11-25) | Account login, reuse and refresh passed; operator session with tool use passed (2026-11-11, `anthropic-account`); real-key API unavailable |
| Codex | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; Windows entry on a Podman machine (WSL provider) with installer and every network mode, no delegation | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-22); Podman machine on Windows: setup, device-code login, a Codex session, Codex's own sandbox in `unrestricted` and the validation script on both PowerShell editions passed (2026-11-22) | Operator session with tool use passed (2026-11-11, `openai-account`; 2026-11-22 on Windows); refresh and real-key API checks pending; synthetic Responses API streaming and tool call passed |
| Antigravity | Adopted `sandbox-ref-28`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; keyring removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode, no delegation | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, Google sign-in, an `agy` session with tool use, token reuse, the Gemini API key method with a dummy key and the validation script on both PowerShell editions passed (2026-11-23) | Operator session with tool use passed (2026-11-11, `google-account`, policy `antigravity-2026-11-11-v2`; 2026-11-23 on Windows); refresh and real-key Gemini API checks pending; synthetic Gemini streaming and tool call passed |
| OpenCode | Adopted `sandbox-ref-28`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; Windows entry on a Podman machine (WSL provider) with installer and every network mode, no delegation | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, an OpenCode session with tool use (`openrouter-api`), native variables through `OPENCODE_CONTAINER_ENV_VARS` and the validation script on both PowerShell editions passed (2026-11-23) | Operator session with tool use passed (2026-11-11, `anthropic-api`; 2026-11-23 on Windows, `openrouter-api`); the `openai-api` and `opencode-zen` profiles pending; synthetic Chat Completions streaming and tool call passed |
| Pi | Adopted `sandbox-ref-28`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; Windows entry on a Podman machine (WSL provider) with installer and every network mode, no delegation | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, a Pi session with tool use (`openrouter-api`), `PI_NPM_CACHE_SIZE` through `PI_CONTAINER_ENV_VARS` and the validation script on both PowerShell editions passed (2026-11-23) | Operator session with tool use passed (2026-11-11, `anthropic-api`; 2026-11-23 on Windows, `openrouter-api`); the `openai-api` and `gemini-api` profiles pending; synthetic Chat Completions streaming and tool call passed |

## Port status

| Item | Status |
| --- | --- |
| Shared copy, identifier scan and byte identity | Done (`tests/test_alignment.py`, `tests/test_reference_copy.py`) |
| Shared suites, guard, mux, policy, feasibility, qualification, setup | Passed in the runner; see [validation](validation.md) |
| Wrapper integration, restricted runtime and setup acceptance | Passed; see [validation](validation.md) |
| Authenticated OpenAI checks | Operator-run, pending |
