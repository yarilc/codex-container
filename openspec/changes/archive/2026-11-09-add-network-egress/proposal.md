# Proposal

## Why

Every Codex session runs with unrestricted networking today. A prompt-injected agent, or any tool it runs, can therefore reach any host, the LAN and host services. `claude-container` at tag `sandbox-ref-2` implements N01–N14 and the review fixes N18–N24 in agent-neutral shared components (`network/`, `agent/profile.json`). This change ports that final state to Codex as the first of two consolidated Wave 3 changes. `add-container-setup` follows with guided setup and the managed launcher.

## What Changes

- **BREAKING** `CODEX_CONTAINER_NETWORK` selects `offline`, `provider` or `unrestricted`. An unset or empty mode stops ordinary launches before any engine call, with a message asking for an explicit mode. `add-container-setup` later replaces that message with `--container-setup` guidance. Unknown values fail before image operations. Restricted failures never fall back to unrestricted networking.
- **BREAKING** Image builds, including the automatic build of a missing image, require the exact `CODEX_CONTAINER_MAINTENANCE=1` in every mode. A provider proxy image is pulled only under the same authorization and only by digest.
- **BREAKING** `CODEX_CONTAINER_PODMAN=1` is rejected in `offline` and `provider` before image or resource operations. Delegation remains available only with explicit `unrestricted`.
- Copy `network/` unchanged from `claude-container` `sandbox-ref-2`. It contains:
  - the static Landlock ABI ≥ 3 and seccomp guard (`sandbox-egress-guard`);
  - the multiplexed relay and egress proxy, with initial and retried TLS ClientHello SNI binding (`tls-clienthello-sni-v2`);
  - protected policy and installation checks;
  - proxy hardening (no capabilities, 128 processes, 256 MiB);
  - platform eligibility, local qualification and its records;
  - the shared session helper (`prepare`, `start`, `agent-args`, `stop`).
  It also includes `setup/diagnostics.py`, which `network/control.py` verifies when present.
- Add `agent/profile.json`, the single source of Codex-specific values, and `agent/policies/default.json` with two exact OpenAI profiles:
  - `openai-api`, expected to be `api.openai.com:443`;
  - `openai-account`, for ChatGPT sign-in without a browser callback; its hosts must be measured from the installed Codex CLI.
  Both profiles are dated and versioned, with no wildcards.
- Add `--container-qualify` and require a current local qualification report before every ordinary `offline` or `provider` launch. The report is bound to the boot, engine, security policy, code, images, policy, profile, CA and hardening settings.
- Port the non-network prerequisites that qualification and restricted launches use:
  - `CODEX_CONTAINER_STATE_DIR` as an isolated `/codex-home`, conflicting with a nonempty host `CODEX_HOME`;
  - opt-in host CA trust (`CODEX_CONTAINER_TRUST_HOST_CA`, `CODEX_CONTAINER_CA_BUNDLE`);
  - an immutable runtime image ID for restricted launches.
- In provider sessions, disable Codex's optional traffic (update checks, analytics, feedback, OTEL export, remote MCP and connectors) through protected launch arguments or variables that the writable `config.toml` cannot override.
- Pass the API key only in `openai-api` sessions.
- The runtime image copies `network/relay.py` and `network/mux.py`, and `.containerignore` admits only these files besides `Containerfile`. The pinned Codex version must equal the policy's `tested.cli`.
- Port the shared tests, adapt the wrapper and runtime tests, and record real rootless evidence in `docs/validation.md`. The documentation covers:
  - the README and wrapper help;
  - `AGENTS.md`;
  - `docs/network-contract.md`;
  - `network/README.md`;
  - the residual exfiltration disclosure for the OpenAI hosts.

Out of scope, deferred to `add-container-setup`:
- `--container-setup`, `setup/` other than `diagnostics.py`, `setup.json` and the managed launcher;
- the setup acknowledgement of residual exfiltration;
- `docs/setup.md` and the missing-setup admission message;
- the final parity table in all five repositories.

## Capabilities

### New Capabilities

- `network-egress`: operator-selected network modes, the native IPC and network guard, the multiplexed egress proxy with exact destination and SNI binding, protected policies and agent profile, OpenAI authentication profiles, optional-traffic suppression, platform prerequisites, credential-free local qualification, owned proxy lifecycle, redacted diagnostics and documented limits.
- `host-ca-trust`: opt-in exposure of one host CA bundle, read-only at `/codex-home/ca/bundle.pem`, with the four standard CA variables.

### Modified Capabilities

- `container-session`: explicit network-mode admission, the required current local qualification for restricted launches, consistent restricted prerequisite decisions, and qualification binding of hardening settings.
- `container-isolation`: an isolated application home (`CODEX_CONTAINER_STATE_DIR`) beside the shared `CODEX_HOME` default, and private state checks for both.
- `container-podman-access`: socket delegation is accepted only in explicit unrestricted mode.
- `runtime-image`:
  - builds require exact maintenance authorization;
  - restricted launches use an immutable image ID;
  - the build context admits the relay and multiplex inputs;
  - the pinned CLI matches the policy's tested version.

## Impact

- **Code:**
  - `codex-container.sh` gains mode parsing, preflight, calls to `network/session.py`, `--container-qualify`, state and CA handling, and the maintenance gate. The restricted lifecycle stays in the shared helper.
  - New files: `network/` (copied unchanged), `setup/diagnostics.py`, `agent/`.
  - `Containerfile` and `.containerignore` change.
- **Tests:**
  - shared tests copied from Claude (`tests/test_alignment.py` list), except `test_alignment.py` and `test_setup.py`, which arrive with `add-container-setup`; until then a per-agent `tests/test_reference_copy.py` checks the copy against `sandbox-ref-2`;
  - adapted `test_wrapper.py`, `test_runtime.py`, `test_network_runtime.py`, `network_tls_fixture.py` and `run-runtime.sh` modes;
  - `test_image_pins.py` checks `tested.cli`.
- **Users:**
  - existing launches must set `CODEX_CONTAINER_NETWORK=unrestricted` to keep today's behavior;
  - first builds need `CODEX_CONTAINER_MAINTENANCE=1`;
  - restricted modes need host Python 3, a same-host rootless Podman ≥ 4.9 Unix service with Netavark, Landlock ABI ≥ 3 and a passing `--container-qualify`.
- **Compatibility risks, measured before porting code:**
  - Codex's own Linux sandbox (Landlock, seccomp or Bubblewrap) nested under the guard;
  - the Rust client honoring proxy variables for HTTPS, streaming and WebSockets;
  - the exact OpenAI account hosts and device-code login;
  - the executable `/tmp` and `/codex-home` that Codex needs, under the guard's mount-layout checks.
