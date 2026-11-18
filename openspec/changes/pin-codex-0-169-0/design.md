## Context

`README.md`, section "Updating pinned image inputs", gives the procedure:
change the pins, rebuild, check the versions, rerun the credential-free suites
and `tests/run-runtime.sh`, then record the result.

The policy note records three measurements of 0.167.0:
- a static inventory (2026-11-09);
- the documentation MCP (2026-11-10);
- the command-sandbox behavior: Codex's Bubblewrap path needs a Netlink socket
  that the guard denies. This is why the wrapper runs provider sessions with
  `--no-daemon -c sandbox_mode="danger-full-access"`.

The release notes for 0.168.0 and 0.169.0 also contain:
- new opt-in TUI features;
- custom-provider onboarding;
- an opt-in Cloud connection;
- the `codex exec` trust change: project configuration and MCP servers stay
  disabled in untrusted directories, and `--trust` is new.

## Goals / Non-Goals

**Goals:**
- Pin 0.169.0 and OpenSpec 2.0.0 exactly. The image must report
  `codex-cli 0.169.0`.
- Repeat the static inventory and the documentation-MCP measurement with the
  method used on 0.167.0, and compare the results host by host.
- Re-confirm the controls the wrapper depends on:
  - `--no-daemon`;
  - `-c sandbox_mode=...`;
  - `--yolo`;
  - `--strict-config` rejecting unknown keys;
  - the Bubblewrap/Netlink behavior under the guard.

**Non-Goals:**
- Adopting the opt-in features that are new in 0.168 and 0.169 (Cloud
  connection, terminal workspace, custom gateways).
- Changing the base digest or any shared file.
- Real-account checks.

## Decisions

- **Same measurement methods as for 0.167.0.**
  - The results can be compared directly and need no credentials.
  - Alternative rejected: only `--version` plus the suites. That would leave
    `tested.cli` claiming an inventory that never ran.
- **The trust change is checked, not worked around.**
  - The wrapper never writes workspace configuration. The documented MCP setup
    is user-level, under `CODEX_HOME`.
  - The check runs `codex mcp list` in a disposable home after
    `codex mcp add openaiDeveloperDocs ...`, from an untrusted workspace, both
    in the default mode and under `codex exec`.
  - If the server no longer loads there, that is a lost behavior. Work pauses
    and the question goes to the user. The wrapper does not add `--trust` on
    its own.
- **Spec delta only when required hosts change.** If that happens, the policy
  gets a new revision `openai-2026-11-18-v1` and a `network-egress` delta,
  after the user agrees.

## Risks / Trade-offs

- [The Netlink requirement changes, and Codex's own sandbox now works or fails
  differently under the guard] → The existing network runtime test covers this
  path. If the result differs, the old-test gate classifies it.
- [A new host appears during startup, for example for the Cloud connection]
  → The static scan and a dummy-key logging-proxy run show it. Opt-in features
  stay off.
- [Rollback] → Revert the two pins and `tested.cli`, then rebuild.

## Migration Plan

1. The operator pushes `main`.
2. The operator reruns `--container-setup` on the three hosts.

Real-account checks follow in the deferred authenticated pass.
