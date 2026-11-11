# Proposal

## Why

claude-container tag `sandbox-ref-11` makes the sandbox work on a Rocky Linux 9
lab host (Podman 5, crun 1.27, partial cgroup delegation, `ipv6.disable=1`,
RHEL `/run/secrets` mount) and on a newer WSL host. The tag was validated on
both. Codex still uses `sandbox-ref-10` and its own launcher and recipe. On
such hosts it fails:

- it rejects the `unix://` socket path;
- it requests undelegated budgets;
- the guard refuses the RHEL secrets mount;
- the terminal cannot attach;
- the image build needs outbound port 80.

## What Changes

- **Adopt `sandbox-ref-11`** with `tools/propagate.py`: the shared `network/`,
  `setup/` and shared tests, the reference manifest and the current-state
  documents. This brings, unchanged:
  - controller-dependent budgets in qualification, smoke and proxy;
  - IPv6-less qualification;
  - the guard's read-only `/run/secrets` acceptance;
  - the proxy address-family fallback;
  - the setup socket and CA build-secret handling.
- **Launcher (`codex-container.sh`)**, ported from the Claude launcher:
  - strip the `unix://` prefix from the reported host socket path;
  - request each budget only when the engine reports its cgroup controller.
    Announce each unenforced budget, and at inspection require enforced
    budgets to match and unenforced ones to be absent;
  - mask `/run/secrets` with an empty read-only tmpfs;
  - stop disabling automatic read-only tmpfs. Mount a `noexec` `/dev`
    tmpfs, `devpts` and an empty read-only `/dev/shm`;
  - pass the selected host CA to `--container-build` and to automatic
    builds as the `build-ca` secret.
- **Runtime image recipe**:
  - fetch Debian packages only over verified HTTPS, bootstrapped from the
    base image's Node.js roots plus the optional `build-ca` secret;
  - `.containerignore` admits `podman-build-secret*`;
  - the pin tests reject plain-HTTP sources and disabled verification.
- **Wrapper tests**:
  - fixtures for the shared-code imports and the controller query;
  - assertions for the new mounts, budgets, socket and build secret.
- **BREAKING (policy):**
  - a budget whose controller is not delegated is not enforced;
  - `/dev` becomes a writable `noexec` tmpfs.
- **BREAKING (installation):** the qualification identity, code digests and
  runtime image identity change. Restricted installations must rebuild and
  rerun setup.
- **Unchanged:**
  - `/tmp` and `/var/tmp` keep `exec` and their 512 MiB sizes, and `/run`
    keeps its 32 MiB size and mode;
  - budget values and validation;
  - the provider policy and profiles;
  - the guard's `/run/secrets` rule, kept exactly as in the reference.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`:
  - budgets are enforced per delegated controller and verified as enforced
    or absent;
  - the secrets mask;
  - terminal-compatible device mounts.
- `container-session`:
  - the qualification identity binds the enforced budget sets;
  - unenforced budgets are announced.
- `container-podman-access`: accepts a `unix://` host socket report.
- `container-setup`:
  - smoke and plan follow the enforced set;
  - the host CA covers the setup package fetches.
- `network-egress`:
  - proxy budgets per delegated controller;
  - IPv6-less qualification;
  - the bootstrap admits only the read-only secrets mask;
  - the proxy skips unsupported address families.
- `runtime-image`: HTTPS package sources and the pinned trust bootstrap.

## Impact

- Shared files from the tag, through the tool: 21 files in `network/`,
  `setup/` and `tests/`, plus `tests/test_reference_copy.py`, `README.md`,
  `AGENTS.md`, `docs/setup.md` and `docs/network-contract.md`.
- Codex-owned files:
  - `codex-container.sh`, `Containerfile`, `.containerignore`;
  - `tests/test_wrapper.py`, `tests/test_image_pins.py`, `tests/test_runtime.py`;
  - `README.md`, `AGENTS.md`, `docs/validation.md`.
- Existing Codex installations must rebuild and rerun setup or qualification.
- OpenCode, Pi and Antigravity are not affected. They adopt the tag in their
  own changes.
