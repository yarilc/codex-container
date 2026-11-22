# Design

## Context

Codex adopted `sandbox-ref-25` on 2026-11-18 and pinned Codex 0.169.0 the same
day. Its runtime and egress images are its own and stay as they are. The tag
changes no Codex build input.

**Dry run.** `tools/propagate.py ../codex-container sandbox-ref-25
sandbox-ref-28` (2026-11-22) gave this plan:

- **Update:**
  - `launcher/core.sh`;
  - `network/README.md`, `agent_budgets.py`, `control.py`, `guard.c`,
    `proxy_hardening.py`, `qualification_probe.py`,
    `qualification_records.py` and `session.py`;
  - `setup/common.py`, `launch.py`, `setup.py` and `smoke.py`;
  - `tests/fake_podman.py` and both fixture `launcher.sh`;
  - `tests/test_alignment.py`, `test_guard.py`, `test_launcher.py`,
    `test_qualification.py`, `test_session.py` and `test_setup.py`.
- **Add:**
  - the five `launcher/windows/` files;
  - `tests/test_windows_bootstrap.py` and `tests/test_windows_enter.py`;
  - `tests/windows/shim_tests.ps1`.
- **Rewrite:** 1 reference each in `README.md`, `AGENTS.md` and
  `docs/setup.md`, and 8 in `docs/network-contract.md`. The 8 include the
  "Adopted `sandbox-ref-25`" cells of the Antigravity, OpenCode and Pi rows.
- **Move:** the manifest to `ba1ef14`.
- **Runner modes listed:** `--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--guard` and `--network`.

**ShellCheck today.** `tools/shellcheck.sh ../codex-container` reports
findings in two groups:

- `launcher/core.sh` and both fixtures, which the tag replaces;
- `agent/launcher.sh`: 25 `SC2034`, 1 `SC2148` and 1 `SC2154`. Codex's agent
  part has no `shell=bash` directive.

**Codex's own tests.**
- `tests/test_setup_wrapper.py` is byte for byte the file Claude had before its
  adoption. Claude changed it for two shared behaviors:
  - the runner has no systemd user manager, so setup needs a fake
    `systemctl`;
  - setup without a launch service offers only unrestricted networking.

  Claude also took the reference version of the budget-notice test.
- In `tests/test_runtime.py`, `test_effective_hardening_and_budgets` asserts
  cgroup limits for all three budgets. It also starts 80 children under a
  process budget of 32. On the rlimit fallback, container startup tasks count
  toward the limit, and Claude raised it to 128 with 200 children.

**Codex specifics on Windows.**
- `native.command` is `codex`, so the reference's
  `tools/windows-validate.ps1` (fixed in `sandbox-ref-28`) runs its cases with
  `--container-shell`.
- The account method logs in with `codex login --device-auth`. From Windows,
  the setup's next step therefore reads
  `codex-container.ps1 login --device-auth`.
- The API method reads `OPENAI_API_KEY`, which the shim forwards.
- In `offline` and `provider`, Codex runs with `--no-daemon` and
  `sandbox_mode="danger-full-access"`, because its own sandbox cannot run under
  the guard. In `unrestricted`, Codex's own Bubblewrap sandbox works on Linux.
  Nobody has measured it in a Podman machine yet.
- Host CA trust sets `SSL_CERT_FILE`, which Codex reads.

**Images.** The runner's engine has no `localhost/codex-cli:latest` and no
`localhost/codex-guard-toolchain:development`. It has only
`setup-be4219e7…` tags, from 2026-11-18.

## Goals / Non-Goals

**Goals:**

- Codex runs on the `sandbox-ref-28` shared files. Beyond the ShellCheck header
  and the two adapted tests, no Codex-specific code changes.
- Codex works from Windows on a Podman machine:
  - in provider mode, with the device-code login and the installer;
  - in unrestricted mode, with its own sandbox, or with a documented limit.
- The parity tables of the reference and the five wrappers state the same rows.

**Non-Goals:**

- Antigravity, OpenCode and Pi, which adopt the tag in their own changes.
- Delegation on Windows and macOS.
- A real-key API check when no key is available.

## Decisions

1. **Adopt with the tool, from `sandbox-ref-25` directly.** Commit this change
   directory on `main`, then run the dry run and `--apply`. `--apply` creates
   `adopt-sandbox-ref-28`. This repeats Claude's adoption. Adopting
   `sandbox-ref-26` and `sandbox-ref-27` on their own adds runs and covers
   nothing more.
2. **Hand-copied files on the same branch.**
   - `sandbox-container.ps1` becomes `codex-container.ps1`, byte for byte.
   - `.gitattributes` is copied. Then, on a clean tree,
     `git rm -r -q --cached . && git reset --hard` rewrites the working files.
   - The shared alignment tests then check the entry, ASCII and line endings.
3. **Codex's agent part.** Add the reference header to `agent/launcher.sh`, as
   Claude did:
   - the comment that the core sources the file;
   - `# shellcheck shell=bash disable=SC2034,SC2154`.

   No hook changes. Disabling `SC2034` and `SC2154` matches the reference and
   Claude. Listing each variable or exporting the data instead would make
   Codex's header differ for no gain.
4. **Codex's own tests.**
   - `tests/test_setup_wrapper.py` takes Claude's current file byte for byte,
     because the two files matched before. Copying it keeps them comparable
     at the next adoption. Re-deriving the change would risk drift.
   - `tests/test_runtime.py` takes Claude's approach:
     - an `engine_budgets()` helper reads the delegated controllers and the
       process mechanism through `network/agent_budgets.py`, the launcher's
       rule;
     - the assertions follow that result;
     - the process-budget probe uses a budget of 128 and 200 children, and is
       skipped when no mechanism applies.
   - Any other failure caused by a shared behavior change is fixed in Codex's
     test on the same branch. A failure in shared code pauses the change for a
     reference fix and a new tag.
5. **Parity rows after `--apply`.**
   - The tool rewrites every `sandbox-ref-25` in `docs/network-contract.md`,
     including the rows of wrappers that stay on it.
   - After `--apply`, restore the Antigravity, OpenCode and Pi rows from
     `main`, and check that the reference and Claude rows equal
     `sandbox-container`'s.
   - Task 4.1 sets Codex's own row.
6. **Docs adapted, not copied.** The reference's and Claude's text for the
   shared behavior moves into Codex's own layout.
   - **`README.md`:**
     - a new `## Windows with Podman machine` section before
       `## Mounts and security`, with `### Trusting a host CA on Windows` and
       `### Install as a command`. It covers:
       - the provider default;
       - the device-code login, which setup runs in the machine and stores
         in the machine user's `~/.codex`, separate from any Codex on
         Windows;
       - `$env:OPENAI_API_KEY`;
       - `codex-container.ps1`;
       - the `CODEX_CONTAINER_*` variables;
       - the Windows limits, with Bitdefender;
       - the result of Windows step 4 for Codex's own sandbox;
     - in `### Session hardening, budgets and lifetime`:
       - the `systemd` and `cgroupfs` managers;
       - the process rlimit fallback;
       - the guard as the confined init;
       - the Windows sensitive folders.
   - **`docs/setup.md`:**
     - the Windows setup and the authentication steps from Windows;
     - setup without a launch service;
     - the carriage-return check;
     - candidate tags;
     - the service endpoint for restricted modes;
     - the budget plan.
   - **`AGENTS.md`:** `codex-container.ps1` and the Windows files among the
     shared and agent-specific files.
7. **Validation on this runner,** in Codex's checkout:
   - `python3 -m unittest tests.test_reference_copy tests.test_alignment` next
     to the `sandbox-container` checkout, with the sibling check not skipped;
   - the unit discovery in the disposable test container;
   - `bash tests/run-runtime.sh` in each of these modes:
     - `--wrapper`, `--shared`, `--setup` and `--setup-runtime`;
     - `--qualification`, `--guard` and `--network`;
     - the default runtime run;
   - from `sandbox-container`, `bash tools/shellcheck.sh ../codex-container`
     and `bash tools/powershell.sh ../codex-container`;
   - `git diff --check`.

   If no `latest` image exists, use the `setup-*` images whose
   `build-inputs-hash` matches the current inputs, through
   `CODEX_CONTAINER_IMAGE`. For `--guard`, tag the matching guard toolchain as
   `development` or pass `SANDBOX_GUARD_TOOLCHAIN`. Record both. If no image
   matches, rebuild with `CODEX_CONTAINER_MAINTENANCE=1 --container-build`.
8. **Validation on Windows.** The operator gets a bundle with snapshots of
   `codex-container` and `sandbox-container`, and these steps:
   1. `.\codex-container.ps1 --container-setup` with the defaults: provider
      networking and the account method. Decline the login and check the next
      step `codex-container.ps1 login --device-auth`. The first setup builds
      the Codex images in the machine.
   2. The login from a project folder:
      `codex-container.ps1 login --device-auth`. Open the URL in a Windows
      browser and enter the code.
   3. A Codex session from the project folder: one prompt that reads a file,
      then Ctrl+C. Note the exit status. `podman ps -a` must list no container
      of the session.
   4. Codex's own sandbox in an unrestricted launch:
      `$env:CODEX_CONTAINER_NETWORK = 'unrestricted'`, then a
      `--container-shell -c` call of `codex sandbox -- sh -c '…'`.
      - The command must run.
      - A workspace write must be denied, as `tests/test_runtime.py` checks
        on Linux.
   5. `sandbox-container\tools\windows-validate.ps1 -Checkout
      C:\Work\codex-container`:
      - on Windows PowerShell 5.1 with `-Install -StopMachine`;
      - on PowerShell 7 without them.
   6. The API method with `$env:OPENAI_API_KEY`:
      - with a real key, Codex answers one prompt;
      - without one, `--container-shell` shows that the variable reaches the
        session.

      Then setup again with the account method, so the machine ends as
      before.

   Each summary is copied after its run. If step 4 fails, the failure and its
   error are recorded and the change pauses. The decision is then between a
   documented Windows limit and a fix.
9. **Parity rows across repositories.**
   - Codex's row names "Adopted `sandbox-ref-28`", with this adoption's
     results.
   - After the merge, Codex's row is copied into `sandbox-container` and the
     four other wrappers, one commit on `main` each.
   - The rows of the wrappers still on `sandbox-ref-25` stay as they are.

## Risks / Trade-offs

- [Three tags at once widen the validation surface.] → Every runner mode that
  the tool lists runs, including `--guard`, plus `--wrapper` and the default
  runtime run.
- [Codex's own sandbox may not run in the machine's rootless engine, which
  uses `cgroupfs` and the WSL kernel.] → Windows step 4 measures it.
  Provider and offline sessions do not depend on it, because Codex runs
  without its sandbox under the guard.
- [The device-code login can need the ChatGPT setting that allows device
  codes.] → The README already sends the user to that flow. A login failure
  that the machine did not cause is recorded, not fixed here.
- [Installed qualification reports no longer match.] → After the merge, the
  operator reruns `--container-setup` on the Linux hosts and on Windows.
- [The tool rewrites rows of wrappers it does not adopt.] → Decision 5 restores
  them before the commit. Task 4.2 checks them in every repository.
- [Docs drift from Claude and the reference.] → The adapted sections follow
  Claude's structure, so a later adoption can compare them section by section.
