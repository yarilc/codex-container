# Network policy contract

Status: ported by the `add-network-egress` change. Restricted modes are
implemented and verified with synthetic and real rootless runtime suites; the
authenticated OpenAI checks are operator-run and recorded separately in
[the validation record](validation.md). Guided setup and the managed launcher
follow in `add-container-setup`.

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md),
with [host-ca-trust](../openspec/specs/host-ca-trust/spec.md) and the session,
isolation, delegation and image specifications in `openspec/specs/`.

## Reference and intentional differences

The shared components are copied unchanged from `claude-container` at tag
`sandbox-ref-2` (commit `56a6f03216c49c78426fc7e9ced96c9fecc12685`):

- `network/` (except the build output `network/bin/`);
- `setup/diagnostics.py`;
- the shared tests listed in that tag's `tests/test_alignment.py`, except
  `test_alignment.py` and `test_setup.py`, which arrive with
  `add-container-setup`.

`tests/test_reference_copy.py` holds the SHA-256 of every copied file and fails
on a changed, missing or extra file, or on a profile identifier (`codex`,
`openai`) in a copied file. A defect in a shared file is fixed in
`claude-container` first and then copied; this repository never carries a
fork. [network/README.md](../network/README.md) is part of the copy and
describes the shared mechanism in agent-neutral terms.

Intentional differences are limited to per-agent files:

| File | Codex value or behavior |
| --- | --- |
| `agent/profile.json` | `codex-container`, prefix `CODEX_CONTAINER`, labels `io.codex-container.*`, images `localhost/codex-cli`, `localhost/codex-egress`, `localhost/codex-guard-toolchain`, home `/codex-home`, command `codex`, `CODEX_HOME`, `CODEX_YOLO`, no shared host directories |
| `agent/policies/default.json` | `openai-api` and `openai-account`, revision `openai-2026-11-09-v1` |
| `codex-container.sh` | Codex arguments, shared or isolated state layout, executable `/tmp`, `/var/tmp` and `/codex-home`, protected `-c` overrides, API key only for `openai-api`, missing-mode message without setup |
| `Containerfile`, `.containerignore` | Codex image; copies `network/relay.py` and `network/mux.py` |
| `tests/test_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py`, `run-runtime.sh`, `test_image_pins.py`, `test_reference_copy.py` | Codex names, synthetic Responses API fixture, OpenAI host inventories |

## Modes

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| unset or empty | Launch stops before engine calls and state creation | No session |
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

## Port status

| Item | Status |
| --- | --- |
| Shared copy and identifier scan | Done (`tests/test_reference_copy.py`) |
| Shared suites, guard, mux, policy, feasibility, qualification | Passed in the runner; see [validation](validation.md) |
| Wrapper integration and restricted runtime acceptance | Passed; see [validation](validation.md) |
| Authenticated OpenAI checks | Operator-run, pending |
| `test_alignment.py`, `test_setup.py`, guided setup, parity table | `add-container-setup` |
