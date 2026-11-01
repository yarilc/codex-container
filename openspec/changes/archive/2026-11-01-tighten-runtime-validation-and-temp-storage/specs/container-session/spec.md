# Spec Delta

## ADDED Requirements

### Requirement: Case-insensitive YOLO environment values

The wrapper SHALL parse `CODEX_YOLO` case-insensitively. Values `1`, `true`, and `yes` SHALL enable wrapper-added YOLO; unset, empty, `0`, `false`, and `no` SHALL disable it. Other values SHALL fail before image operations or startup. Shell mode SHALL validate the value without adding Codex arguments. Help and README SHALL document the accepted values.

#### Scenario: Mixed-case enabled values
- **WHEN** a Codex invocation sets `CODEX_YOLO` to `TrUe`, `YeS`, or another capitalization of an enabled word
- **THEN** the wrapper adds `--yolo` before the unchanged user arguments, retaining their order and boundaries

#### Scenario: Mixed-case disabled values
- **WHEN** `CODEX_YOLO` is unset, empty, `0`, or any capitalization of `false` or `no`
- **THEN** the wrapper does not add `--yolo`
- **AND** explicit native arguments and saved settings retain their existing behavior

#### Scenario: Invalid values
- **WHEN** `CODEX_YOLO` is an unsupported value such as `enabled`, `2`, or a boolean word surrounded by spaces
- **THEN** the wrapper fails with accepted-value guidance before image inspection, building, or session creation

#### Scenario: Shell-mode compatibility
- **WHEN** shell mode receives any valid case-insensitive YOLO value
- **THEN** Bash starts without wrapper-added Codex arguments
- **AND** invalid values remain errors in shell mode

#### Scenario: Exact Podman opt-in remains independent
- **WHEN** a valid mixed-case YOLO value is combined with `CODEX_CONTAINER_PODMAN` equal to `1`, `TrUe`, or `YeS`
- **THEN** only exactly `1` enables delegation, independently of the YOLO value
- **AND** YOLO normalization does not change workspace mounts or the read-only image filesystem
