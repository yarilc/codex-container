# Spec Delta

## MODIFIED Requirements

### Requirement: Codex launcher tests cover only Codex's part
Codex's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only Codex's hooks, agent data, credential rules per policy profile and shipped policy inventories. A Codex launcher case that the shared tests do not cover SHALL be added to the reference first, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests
- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations
- **WHEN** `tests/test_wrapper.py` runs every combination of `CODEX_YOLO` and shell mode in unrestricted shared and isolated modes
- **THEN** only `CODEX_YOLO` determines the `--yolo` argument, and no combination mounts a Podman socket
