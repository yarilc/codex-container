# Proposal

## Why

Codex runs on `sandbox-ref-25`. Claude adopted `sandbox-ref-28` on
2026-11-22. The three tags since `sandbox-ref-25` bring:

- **`sandbox-ref-26`:** the budgets rule.
  - Only the `systemd` cgroup manager delegates controllers.
  - Without the `pids` controller, the process budget falls back to the
    process rlimit.
  - The shared launcher files pass ShellCheck.
- **`sandbox-ref-27`:** Windows support on a Podman machine.
  - The PowerShell entry, the shim, the bootstrap, the namespace helper and
    the installer.
  - Offline and provider networking in the machine, with the guard as the
    confined init of restricted sessions.
  - Setup changes for the machine, and API key variables forwarded from
    Windows.
- **`sandbox-ref-28`:** setup started from Windows names the login and API key
  steps for PowerShell.

Without these tags, Codex has two gaps:

- On a `cgroupfs` engine, which applies no budget, Codex reports the budgets
  as enforced.
- Codex cannot run from Windows.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-28` from
  `sandbox-ref-25`. The dry run of 2026-11-22 gave this plan:
  - update 22 shared files;
  - add 8: the `launcher/windows/` files and the Windows tests;
  - rewrite 11 tag references: 8 in `docs/network-contract.md`, 1 each in
    `README.md`, `AGENTS.md` and `docs/setup.md`;
  - move the manifest.
- **Files outside the copied directories,** handled as Claude handled them:
  - `codex-container.ps1`, the thin Windows entry, copied byte for byte from
    `sandbox-container.ps1`;
  - `.gitattributes`, followed by an LF renormalization.
- **Codex's agent part** (`agent/launcher.sh`) gets the reference's ShellCheck
  header. Without it, the lint requirement that arrives with the tag reports
  27 findings in that file.
- **Codex's own tests** change only where the shared changes alter what they
  check:
  - `tests/test_setup_wrapper.py` is identical to Claude's file before Claude's
    adoption. It takes Claude's adapted version: setup without a launch
    service, and the budget notices.
  - The budget checks of `tests/test_runtime.py` follow the engine's delegated
    controllers and process mechanism, as Claude's do.

  A failure caused by shared code pauses the change for a fix in the
  reference.
- **Codex's documentation** (`README.md`, `docs/setup.md`, `AGENTS.md`):
  - a Windows section adapted to Codex:
    - provider is the default;
    - the ChatGPT device-code login runs in the machine;
    - `$env:OPENAI_API_KEY` supplies the API key;
    - the installer;
    - host CA trust with `--import-native-ca`;
    - the Windows limits, including Bitdefender;
  - the process rlimit fallback and the `cgroupfs` budgets;
  - the guard as the confined init;
  - the setup changes.
- **Parity tables:**
  - Codex's row names `sandbox-ref-28`, with this adoption's results;
  - the reference and Claude rows match `sandbox-container`;
  - Codex's row is copied into the reference and the other wrappers.
- **Validation on Windows** with Codex, by the operator:
  - setup in provider mode with the account login;
  - a Codex session;
  - Codex's own sandbox in an unrestricted session;
  - `windows-validate -Checkout` on both PowerShell editions, including
    `-Install` and `-StopMachine`.

## Capabilities

### New Capabilities

- `windows-launcher`: the reference capability, copied as is. It runs Codex
  from PowerShell in a Podman machine's WSL distribution.
- `windows-installation`: the reference capability, copied as is. It installs
  the Windows entry for one Windows user.

### Modified Capabilities

- `container-isolation`:
  - budgets follow the controllers the engine delegates;
  - the process budget falls back to the process rlimit;
  - the documented hardening controls include that fallback.
- `container-session`: the budget notices name the reason or the rlimit
  mechanism, and the qualification identity includes the process budget
  mechanism.
- `container-setup`:
  - the questionnaire and saved budgets with the fallback;
  - recovery tags;
  - setup without a launch service;
  - carriage-return checks;
  - setup started by the Windows entry, with the PowerShell authentication
    steps;
  - the service endpoint proposed for restricted modes.
- `network-egress`: the proxy process budget falls back to the rlimit, and the
  guard runs restricted sessions as a confined init.
- `shared-launcher`:
  - ShellCheck;
  - the shared Windows shim and bootstrap;
  - the thin PowerShell entry;
  - LF line endings;
  - PSScriptAnalyzer;
  - the bootstrap tests.
- `workspace-mounts`: Windows system and profile folders are sensitive
  workspace roots.

## Impact

- **Code:** only these files change:
  - the shared files;
  - `codex-container.ps1` and `.gitattributes`;
  - the ShellCheck header of `agent/launcher.sh`;
  - the two adapted tests.
- **Installations:** the installed core, setup and guard change, so every
  Codex installation reruns `--container-setup`.
- **Behavior on Linux:**
  - On a `cgroupfs` engine, the launch notices state that the memory and CPU
    budgets are not enforced and that the process budget uses the rlimit.
  - Restricted sessions run under the guard as init, so Ctrl+C reaches Codex
    at once.
  - Codex's own sandbox stays off under the guard and on in unrestricted
    sessions.
- **Repositories:** the adoption is in `codex-container`. `sandbox-container`
  and the other wrappers get only the parity row.
- **Dependency:** `sandbox-ref-28` already exists. Claude's adoption gives the
  pattern.
