# Spec Delta

## MODIFIED Requirements

### Requirement: Explicit temporary storage capacities

In Codex and shell sessions, the wrapper SHALL cap the `/tmp` and `/var/tmp` tmpfs mounts at 512 MiB each and `/run` at 32 MiB, independently of delegation and YOLO. All three SHALL remain writable with mode 1777, nosuid, and nodev. `/tmp` and `/var/tmp` SHALL retain exec; existing execution options for `/run` and `/codex-home` SHALL be preserved. These caps SHALL NOT change persistent bind mounts.

#### Scenario: Finite capacities in either session mode
- **WHEN** a Codex or shell session starts with any supported delegation and YOLO combination
- **THEN** `/tmp` and `/var/tmp` each have a 536870912-byte tmpfs capacity and `/run` has a 33554432-byte tmpfs capacity
- **AND** their existing access and protective mount options remain in effect

#### Scenario: Temporary executables remain usable
- **WHEN** the mapped user creates and runs an executable in `/tmp`, `/var/tmp`, or `/codex-home` outside persistent state
- **THEN** execution remains possible without modifying the read-only image filesystem

#### Scenario: Exhaust a bounded mount
- **WHEN** a write would exceed the available capacity of `/tmp`, `/var/tmp`, or `/run`
- **THEN** the write fails instead of expanding that mount beyond its configured capacity
- **AND** persistent workspace and state mounts retain their existing capacities and access

#### Scenario: Var tmp contents are ephemeral
- **WHEN** a session writes an executable and other files under `/var/tmp`, exits, and a new session starts
- **THEN** the previous files are absent and `/var/tmp` retains its 512 MiB capacity and executable writable policy

### Requirement: Document temporary storage boundaries

Help, README, and runtime guidance SHALL state the `/tmp`, `/var/tmp`, and `/run` capacities. The README SHALL explain that these are per-mount maxima, not reserved memory or an overall container memory limit, and that ephemeral home has no explicit capacity imposed by this policy.

#### Scenario: User plans temporary storage
- **WHEN** a user reads the storage guidance
- **THEN** they find all three mount capacities, retained executable temporary locations, and the distinction from a total memory limit
