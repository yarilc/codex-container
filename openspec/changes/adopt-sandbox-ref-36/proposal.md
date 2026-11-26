# Proposal

## Why

Codex runs on `sandbox-ref-28`. Its container tests still need host Podman
delegation, which gives the session host engine authority and works only in
unrestricted mode. The reference is at `sandbox-ref-36`, and Claude adopted it
on 2026-11-26. The tag brings:
- the private session container engine, which restricted sessions can use too;
- image toolchains and catalog recipes;
- process limits set inside each container;
- runner tests that are portable to hosts without IPv6, a delegated `cpu`
  controller or terminal attach;
- systemd in nested containers;
- the engine's capability label.

Until Codex adopts the tag, every reference fix since `ref-28` misses it, and
the next tag would have to cross the same gap.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-36` from
  `sandbox-ref-28` in one step, skipping `ref-29` to `ref-35`. The 2026-11-26
  dry run gave this plan:
  - update 29 shared files under `launcher/`, `network/`, `setup/` and `tests/`;
  - add 17:
    - the eight `launcher/engine/` files;
    - `setup/engine.py`;
    - the six `setup/toolchain-catalog/` recipes;
    - `tests/guard_terminal_probe.py` and `tests/test_engine.py`;
  - rewrite one reference each in `README.md`, `AGENTS.md` and `docs/setup.md`;
  - rewrite 3 references in `docs/network-contract.md` and keep 8 as history;
  - move the manifest to commit `ce2c9d2`.

  The thin Windows entry and `.gitattributes` are unchanged.
- **BREAKING: host Podman delegation is removed**, as in the reference and
  Claude:
  - `CODEX_CONTAINER_PODMAN=1` stops every launch with migration guidance;
  - saved delegation stops the Windows bootstrap;
  - setup migrates saved preferences to schema 3, without the setting;
  - `CODEX_CONTAINER_PODMAN_SOCKET` is ignored.
- **Session container engine, from the shared files:**
  - **When:** a session gets a private rootless engine when the toolchain
    library holds an image.
  - **Endpoint:** the session reaches it at `CONTAINER_HOST` and
    `DOCKER_HOST=tcp://127.0.0.1:2375`.
  - **Image:** setup builds `localhost/codex-cli-engine`.
  - **Startup:** the engine starts through a step that delegates its own cgroup
    subtree, so systemd images boot in nested containers.
  - **Capabilities:** the image declares them in `io.containers.capabilities`.
- **Process limits, from the shared files.** Where the engine applies no cgroup
  limits, the first process of the agent, the proxy and the engine sets the
  process limit inside its container.
- **Codex's own tests:**
  - **Delegation cases:** the cases that delegated the host engine become
    refusal cases, or cases without delegation, in `tests/test_wrapper.py`,
    `test_runtime.py`, `test_network_runtime.py`, `test_setup_wrapper.py` and
    `test_setup_runtime.py`.
  - **Engine cases:** `test_runtime.py` takes the reference's
    `SessionEngineTests`. `test_network_runtime.py` takes the engine cases,
    with the engine inputs read from `engine.INPUTS`.
  - **Portability fixes of `ref-35`:**
    - the budget check follows the engine's controllers;
    - the terminal case skips where no terminal attaches;
    - the setup test uses a copied CA bundle and removes the engine, guard and
      proxy tags it created.
  - **Runner:** `tests/run-runtime.sh` no longer reads the delegation variable.
    Its `--shared` list gains the shared suites it lacked: `test_engine`,
    `test_toolchains`, `test_windows_bootstrap` and `test_windows_enter`.
- **Codex's documentation:**
  - `README.md`, `AGENTS.md` and `docs/setup.md` take the reference's engine,
    toolchain and migration text, with Codex's names;
  - the delegation sections go;
  - the parity row in `docs/network-contract.md` is updated.
- **Validation on one host,** WSL, with `tools/adoption-run.sh`. The tag
  touches every component, so every runner mode runs. The Windows validation
  script runs too, because `launcher/windows/` changed.

## Capabilities

### New Capabilities

- `session-container-engine`: the private per-session engine. Its 20
  requirements take the reference's text, with `CODEX_CONTAINER_TOOLCHAINS`:
  - when it starts, its endpoint, mounts, image store and storage;
  - its budgets, its delegated cgroup subtree, its startup step and its
    hardening exceptions;
  - systemd and explicit limits in nested containers;
  - its capability label, cleanup, qualification and documentation.

### Modified Capabilities

- `container-podman-access`: retired. Its delegation requirements are removed.
  The launch-engine requirements in it move to `container-session` without
  delegation:
  - the verified launch engine;
  - same-host Unix execution;
  - the verification response format and its documentation.
- `container-session`:
  - gains the moved requirements and the refusal of a leftover
    `CODEX_CONTAINER_PODMAN=1`;
  - drops delegation from the YOLO, network admission and engine query
    requirements.
- `container-isolation`:
  - no Podman socket in any session;
  - the capability rule is restated without delegation;
  - the read-only root, the secrets mask and the temporary storage rules hold
    with or without an engine;
  - the process rlimit fallback is set inside the container.
- `container-setup`:
  - drops the delegation choice and migrates saved delegation;
  - adds the engine image to preparation;
  - applies the saved worktree scope only to sessions;
  - re-verifies the toolchain library.
- `network-egress`:
  - engine containment replaces delegation rejection in the evidence;
  - the proxy's process rlimit fallback is set inside the proxy;
  - the runtime modes no longer name delegation.
- `toolchain-library`: catalog names, several sources, archive downloads,
  image entries and the read-only image store, image removal, recipes outside
  writable mounts and Windows paths.
- `windows-launcher`: the delegation refusal is the common migration refusal.
- `runtime-image`: restricted builds are gated by a leftover opt-in instead of
  enabled delegation.
- `shared-launcher`: Codex's approval-bypass combinations no longer include
  delegation.
- `workspace-mounts`: child bind mounts go through the session's engine.

## Impact

- **Shared files:** the dry run's 46 files. A defect in them pauses this change
  for a fix in `sandbox-container` under a new tag.
- **Codex's files:**
  - **Tests:** `tests/run-runtime.sh`, `test_wrapper.py`, `test_runtime.py`,
    `test_network_runtime.py`, `test_setup_wrapper.py` and
    `test_setup_runtime.py`.
  - **Documentation:** `README.md`, `AGENTS.md`, `docs/setup.md` and
    `docs/validation.md`.
  - **Parity:** the parity table in `docs/network-contract.md`. Codex's row is
    copied into the reference and the other four wrappers.
- **Operators:**
  - rerun `codex-container --container-setup` after updating. It builds the
    engine image and migrates saved delegation;
  - add the images that tests need with `--container-toolchain add`;
  - unset `CODEX_CONTAINER_PODMAN`.
- **Images:** a new `localhost/codex-cli-engine` image, from a digest-pinned
  `quay.io/podman/stable`. Codex's runtime image is unchanged: its build
  context (`Containerfile`, `network/relay.py` and `network/mux.py`) does not
  change.
- **Reference tool:** `propagate.py` runs `--shared` instead of the host unit
  tests, as if it were the unit discovery. In the four wrappers that offer it,
  it is a fixed list. This change completes Codex's list. A reference change
  should make the checklist name the changed modules that the list lacks,
  before Antigravity, OpenCode and Pi adopt.
