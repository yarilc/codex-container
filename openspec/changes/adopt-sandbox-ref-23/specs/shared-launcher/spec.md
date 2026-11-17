# Spec Delta

## Purpose

Defines how Codex's launcher is built from the shared Bash core of the `sandbox-container` reference and Codex's own agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## ADDED Requirements

### Requirement: Launcher runs on the shared core
`codex-container.sh` SHALL be the thin entry script of the reference. It SHALL be identical to the reference's `sandbox-container.sh` after the wrapper name is replaced, and SHALL only source `launcher/core.sh` with `agent/launcher.sh` and its arguments. `launcher/core.sh` SHALL be a byte-identical copy from the adopted reference tag, recorded in the reference-copy manifest. Codex SHALL NOT keep launcher logic outside the core and its agent part.

#### Scenario: Core edited in this wrapper
- **WHEN** `launcher/core.sh` differs from the adopted reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Entry script compared with the reference
- **WHEN** `codex-container.sh` is compared with the reference entry script after replacing the wrapper name
- **THEN** they are identical

### Requirement: Codex agent launcher part
`agent/launcher.sh` SHALL hold Codex's profile data for the core, consistent with `agent/profile.json` and `agent/policies/default.json`, including a credential entry for each policy profile of the default policy. Codex's hooks SHALL be `agent_command_args`, `agent_approval_bypass` and `agent_help`. Every other hook SHALL use the core default.

#### Scenario: Profile and launcher part disagree
- **WHEN** `agent/launcher.sh` and `agent/profile.json` or the default policy declare different values for the same property
- **THEN** the shared alignment test fails naming the property

#### Scenario: Credential entries
- **WHEN** the alignment test reads `AGENT_CREDENTIALS`
- **THEN** it lists `openai-api=OPENAI_API_KEY`, `openai-api-docs=OPENAI_API_KEY` and `openai-account=` with an empty credential

#### Scenario: Help documents the approval bypass
- **WHEN** `--container-help` runs
- **THEN** it lists `CODEX_YOLO` with `--yolo` after the common variables, and states that it is never applied in shell mode

### Requirement: Protected Codex arguments by mode
In offline and provider Codex sessions, the agent part SHALL place `--no-daemon` and `-c sandbox_mode="danger-full-access"` before the approval bypass and the user's arguments. Provider sessions SHALL also receive the protected `-c` overrides that disable update checks, analytics, feedback, OTEL export, apps and plugins. Unrestricted sessions, shell mode and the qualification probe SHALL receive none of them.

#### Scenario: Provider session arguments
- **WHEN** a provider Codex session starts with `CODEX_YOLO=1` and the user arguments `exec "a b"`
- **THEN** the application runs `/usr/local/bin/codex --no-daemon -c sandbox_mode="danger-full-access"`, then the provider overrides, then `--yolo`, then `exec` and `a b` as two arguments

#### Scenario: Offline session arguments
- **WHEN** an offline Codex session starts
- **THEN** it receives `--no-daemon` and the sandbox override, and none of the provider overrides

#### Scenario: Unrestricted and shell sessions
- **WHEN** an unrestricted Codex session or any shell session starts
- **THEN** neither `--no-daemon` nor any `-c` override is added

### Requirement: Codex launcher tests cover only Codex's part
Codex's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only Codex's hooks, agent data, credential rules per policy profile and shipped policy inventories. A Codex launcher case that the shared tests do not cover SHALL be added to the reference first, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests
- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations
- **WHEN** `tests/test_wrapper.py` runs every combination of `CODEX_YOLO` and `CODEX_CONTAINER_PODMAN=1` in unrestricted shared and isolated modes
- **THEN** only `CODEX_YOLO` determines the `--yolo` argument, and only the Podman opt-in determines the delegation mounts and variables
