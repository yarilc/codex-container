# Tasks

## 1. Baseline and privilege dropping (B01)

- [x] 1.1 On the host, record a pre-change baseline with the current image: capability sets and `NoNewPrivs` from `/proc/self/status`, cgroup `memory.max`/`pids.max`/`cpu.max`, `codex --version`, Git, OpenSpec, a bubblewrap probe, Codex's own Linux sandbox running `true` (subcommand taken from `codex --help`), and delegated `podman info` plus a child container; verify the results are captured in working notes for `docs/validation.md`
- [x] 1.2 Add `--cap-drop=all` and `--security-opt=no-new-privileges` to the common `podman_args` for every mode (D3) and replace the help sentence about added privileges; verify a new `tests/test_wrapper.py` case finds both flags in the recorded `podman create` arguments for Codex, shell, YOLO and delegated launches

## 2. Resource budgets (B02)

- [x] 2.1 Add budget validation and normalization per D1/D2 right after option parsing, before `command -v podman`, and append `--memory`, `--cpus`, `--pids-limit` to `podman_args`; verify table-driven wrapper tests for defaults, overrides and every rejected form (status 1, variable named, no engine call)
- [x] 2.2 Add the post-create `podman inspect` budget check before `podman start` (D4) with bounded timeout and pending-signal handling; extend the fake engine to answer it (`FAKE_AGENT_BUDGETS`); verify wrapper tests for a matching, missing and different limit and for an inspection failure, each removing only the owned container and never starting it
- [x] 2.3 Add real-engine checks in `tests/test_runtime.py` for zero capabilities, `NoNewPrivs: 1`, default and overridden effective cgroup v2 limits (with and without delegation) and an enforced process limit; verify `bash tests/run-runtime.sh` passes on the host

## 3. Sensitive workspace roots (B03)

- [x] 3.1 Add the workspace guard per D6 after budget validation and before any engine or state operation, with the exact override and warning; verify wrapper tests for the physical home (fake `HOME`), the worktree parent equal to the home, a symlink to `/etc`, `/` and `/tmp`, `/mnt/d` refused and `/mnt/d/project` accepted, exact and non-exact override, and no engine call or state creation on refusal
- [x] 3.2 Confirm all wrapper and runtime fixtures use non-refused workspaces; verify both suites pass without the override

## 4. Session lifetime (B04)

- [x] 4.1 Add `CODEX_CONTAINER_RUN_TIMEOUT` validation, `--timeout N` for N ≥ 1 and the lifetime notice after the client exits (D5) without altering the status; verify wrapper tests for unset, empty, `0`, valid, negative, fractional and non-numeric values and for the notice with a fake non-zero exit after the limit
- [x] 4.2 Add a real-engine test with a short limit that checks expiry, the notice, a non-zero status and owned cleanup, plus an early exit with no notice; verify on the host and record the observed status

## 5. Pinned image inputs (B05)

- [x] 5.1 Resolve the current `@openai/codex` version on the host, pin `Containerfile` per D7 (base digest, `CODEX_VERSION`, `OPENSPEC_VERSION=1.16.0`, update-procedure comment), rebuild with `--container-build`; verify `codex --version` and `openspec --version` report the pinned versions
- [x] 5.2 Add `tests/test_image_pins.py` rejecting a base without digest, unpinned packages, `@latest` and version ranges; verify it passes and fails on a mutated copy

## 6. Codex sandbox and tools under hardening

- [x] 6.1 Add real-engine checks that Codex's own Linux sandbox runs a command, bubblewrap creates a sandbox, Git and OpenSpec work, and delegated `podman info` and a child container succeed in a hardened session, with no credentials or model request; verify on the host; if the Codex sandbox fails, record the limitation and a working Codex sandbox configuration without adding capabilities

## 7. Documentation and evidence

- [x] 7.1 Update `--container-help`, README ("Usage", "Mounts and security", "Included Tools") and `AGENTS.md` with the budgets, defaults and formats, the lifetime, the refused set and override, the capability drop in every mode, the storage-growth statement, the cgroup controller requirement and the pinned versions with the update procedure; verify a help test lists all five variables with defaults and `bash -n codex-container.sh` and `git diff --check` pass
- [x] 7.2 Run the full credential-free unit suite and `bash tests/run-runtime.sh` on the host, and add a dated `docs/validation.md` section with the 1.1 baseline comparison, results, initial failures and reruns, the observed lifetime status, the pinned versions and any documented limitation; verify `openspec validate harden-session-baseline --strict` passes
- [x] 7.3 Mark B01–B05 complete in `todo.md` with an implementation note; verify the note names the change and the evidence section

## Workflow follow-up

- Archive the change after review, then commit and merge when the user asks; the user pushes.
- Continue Wave 2 with `harden-session-baseline` in `antigravity-container`.
