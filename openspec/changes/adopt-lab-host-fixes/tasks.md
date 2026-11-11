# Tasks

## 1. Adopt sandbox-ref-11

- [x] 1.1 From claude-container, run `python3 -I tools/propagate.py
  ../codex-container sandbox-ref-10 sandbox-ref-11` (dry run). Verify that
  it lists 21 modified shared files, nothing added, removed or "not
  adopted", and `REFERENCE_COMMIT` `d17e865`.
- [x] 1.2 Run the same command with `--apply` and verify:
  - Codex is on branch `adopt-sandbox-ref-11`;
  - `git diff --stat` touches only the listed shared files,
    `tests/test_reference_copy.py`, `README.md`, `AGENTS.md`,
    `docs/setup.md` and `docs/network-contract.md`;
  - `python3 -m unittest tests.test_reference_copy tests.test_alignment`
    passes.

## 2. Wrapper test fixtures

- [x] 2.1 In `tests/test_wrapper.py`:
  - copy `network/agent_budgets.py` into the fake installation;
  - make the fake engine answer `info --format '{{.Host.CgroupControllers}}'`
    from `FAKE_CONTROLLERS`, by default `[cpu memory pids]`.

  Verify that the 21 previously failing wrapper tests pass and that no
  other test changes outcome.

## 3. Launcher

- [x] 3.1 Strip `unix://` from the reported host socket path before the
  absolute-path check. Add wrapper tests for:
  - `unix:///host/podman.sock`, which mounts `/host/podman.sock`;
  - `unix://relative`, which is rejected before image operations.

  Verify with `python3 -m unittest discover -s tests -p test_wrapper.py -k socket`.
- [x] 3.2 Make budgets follow the delegated controllers (design decision 2):
  - query and validate `Host.CgroupControllers`;
  - build `budget_args` and expected values, with `--pids-limit=-1` when
    `pids` is missing;
  - print one notice per unenforced agent budget;
  - verify inspection for both enforced and unenforced budgets, with a
    diagnostic that names the reported controllers;
  - update the `--container-help` budget text.

  Add wrapper tests:
  - every subset of controllers, with the arguments, notices and
    inspection results;
  - an unverifiable controller list, rejected before state creation;
  - a mismatched enforced budget, and an unexpectedly present unenforced
    budget.

  Verify that they pass.
- [x] 3.3 Replace `--read-only-tmpfs=false` with the `/dev`, `/dev/pts`,
  `/dev/shm` and `/run/secrets` mounts (design decision 4). Leave
  `/tmp`, `/var/tmp` and `/run` unchanged. Update the wrapper test that
  asserted `--read-only-tmpfs=false`. Add a test asserting the four mounts
  in Codex and shell mode, in every network mode and with delegation on
  and off. Verify that they pass.
- [x] 3.4 Pass `--secret id=build-ca,src=<bundle>` to both `podman build`
  calls only when host CA trust is enabled, and add `!podman-build-secret*`
  to `.containerignore`. Update the exact build-argument assertion in
  `tests/test_wrapper.py`. Add tests with and without trust, for
  `--container-build` and for the automatic build of a missing image.
  Verify that they pass.
- [x] 3.5 Run `bash -n codex-container.sh` and the full
  `python3 -m unittest discover -s tests -p test_wrapper.py`. Verify that
  both pass.

## 4. Runtime image recipe

- [x] 4.1 Port the HTTPS trust bootstrap into the `Containerfile` package
  step (design decision 6), keeping the Codex package list and npm
  packages. Add the reference's transport and residue checks to
  `tests/test_image_pins.py`:
  - plain-HTTP sources are rejected;
  - disabled peer or host verification is rejected;
  - `build-ca` stays an optional secret mount;
  - the bootstrap bundle is removed.

  Verify that `python3 -m unittest tests.test_image_pins` passes.
- [x] 4.2 Build the image with `CODEX_CONTAINER_MAINTENANCE=1` and
  `CODEX_CONTAINER_IMAGE=localhost/codex-cli:adopt-ref-11 ./codex-container.sh --container-build`.
  Verify:
  - every Debian `URIs:` line is `https://`;
  - `/tmp/apt-bootstrap-ca.pem` is absent;
  - `codex --version` and `openspec --version` report the pinned versions.

## 5. Documentation

- [x] 5.1 Update `README.md` (session hardening, budgets and lifetime,
  temporary storage, image maintenance) and `AGENTS.md`:
  - budgets are enforced per delegated controller, with notices and the
    exhaustion risk;
  - the `/run/secrets` mask;
  - the writable `noexec` `/dev`, `/dev/pts` and read-only `/dev/shm`;
  - image preparation needs outbound HTTPS (443), not port 80;
  - the host CA is passed as a build secret.

  Verify that the documented variables and paths match `--container-help`
  and the launcher.

## 6. Validation and publication

- [x] 6.1 Run the full unit discovery,
  `python3 -m unittest discover -s tests`, on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun, which are recorded as such.
- [x] 6.2 Run `bash tests/run-runtime.sh` with the image from 4.2 in the
  modes the tool listed (`--shared`, `--setup`, `--setup-runtime`,
  `--qualification`, `--guard`, `--network`) and in the default mode
  (`test_runtime.py`, including the Codex native sandbox and the tmpfs
  checks). Verify that every mode passes, or record it as unavailable on
  this host.
- [x] 6.3 Fill in the tool's validation-record template in
  `docs/validation.md` with the results of 6.1–6.2. Add:
  - the wrapper adaptations;
  - the new runtime image ID;
  - the requalification requirement;
  - the operator `--container-setup` and session checks, on this host and
    on the Rocky Linux 9 and newer WSL hosts, as operator-reported or
    pending.

  Verify that every check is listed as passed, failed or unavailable.
- [x] 6.4 Check the five-wrapper parity table: compute the SHA-256 of the
  table from the `| Wrapper |` header to the first blank line in Codex and
  in claude-container. Verify that the two hashes match.
- [x] 6.5 Commit on `adopt-sandbox-ref-11` with the tool's message and the
  co-author trailer, merge it into `main` with `--no-ff`, and verify that
  `git log --oneline -3` shows the merge.

## Workflow follow-up

- The operator pushes Codex `main`, then runs `--container-setup` (refresh
  approved) and a session on this host, the Rocky Linux 9 lab host and the
  newer WSL host. The results are added to `docs/validation.md`.
- Sync the delta specs and archive this change after review.
- OpenCode, Pi and Antigravity follow in their own changes.
