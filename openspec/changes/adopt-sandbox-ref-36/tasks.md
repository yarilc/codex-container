# Tasks

## 1. Adopt `sandbox-ref-36`

- [x] 1.1 Copy the tag's shared files with `tools/propagate.py` (design decision 1).
  - **Before:** check that `sandbox-ref-36` exists in `sandbox-container`, then commit this change directory on `main`.
  - **Copy:** from `sandbox-container`, run `python3 -I tools/propagate.py ../codex-container sandbox-ref-28 sandbox-ref-36` (dry run), then `--apply`.
  - **Verify:**
    - the plan lists the files in proposal "What Changes", with `docs/network-contract.md (3, 8 kept)` and the 19 review lines;
    - the tool switched to `adopt-sandbox-ref-36`;
    - `codex-container.ps1` and `.gitattributes` need no copy;
    - `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes.

## 2. Codex's tests, runner, documentation and specs

- [x] 2.1 Rewrite the delegation cases of `tests/test_wrapper.py` (design decision 2).
  - **YOLO grid:** `test_yolo_case_insensitive_and_delegation_independent` becomes `test_yolo_case_insensitive_and_no_socket`. It runs shell × YOLO value, keeps the argument checks and checks that no argument names `podman.sock`.
  - **Opt-in grid:** `test_permissions_independent_and_exact_opt_in` becomes `test_permissions_and_hardening_independent_of_yolo`. It varies only `CODEX_YOLO`, and keeps the bypass, hardening and no-socket checks. The refusal of a leftover `CODEX_CONTAINER_PODMAN=1`, and the other values being ignored, are launcher behavior: the shared `tests/test_launcher.py` covers them, and spec `shared-launcher` keeps them out of `test_wrapper.py`.
  - **Help:** the help case checks "Host Podman delegation was removed: CODEX_CONTAINER_PODMAN=1 stops startup.".
  - **Removed:** the `AF_UNIX` fixture, `CODEX_CONTAINER_PODMAN_SOCKET`, `import socket`, and `CODEX_CONTAINER_PODMAN` in the restricted environment. The `RestrictedTests` overrides follow the new names.
  - **Verify:**
    - `grep -n "PODMAN_SOCKET\|AF_UNIX\|import socket\|podman/podman.sock' in" tests/test_wrapper.py` finds nothing;
    - `python3 -m unittest tests.test_wrapper` passes here, or fails only as on `main` (task 2.8). Here the help case passes, with the migration line, and the other cases stop at the private state check on drvfs;
    - the `--wrapper` entry of task 3.1 passes.
- [x] 2.2 Rewrite the delegation cases of `tests/test_runtime.py` and add the engine cases (design decision 2).
  - **Setup:** `CODEX_CONTAINER_PODMAN='0'` and the socket selection leave `setUp`.
  - **Refusal:** the image environment case checks the cleared defaults without a socket, then the refusal of `CODEX_CONTAINER_PODMAN=1`, in both state modes.
  - **Delegated variants:**
    - `test_effective_hardening_and_budgets` drops its `service` loop;
    - `test_tools_and_codex_sandbox_without_capabilities` drops the delegated child;
    - `test_child_container_host_bind` is removed.
  - **Containerized caller:** `test_containerized_caller_with_remapped_socket` keeps its remapped launch socket. It drops `CODEX_CONTAINER_PODMAN=1`, and its script checks `test ! -S /run/podman/podman.sock` before writing the nested file.
  - **Engine cases:**
    - add Claude's `engine_budgets()` and `start_crowd()` helpers and `test_process_rlimit_counts_per_container`;
    - add the `SessionEngineTests` class, with the reference's four cases without the systemd ones: `test_session_engine_runs_library_images_inside_the_session_boundaries`, `test_engine_process_rlimit_counts_per_container`, `test_no_engine_without_library_images` and `test_live_image_and_isolated_concurrent_sessions`;
    - use `ENGINE_IMAGE = localhost/codex-cli-engine:latest` and the pinned alpine `SAMPLE`.
  - **Verify:**
    - `grep -n "CODEX_CONTAINER_PODMAN" tests/test_runtime.py` finds only the refusal case;
    - the module parses, and its classes skip without `SANDBOX_RUNTIME_TESTS`;
    - the default runtime entry of task 3.1 passes.
- [x] 2.3 Rewrite the delegation cases of `tests/test_network_runtime.py` and add the engine and `ref-35` cases (design decisions 2 and 3).
  - **Installation:**
    - put `setup/` on `sys.path` and `import engine`;
    - copy `setup/engine.py` and `*engine.INPUTS` beside the other names, in place of the hand-written list at lines 58-59;
    - add the reference's `engine_profile()` and copy the engine's seccomp profile when the engine image exists.
  - **Refusal cases:**
    - `test_restricted_delegation_grid_and_disabled_override` becomes `test_leftover_delegation_opt_in_and_other_values`;
    - `test_offline_defaults_and_delegation_rejection` becomes `test_offline_defaults_and_leftover_delegation_refusal`;
    - both check "CODEX_CONTAINER_PODMAN=1: host Podman delegation was removed".
  - **Engine cases:** `test_offline_session_engine_has_no_external_path`, `test_image_recipe_check_runs_without_network` and `test_proxy_starts_beside_containers_holding_more_than_its_budget`, with `remove_toolchain_on_cleanup()`, from Claude with Codex's names.
  - **`ref-35` budget rule:** `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy` checks each budget with `engine_budgets()`. A delegated controller holds its budget, and an undelegated one reads `max` or is absent. On `rlimit`, `/proc/self/limits` holds the process budget.
  - **`ref-35` terminal case:** the terminal case of `test_guarded_arguments_stdin_status_and_tty_both_state_modes` runs in `subTest(terminal=True, isolated=…)`, skipping with `terminal_skip_reason(IMAGE)`.
  - **Interrupted creation:** in `test_interrupted_and_failed_creation_recovers_both_roles`:
    - the wait for the intercepted `create` is 60 s;
    - `before` and `after` get 90 s to exit;
    - after `terminate()`, the interrupt phase still gets 25 s;
    - a launch that times out is killed before the subtest fails.
  - **Verify:**
    - `grep -n "launcher/engine/" tests/test_network_runtime.py` finds no build input;
    - `grep -n "PODMAN_SOCKET\|rejects CODEX_CONTAINER_PODMAN" tests/test_network_runtime.py` finds only the check that the old socket override is ignored;
    - the module parses;
    - the `--network` entry of task 3.1 passes.
- [x] 2.4 Remove the delegation question from `tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`, and port the `ref-35` and `ref-34` setup fixes (design decision 2).
  - **Both files:** the answers drop `('Delegate the host Podman API', 'no')`. `test_setup_wrapper.py` drops `'podman: False'` from the expected summary.
  - **`test_setup_runtime.py`:**
    - **CA case:** it copies `/etc/ssl/certs/ca-certificates.crt` to `self.base / 'ca-bundle.pem'` and answers with that path.
    - **Tags:** `clean_tags` adds `REAL_PROFILE.image(kind, 'setup-' + release)` for `engine`, `toolchain` and `proxy`.
    - **Proxy shim:** it routes only `{{.Id}}` lookups of the egress image.
  - **Verify:**
    - `grep -n "Delegate the host Podman API" tests/test_setup_*.py` finds only the `assertNotIn` check;
    - the `--setup` and `--setup-runtime` entries of task 3.1 pass, with equal image tags before and after `--setup-runtime`, apart from the rebuilt engine image;
    - `tests.test_setup_wrapper` passes on the WSL host (task 3.1). No runner mode runs it, and here it stops at the protected-path check on drvfs.
- [x] 2.5 Update `tests/run-runtime.sh` (design decision 4).
  - **Socket:** drop `CODEX_CONTAINER_PODMAN_SOCKET`. The socket comes from a Unix `CONTAINER_HOST`, else from `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock`.
  - **`--shared` list:** add `test_engine`, `test_toolchains`, `test_windows_bootstrap` and `test_windows_enter`.
  - **Verify:**
    - `bash -n tests/run-runtime.sh` passes;
    - a one-line check lists the shared `tests/test_*.py` of `SHARED_TESTS` in `tests/test_alignment.py`, without `test_setup.py`, and they equal the `--shared` list;
    - the dry run still prints `--shared` first;
    - the `shared` entry of task 3.1 runs those modules.
- [x] 2.6 Adapt `README.md`, `AGENTS.md` and `docs/setup.md` to the tag, with Codex's names (design decision 6).
  - **`README.md`:**
    - **Introduction:** sessions never receive the host Podman API.
    - **Launch service:** "Optional host Podman API access" becomes "Enable the launch service", with "Verify the launch service". The delegation socket selection goes.
    - **"Container tests" (new section):** from Claude's, which the core's refusal names. It covers the engine, image toolchains, the host `/sys` view and the migration.
    - **Removed:** the delegation examples, the YOLO × Podman table and the delegation column.
    - **Toolchains:** catalog names, image entries and Windows paths.
    - **Engine items:** the budgets, the hardening exceptions with the startup step and the label, "Systemd containers and nested limits" and the read-only `/sys`.
    - **Security statements:** they drop the socket.
    - **Runner section:** it drops the delegation socket.
  - **`AGENTS.md`:**
    - the delegation rules become the engine rules;
    - the shared test list at line 39 gains `test_engine.py`, `test_toolchains.py`, `test_windows_bootstrap.py`, `test_windows_enter.py` and `guard_terminal_probe.py`;
    - add the reference's terminal check paragraph, with Codex's names.
  - **`docs/setup.md`:** no delegation question, schema 3 preferences and the engine image.
  - **Verify:**
    - `grep -n "PODMAN_SOCKET\|PODMAN=1\|[Dd]elegat" README.md AGENTS.md docs/setup.md` finds only the migration refusal and cgroup controller delegation;
    - `grep -n "^### Container tests" README.md` finds the section;
    - no `SANDBOX_CONTAINER_` or Claude name appears in the new text;
    - `git diff --check` passes.
- [x] 2.7 Check the main specs that the archive will produce (design, Risks).
  - **How:** in a scratch copy of the checkout outside the repositories, run `openspec archive adopt-sandbox-ref-36 --yes`.
  - **Verify:**
    - `openspec/specs/container-podman-access/` is gone, and `session-container-engine` has 20 requirements;
    - `grep -rn "PODMAN_SOCKET\|PODMAN=1\|[Dd]elegat" openspec/specs` finds only the migration and refusal requirements and cgroup controller delegation;
    - every warning that `openspec validate --specs --strict` adds to those of `main` is a requirement whose text, taken from the reference, is also over 500 characters there. On 2026-11-26 there were 8: "Fixed engine hardening exceptions", "Mode-specific image and guard preparation", "Persistent non-secret managed launch preferences", "Proxy process budget falls back to the process rlimit", and four `toolchain-library` requirements ("Relocatable toolchains from pinned sources", "Self-describing library for the agent", "Toolchain command on the host" and "Verified against the runtime image").

    Remove the scratch copy afterwards.
- [x] 2.8 Run the repository checks here, then commit the adoption on `adopt-sandbox-ref-36`, without merging.
  - **Unit checks:** `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_engine tests.test_toolchains tests.test_image_pins tests.test_wrapper tests.test_setup_wrapper`, with `SANDBOX_TEST_TMPDIR` on executable storage when `/tmp` is `noexec`.
  - **Other checks:**
    - `python3 -c "import ast,sys; [ast.parse(open(p).read()) for p in sys.argv[1:]]"` on the changed test modules;
    - `bash -n tests/run-runtime.sh`;
    - `openspec validate adopt-sandbox-ref-36 --strict`;
    - `git diff --check`.
  - **Verify:**
    - every failure is one this environment also gives on `main`, from storage without `chmod` (drvfs, mode 777) or refused `AF_UNIX` sockets. A test new in the tag may fail only at the same point;
    - the runtime suites skip without an engine;
    - the validation reports only "Fixed engine hardening exceptions".

## 3. Development validation on WSL

- [ ] 3.1 Have the operator run the adoption runner on WSL (design decision 7).
  - **Preparation:**
    - in the native clones, `sandbox-container` is on `main` and `codex-container` is on `adopt-sandbox-ref-36`;
    - `localhost/codex-cli:latest` and `localhost/codex-guard-toolchain:development` exist;
    - pull `docker.io/library/alpine@sha256:c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e`.
  - **Command:** from `sandbox-container`, run `bash tools/adoption-run.sh ../codex-container sandbox-ref-28 sandbox-ref-36`.
  - **Codex's own module without a runner mode:** from `codex-container`, run `python3 -m unittest tests.test_setup_wrapper -v` on the host's Python, with `SANDBOX_TEST_TMPDIR` on a new private directory under the home, to its own full log. `--setup` runs only the shared `test_setup.py`, and the checklist does not name this module.
  - **Expected:**
    - the preflight passes;
    - the engine image label reads `SETUID,SETGID,SYS_CHROOT,CHOWN`;
    - every entry passes, and no skip is `NOT PREPARED`;
    - the only skips are these:
      - the rlimit cases, `test_process_rlimit_counts_per_container`, `test_engine_process_rlimit_counts_per_container` and the proxy's, with "the engine does not use the process rlimit fallback";
      - the opt-in cases: the idle check of `--guard` and `test_real_documentation_mcp_through_the_production_proxy`;
    - both terminal cases run;
    - the setup-runtime tags are equal;
    - `tests.test_setup_wrapper` passes.

  Analyse the archive in a new empty directory. A failure in shared code pauses the change for a fix in `sandbox-container` under a new tag. A Codex-only failure is fixed on the branch, and only its entries are rerun with `--only`, into a new archive.

## 4. Record, merge and parity

- [ ] 4.1 Record the adoption and merge it.
  - **Record:** add the `sandbox-ref-36` adoption section to `docs/validation.md`, from the tool's template, with:
    - every result of tasks 2.8 and 3.1;
    - the engine label and the expected skips;
    - the checks not run, with the reference's `ref-36` runs as their evidence: Rocky, the systemd and cgroup delegation cases, and the runner inside a session;
    - the release risk (design decision 7): the Windows entry was not run against a real Podman machine. Its smoke test, after the release, is `.\tools\windows-validate.ps1 -Checkout <the Windows checkout>` from `sandbox-container`, on Windows PowerShell 5.1, with the updated installation. It should report no failed case, the refusal of saved delegation by the bootstrap, and a passing "Session with library images". A defect it finds gets its own change.
  - **Parity:**
    - Codex's implementation cell names the session container engine for image toolchains, with systemd in nested containers;
    - its real enforcement cell gains the WSL `sandbox-ref-36` entry;
    - copy the reference row from `sandbox-container`.
  - **Merge:** commit with the tool's message and the co-author trailer, then merge into `main`.
  - **Verify:** `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes on `main`.
- [ ] 4.2 Copy Codex's parity row into `sandbox-container`, `claude-container`, `antigravity-container`, `opencode-container` and `pi-container`, one commit on `main` each.

  Verify: the reference and Codex rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` and the adoption branch in every touched repository.
- Archive this change with spec sync:
  - it retires `container-podman-access`;
  - it creates `session-container-engine`;
  - it moves the launch-engine requirements to `container-session`.
- A reference change in `sandbox-container` that aligns `docs/propagation.md` and the tool's checklist with the rule of development tests only: `launcher/windows/` maps to a release risk with its smoke test instead of a manual validation step.
- A reference change in `sandbox-container`: when the runner offers `--shared`, the checklist also names the changed shared modules that the runner's list lacks. It should come before Antigravity, OpenCode and Pi adopt `sandbox-ref-36`, whose lists lack the same four modules.
- Antigravity, OpenCode and Pi adopt `sandbox-ref-36` from `sandbox-ref-28`, with this change as their model.
  Their `test_wrapper.py` probe case appends a second `qualification-input` answer to the synthetic control, which answers it itself since `sandbox-ref-34`. As in Codex, the case drops the append.
