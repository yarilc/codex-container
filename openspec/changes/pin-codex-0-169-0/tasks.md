## 1. Baseline

- [x] 1.1 Record the current image ID and the reported versions (`codex-cli 0.167.0`, OpenSpec 1.16.0). Run the pin tests and the credential-free unit suite on the unchanged tree, and keep the results as the baseline for the old-test gate.

## 2. Pins and policy

- [x] 2.1 Set `CODEX_VERSION=0.169.0` and `OPENSPEC_VERSION=2.0.0` in `Containerfile`. Leave the base digest unchanged.
- [x] 2.2 Set `tested.cli` in `agent/policies/default.json` to `0.169.0`, with the measurement notes and dates. Keep the revision unless task 3.3 finds a changed required host.
- [x] 2.3 Update the tests that name the version:
  - `tests/test_image_pins.py`: the diverging CLI becomes `0.169.1`, and the OpenSpec version-range mutation follows the new pin;
  - `tests/test_network_runtime.py`: the version assertion and the measurement comment;
  - `tests/test_setup_runtime.py`: both version assertions.

## 3. Build and measure

- [x] 3.1 Rebuild with `CODEX_CONTAINER_NETWORK=unrestricted CODEX_CONTAINER_MAINTENANCE=1 ./codex-container.sh --container-build`. In the image, confirm `codex --version` reports `codex-cli 0.169.0` and `openspec --version` reports `2.0.0`.
- [x] 3.2 Check the controls the wrapper uses:
  - `--no-daemon`, `-c sandbox_mode=...` and `--yolo`;
  - `--strict-config` rejecting an unknown key;
  - the Bubblewrap/Netlink behavior under the guard.
- [x] 3.3 Run the static endpoint inventory of the 0.169.0 Linux binaries with the 0.167.0 method, and compare it with the recorded hosts. If a required host changed, stop and agree on a `network-egress` delta and a new revision.
- [x] 3.4 Measure the documentation MCP again under `openai-api-docs` with a dummy key. Then check that `codex mcp add` at user level still loads from an untrusted workspace, in the default mode and under `codex exec`.
- [x] 3.5 In provider mode, run a dummy-key session under the logging proxy and record every destination it attempts.

## 4. Suites

- [x] 4.1 Run the credential-free suites and `bash tests/run-runtime.sh` in every mode. Classify any failing old test with the gate and resolve it.
- [x] 4.2 Run the offline OpenSpec round trip from the reference change in shell mode.
- [x] 4.3 Run `bash ../sandbox-container/tools/shellcheck.sh .` and `git diff --check`. Agent-part findings that were already known are recorded; this change must add none.

## 5. Record

- [x] 5.1 Update the version-specific notes in `README.md` and `docs/network-contract.md` to name the version that was measured.
- [x] 5.2 Add a dated entry to `docs/validation.md`. It records the version rule, the versions, the inventory diff, the MCP and trust results, and the suite results.
- [x] 5.3 Run `openspec validate pin-codex-0-169-0 --strict`, then commit on `main`.

## Workflow follow-up

- The operator pushes `main` and reruns `--container-setup` on the three hosts.
- Archive with `/opsx:archive pin-codex-0-169-0`. Sync specs only if a delta was added.
- Real-account checks go to the deferred authenticated pass.
