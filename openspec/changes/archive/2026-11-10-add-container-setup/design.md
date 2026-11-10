# Design

## Context

See `proposal.md`. The reference is still `claude-container` at tag `sandbox-ref-2` (commit `56a6f03216c49c78426fc7e9ced96c9fecc12685`). `add-network-egress` (merged as `35cbf32`) already copied `network/`, `setup/diagnostics.py` and the shared tests except `test_setup.py` and `test_alignment.py`. It also integrated the restricted modes into `codex-container.sh`.

**Observed in the reference.**
- `setup/` (1,330 lines) takes every agent value from `agent/profile.json`:
  - wrapper name, prefix, images and labels;
  - `config_dir_env` (`CODEX_HOME`), `config_home` (`.codex`), `shared_dirs` (empty here) and `approval_bypass_env` (`CODEX_YOLO`);
  - authentication methods with `login_args` (`login --device-auth`) or `credential_env` (`OPENAI_API_KEY`).
- Setup drives the wrapper. It uses `--container-qualify`, `--container-shell` for the smoke check, the login arguments in ordinary mode, and `--container-git-worktree`.
- The managed dispatcher calls `setup/launch.py`. That script validates the protected `setup.json`, exports the saved variables and execs the installed wrapper.
- Shared `tests/test_setup.py` (1,268 lines) runs the real wrapper for `--container-setup` admission and help precedence, and checks the `setup required:` message (also for `--container-qualify-probe` without a mode). It also checks managed launches with saved modes and empty overrides, and the `setup/diagnostics.py` stderr filter.
- Shared `tests/test_alignment.py` scans `network/`, `setup/` and the shared tests for profile identifiers. It also checks the wrapper:
  - every profile variable is used;
  - the session label, agent image, home and command appear;
  - the four `session.py` calls use the `"${session_helper[@]}" <operation>` form;
  - there is no inline restricted lifecycle;
  - the image and wrapper use neutral in-container paths.

**Observed in Codex.**
- `codex-container.sh` already satisfies the alignment patterns (`"${session_helper[@]}" prepare|start|agent-args|stop`, `io.codex-container.session`, `localhost/codex-cli`, `/codex-home`, `codex`) and has no inline lifecycle strings.
- It does not yet:
  - accept `--container-setup`;
  - print `setup required:`;
  - pipe stderr through `setup/diagnostics.py`. Codex sessions on Podman 4.3 clients show `level=error msg="Should restart: false"`.
- `add-network-egress` measured that Codex's own sandbox cannot start under the guard. The Bubblewrap path fails because Netlink is denied. The Landlock-only path refuses to run with "requires bubblewrap". Restricted Codex commands therefore fail unless the inner sandbox is disabled.

## Goals / Non-Goals

**Goals:**
- `network/`, `setup/` and every shared test byte-identical to `sandbox-ref-2`. Unchanged `test_alignment.py` and `test_setup.py` pass against the Codex wrapper.
- Guided setup produces a working managed launcher for all three modes, with qualification and the smoke check passing on the WSL target.
- Restricted Codex sessions run shell commands by default, with the guard as the enforced boundary.
- The parity table records the Codex row in both this repository and `claude-container`.

**Non-Goals:**
- Authenticated OpenAI verification. It stays operator-run.
- Enabling real systemd user services in tests. They are recorded as unavailable unless the operator runs them.
- Ports for OpenCode, Pi and Antigravity, and their parity rows.
- Any change to shared files. A defect is fixed in `claude-container` first and then copied.

## Decisions

### Copy the remaining setup files and tests from the tag

`git -C ../claude-container archive sandbox-ref-2 setup tests/test_setup.py tests/test_alignment.py` provides the files, unpacked over the checkout. `setup/diagnostics.py` is already identical. `tests/test_reference_copy.py` keeps its SHA-256 manifest and gains the new entries. `test_alignment.py` checks identifiers and wrapper consistency, while the manifest checks byte identity against the tag. They are complementary, so both stay.

Alternative: drop `test_reference_copy.py` as planned in `add-network-egress`. Rejected, because `test_alignment.py` cannot detect a non-identifier edit to a shared file.

### Wrapper entry points follow the Claude wrapper exactly

- `--container-setup` is handled after help and qualification, as in Claude. It must be used alone and needs a terminal on stdin and stdout and host Python 3, then it `exec`s `setup/setup.py`.
- The missing-mode message becomes the Claude form: `setup required: run bash <wrapper> --container-setup; use the managed launcher afterward or explicitly set CODEX_CONTAINER_NETWORK for an operator workflow`. The wrapper path is absolute and quoted with `printf %q`.
- When `setup/diagnostics.py` and host Python exist, the attached client's stderr goes through the filter on a FIFO. The FIFO lives in the private session directory.

The diagnostics FIFO adds a second background child. The Codex lifecycle (`record_signal`, `cleanup`, `reap_client`) reaps it after the client, with the one-second drain bound that the Claude wrapper uses. Only the `podman start` invocation changes, so the existing signal and status tests keep covering the client.

### Protected sandbox override in restricted modes

In `offline` and `provider`, the Codex application command becomes:

```
/usr/local/bin/codex -c 'sandbox_mode="danger-full-access"' [provider overrides] [--yolo] <user arguments>
```

`-c` takes precedence over the agent-writable `config.toml`, as measured in `add-network-egress`. A later operator `--sandbox` or `-c sandbox_mode` wins as an explicit choice. A sandbox selected that way fails closed under the guard. Shell mode gets no override, because no Codex process is started. `unrestricted` gets none either, so Codex's sandbox keeps working there.

Before writing the wrapper code, the implementation verifies the key name and value in 0.167.0 with `--strict-config`. It checks the effective policy through `codex exec` against the synthetic Responses API: the startup banner reports `sandbox: danger-full-access`. Approval prompts are unchanged; `--yolo` still controls them.

Alternatives considered:
- A setup question for YOLO, which leaves direct launches broken;
- documentation only. That is the current state, and commands fail by default.

The operator chose the protected override on 2026-11-09.

### Parity table placement

`docs/network-contract.md` here gets the five-wrapper table copied from Claude, with the Codex row filled in:
- contract adoption: ported from `sandbox-ref-2`;
- implementation: integrated;
- real enforcement: the runtime modes of the validation record;
- authentication: pending operator checks.

The same row replaces "Pending (profile-based port planned)" in `claude-container/docs/network-contract.md`. That edit is documentation-only and is committed separately in that repository when the user requests commit and merge. It is not a shared file, so the no-fork rule does not apply.

### Setup runtime acceptance

`tests/test_setup_runtime.py` is ported from Claude with Codex names. It runs setup under a pseudo-terminal against the real same-host service, with:
- disposable `HOME`, installation and command paths;
- a disposable proxy image;
- prepared runtime images routed by tag lookups, so no operator-owned image is retagged.

It covers offline, provider and unrestricted installation and runs the managed launcher from another workspace. It does not enable systemd services, read real credentials or send model requests. `tests/run-runtime.sh` gains the `--setup` mode (shared `test_setup.py`) and the `--setup-runtime` mode.

## Risks / Trade-offs

- **A shared setup test assumes Claude-only wrapper behavior.** Mitigation: run `test_setup.py` early (task group 2). A failure caused by shared code is fixed in `claude-container` first; a failure caused by the Codex wrapper is fixed in the wrapper.
- **Disabling Codex's sandbox removes a defense layer inside the container.** Mitigation: the guard (Landlock, seccomp, no Unix sockets, no capabilities), the read-only root and the network mode remain. The README states the trade-off, and `unrestricted` keeps the inner sandbox.
- **Device-code login must be enabled per ChatGPT account or workspace.** Mitigation: setup reports authentication pending with that prerequisite and the API-key alternative.
- **The diagnostics FIFO changes stderr buffering of the attached client.** Mitigation: the Claude design is already measured. The Codex TTY, pipe and signal tests are rerun, and the filter forwards interactive prompts without waiting for a newline.

## Migration Plan

1. New users run `bash ./codex-container.sh --container-setup`, then use `~/.local/bin/codex-container`.
2. Existing direct invocations keep working with an explicit `CODEX_CONTAINER_NETWORK`. Without one they get the setup-required message instead of the variable-only message.
3. Restricted sessions no longer need `--sandbox danger-full-access` from the user.
4. Rollback: setup keeps the last working release and restores it on failed activation. At the repository level, check out the previous `main` merge (`35cbf32`).

## Open Questions

None. The `sandbox_mode` key is verified in task 3.1 before use.
