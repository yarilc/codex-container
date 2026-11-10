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

The shared components are copied unchanged from `claude-container` at tag
`sandbox-ref-8` (commit `12cffab0d248ec48a95f3b1840c573fcebdbb427`):

- `network/` (except the build output `network/bin/`);
- `setup/`;
- the shared tests listed in that tag's `tests/test_alignment.py`.

The unchanged `tests/test_alignment.py` fails on a profile identifier (`codex`,
`openai`) in a shared file and checks the wrapper against the profile.
`tests/test_reference_copy.py` holds the SHA-256 of every copied file and fails
on a changed, missing or extra file. A defect in a shared file is fixed in
`claude-container` first and then copied; this repository never carries a
fork. [network/README.md](../network/README.md) is part of the copy and
describes the shared mechanism in agent-neutral terms.

Intentional differences are limited to per-agent files:

| File | Codex value or behavior |
| --- | --- |
| `agent/profile.json` | `codex-container`, prefix `CODEX_CONTAINER`, labels `io.codex-container.*`, images `localhost/codex-cli`, `localhost/codex-egress`, `localhost/codex-guard-toolchain`, home `/codex-home`, command `codex`, `CODEX_HOME`, `CODEX_YOLO`, no shared host directories |
| `agent/policies/default.json` | `openai-api` and `openai-account`, revision `openai-2026-11-09-v1` |
| `codex-container.sh` | Codex arguments, shared or isolated state layout, executable `/tmp`, `/var/tmp` and `/codex-home`, protected `-c` overrides (including `sandbox_mode="danger-full-access"` in restricted modes), API key only for `openai-api` |
| `Containerfile`, `.containerignore` | Codex image; copies `network/relay.py` and `network/mux.py` |
| `tests/test_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py`, `test_setup_runtime.py`, `run-runtime.sh`, `test_image_pins.py`, `test_reference_copy.py` | Codex names, synthetic Responses API fixture, OpenAI host inventories |

## Modes

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| unset or empty | Launch stops with setup guidance before engine calls and state creation | No session |
| `offline` | Own loopback, pipes and connected socket pairs only | Rejected |
| `provider` | As offline, plus one preconnected channel to an exact-destination proxy | Rejected |
| `unrestricted` (explicit only) | Ordinary runtime networking | Exact opt-in allowed |

Unknown modes fail before image operations. Restricted failures never retry
with unrestricted networking. Workspace and application settings, Codex's own
sandbox and approval settings, YOLO and shell mode cannot broaden the outer
policy. Restricted agents have no direct route, external resolver, UDP/QUIC,
host/LAN/metadata access or proxy administration access. Every agent container,
in every mode, drops all capabilities, enables no-new-privileges and has
verified memory, CPU and process budgets.

Restricted launches follow the Claude wrapper order: arguments; mode and
delegation; budgets and lifetime; engine verification; restricted platform
queries; state; CA; `network/session.py prepare`; image operations under the
maintenance gate; the immutable image ID; `network/qualify.py check`;
`session.py start` and `agent-args`; owned create and start; `session.py stop`
within the remaining shutdown budget.

## Provider profiles

| Profile | Destinations | Status |
| --- | --- | --- |
| `openai-api` | `api.openai.com:443` | Synthetic coverage; real API key unverified |
| `openai-account` | `auth.openai.com:443`, `chatgpt.com:443` | Measured statically from Codex 0.167.0 and the documentation; sign-in, request and refresh unverified |

`OPENAI_API_KEY` is forwarded only to provider sessions whose profile is
exactly `openai-api`. ChatGPT sign-in uses `codex login --device-auth`; the
browser callback is unsupported. Optional traffic (update checks, analytics,
feedback, OTEL export, connectors and remote plugins) is disabled with `-c`
overrides placed before the operator's arguments, which take precedence over
the agent-writable `config.toml`. Remote MCP servers in `config.toml` have no
disable control; the proxy denies them.

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

The same row appears in `claude-container/docs/network-contract.md`.

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Claude | Reference (`sandbox-ref-8`) | Mandatory bootstrap, multiplexed proxy and guided setup integrated | See the Claude validation record | Account login, reuse and refresh passed; real-key API unavailable |
| Codex | Ported from `sandbox-ref-8`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-09) | Pending operator device-code login, refresh and API-key checks; synthetic Responses API streaming and tool call passed |
| Antigravity | Pending (profile-based port planned) | Not assessed | Not assessed | Not assessed |
| OpenCode | Ported from `sandbox-ref-5`; shared files unchanged | Guard, multiplexed proxy, qualification and guided setup integrated | WSL ABI 3: all runtime modes and setup acceptance passed (2026-11-10) | Pending operator API-key checks for the four profiles; synthetic Chat Completions streaming and tool call passed |
| Pi | Pending (profile-based port planned) | Not assessed | Not assessed | Not assessed |

## Port status

| Item | Status |
| --- | --- |
| Shared copy, identifier scan and byte identity | Done (`tests/test_alignment.py`, `tests/test_reference_copy.py`) |
| Shared suites, guard, mux, policy, feasibility, qualification, setup | Passed in the runner; see [validation](validation.md) |
| Wrapper integration, restricted runtime and setup acceptance | Passed; see [validation](validation.md) |
| Authenticated OpenAI checks | Operator-run, pending |
