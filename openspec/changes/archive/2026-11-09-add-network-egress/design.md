# Design

## Context

See `proposal.md`. The reference is `claude-container` at tag `sandbox-ref-2` (merge `56a6f03`).

**Reference.** `network/` and the shared tests listed in its `tests/test_alignment.py` contain no agent identifiers; a scan for `codex` and `openai` finds none. Every agent value comes from `agent/profile.json`, through `network/agent_profile.py`. The Claude wrapper keeps the CLI, engine verification, image operations, state layout and agent container lifecycle. It calls `network/session.py` (`prepare`, `start`, `agent-args`, `stop`) for everything restricted.

**Current Codex wrapper.** `codex-container.sh` (466 lines) already has:
- the hardened baseline: no capabilities, no-new-privileges, verified budgets, workspace guard and optional lifetime;
- atomic naming, signal forwarding, bounded owned cleanup and same-host Unix engine verification.

It has no network modes, isolated state home, CA trust or maintenance gate, and it builds missing images automatically. Codex state is a private `CODEX_HOME` mounted at `/codex-home/.codex` below a `/codex-home` tmpfs that allows execution. `/tmp` and `/var/tmp` also allow execution.

**Coupling found during planning.** The split into two changes was moved for these reasons:
- `network/qualify.py` drives the wrapper with `<PREFIX>_STATE_DIR` per phase.
- `network/qualification_records.py` binds `<PREFIX>_TRUST_HOST_CA` and `<PREFIX>_CA_BUNDLE`.
- `network/control.py` verifies `setup/diagnostics.py` when it exists.
- The Claude wrapper runs `network/qualify.py check` before every restricted launch.

Copying `network/` unchanged therefore brings qualification (C08), the isolated state home and CA trust (C01) into this change.

## Goals / Non-Goals

**Goals:**
- `network/` and `setup/diagnostics.py` byte-identical to `sandbox-ref-2`, with Codex differences only in `agent/`, the wrapper, the image files and the per-agent tests.
- Restricted Codex sessions that behave like restricted Claude sessions, and an `unrestricted` mode that behaves like today's wrapper.
- Measured answers to the Codex-specific risks before the wrapper integration is written.

**Non-Goals:**
- Guided setup, the managed launcher, `setup.json`, the release rollback and the setup acknowledgement (all in `add-container-setup`).
- Changes to shared files. A defect found in `network/` is fixed in `claude-container` first and copied afterwards (Wave 4 rule).
- Release acceptance entries. `release_acceptance.json` stays empty.
- Authenticated provider checks in automated tests.

## Decisions

### Copy the reference tree from the tag, not from the working tree

`git -C ../claude-container archive sandbox-ref-2 network setup/diagnostics.py <shared tests>` provides the files, which are then unpacked. This excludes `__pycache__`, `network/bin` and any uncommitted Claude edits. `docs/network-contract.md` records the reference tag and commit.

Alternative: copy with `cp -r`. Rejected, because it can carry local bytecode or uncommitted edits.

### Temporary alignment check until setup arrives

Claude's `tests/test_alignment.py` requires the full shared test inventory, including `tests/test_setup.py`. That test drives `--container-setup` through the wrapper, which arrives only with `add-container-setup`. Both files are therefore deferred to that change. Until then, the per-agent test `tests/test_reference_copy.py` provides the alignment check:
- it holds the SHA-256 of every copied file at `sandbox-ref-2`;
- it fails on any difference, missing file or extra file in `network/`;
- it scans the copied files for the profile's identifiers;
- it runs `diff -r` when a sibling checkout at that tag exists.

`add-container-setup` replaces it with the unchanged `test_alignment.py`.

Alternative: copy `setup/` and the setup tests now. Rejected, because the setup tests would fail until the wrapper integration exists, or would pull the whole setup change into this one.

### Missing mode is an explicit-selection error until setup exists

Claude's message points to `--container-setup`, which does not exist in Codex yet. The wrapper therefore stops with a message naming `CODEX_CONTAINER_NETWORK`, its three values, and `unrestricted` as the previous behavior. `add-container-setup` replaces only that message. This follows the operator decision of 2026-11-09 and replaces the "default offline" decision of 2026-11-08.

### Follow the Claude wrapper order of checks

The check order is:
1. arguments;
2. mode and delegation;
3. budgets and lifetime;
4. engine verification;
5. restricted platform queries;
6. state;
7. CA;
8. `session.py prepare`;
9. image operations with the maintenance gate;
10. immutable image ID;
11. `qualify.py check`;
12. `session.py start` and `agent-args`;
13. owned create and start;
14. `session.py stop` within the remaining budget.

The existing Codex lifecycle code (naming loop, cid files, signal traps, bounded cleanup and exit-status preservation) stays. The restricted steps are inserted where the Claude wrapper places them, so later Claude changes can be ported by reading the diff.

### Codex agent profile

| Field | Value |
| --- | --- |
| `name` | `codex-container` |
| `env_prefix` | `CODEX_CONTAINER` |
| `label_namespace` | `io.codex-container` |
| `identifiers` | `codex`, `openai` |
| `images.agent` | `localhost/codex-cli` |
| `images.proxy` | `localhost/codex-egress` |
| `images.toolchain` | `localhost/codex-guard-toolchain` |
| `install.state_name` | `codex-egress` |

Native values:
- `home` is `/codex-home`, `command` is `codex` and `config_home` is `.codex`;
- `config_dir_env` is `CODEX_HOME` and `approval_bypass_env` is `CODEX_YOLO`;
- `shared_dirs` is empty, because Codex does not mount host OpenSpec configuration today.

Authentication methods:
- `api`: `openai-api`, hosts `api.openai.com`, `credential_env` set to `OPENAI_API_KEY`;
- `account`: `openai-account`, with the measured hosts and `login_args` for device-code login, if the installed CLI supports it.

The profile schema needs no extension. If Codex needs one, the extension is made in Claude first.

### OpenAI host inventory is measured, not assumed

Hosts come from three sources:
- the official Codex authentication documentation;
- a static inventory of URLs in the installed `@openai/codex` 0.167.0 package;
- denial records from operator-run sign-in, request and refresh in `provider` mode.

The policy revision is `openai-2026-11-09-v1`, with `tested.cli` set to `0.167.0`. Until the operator run, `tested.authentication` states that the authenticated checks are unverified. `chatgpt.com` and `auth.openai.com` are candidates, not commitments, and no wildcard is allowed.

### Optional traffic is disabled with protected command-line overrides

Codex accepts `-c key=value` overrides that take precedence over `config.toml`. In provider mode the wrapper inserts these overrides before the user's arguments for the settings supported by 0.167.0: update check, analytics, feedback, OTEL exporter and remote MCP or connectors. Equivalent environment variables are used where they exist. Settings without a control are documented, and the proxy denies the traffic anyway. Shell mode receives the same environment.

Alternative: write a managed `config.toml`. Rejected, because `CODEX_HOME` is agent-writable.

### Codex's own sandbox nested under the guard

The first implementation step measures whether Codex's sandbox works with no capabilities, no-new-privileges, the guard's seccomp filter and the AF_UNIX denial. The sandbox is Landlock and seccomp on Linux, or Bubblewrap, which needs unprivileged user namespaces. The outcome follows this order:
1. If it works, keep it as is.
2. If only Bubblewrap fails, select the Landlock path through a protected override.
3. If neither works, document the setting that disables the inner sandbox in restricted modes, with the guard remaining the enforced boundary.

The guard is never weakened. The result is recorded in `docs/validation.md`.

### Executable temporary storage stays

Codex needs executable `/tmp` and `/codex-home` (the Claude wrapper mounts `/tmp` noexec). The guard validates that the private `/tmp`, `/run` and `/var/tmp` hierarchies are not host binds, not that they are noexec. This is verified by the guard runtime tests on the Codex layout before integration. If a check fails, the finding goes back to Claude rather than the shared code being patched.

### Proxy and guard artifacts without setup

Before setup exists, the operator follows the procedure in `network/README.md` ("Operator build inputs"):
1. build the toolchain image;
2. run `network/build-guard.sh` into `network/bin` under `CODEX_CONTAINER_MAINTENANCE=1`;
3. build `localhost/codex-egress` from `network/Containerfile` and pass its immutable ID or digest as `CODEX_CONTAINER_EGRESS_IMAGE`.

`docs/validation.md` records the commands.

## Risks / Trade-offs

- **Every existing invocation breaks until a mode is set.** Mitigation: the error message names `unrestricted` as the previous behavior, and the README has a migration section. This trade-off was accepted by the operator.
- **The Rust client ignores proxy variables for some transport, for example WebSockets.** Mitigation: that traffic fails closed. The incompatibility is recorded and Codex's HTTPS fallback is verified. The allowlist is never broadened.
- **The Rust TLS stack does not use `SSL_CERT_FILE`.** Mitigation: verify with a controlled CA in the runtime tests. The CA contract is still mounted, and the gap is documented.
- **Account sign-in needs a host that cannot be measured without credentials.** Mitigation: ship `openai-account` as measured statically, label it unverified, and let the operator-run check revise it under a new revision.
- **A defect in a shared file shows up during the port.** Mitigation: stop, fix it in `claude-container` under its own change, and recopy. Codex never carries a fork.
- **Change size.** It is about 5,000 lines of copied code plus wrapper and test work. Mitigation: the tasks are ordered so that the copied components and their shared tests pass first, before the wrapper changes.

## Migration Plan

1. Users set `CODEX_CONTAINER_NETWORK=unrestricted` to keep today's behavior, and add `CODEX_CONTAINER_MAINTENANCE=1` to commands that build images.
2. Restricted use requires the operator build inputs, then `CODEX_CONTAINER_NETWORK=offline bash ./codex-container.sh --container-qualify`, then ordinary launches. Provider mode needs the same steps with the proxy image and `CODEX_CONTAINER_NETWORK_PROFILE`, `CODEX_CONTAINER_NETWORK_POLICY` and `CODEX_CONTAINER_NETWORK_RUNTIME_DIR`.
3. Rollback: check out the previous `main` merge. No persistent state format changes, and `CODEX_HOME` is untouched.

## Open Questions

- The exact `openai-account` host list and whether 0.167.0 supports device-code login. Both are measured in task group 2 and do not change the spec shape.
- The exact `-c` keys for optional traffic in 0.167.0. They are measured in task group 2.
