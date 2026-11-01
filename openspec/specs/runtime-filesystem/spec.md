# runtime-filesystem Specification

## Purpose

Protect the runtime image from session writes while retaining writable project files, persistent Codex state, and temporary storage.

## Requirements

### Requirement: Read-only image filesystem in all session modes

The wrapper SHALL launch Codex and shell sessions with the image root filesystem mounted read-only, independently of Podman access and `CODEX_YOLO`. Explicit workspace and state mounts and temporary filesystems SHALL be writable exceptions.

#### Scenario: Image files cannot be modified
- **WHEN** a session starts in either Codex or shell mode with either Podman access setting
- **THEN** the container root mount is read-only
- **AND** attempts to modify image files outside writable mounts fail because the filesystem is read-only

#### Scenario: YOLO retains filesystem protection
- **WHEN** the wrapper starts Codex with `CODEX_YOLO=1`
- **THEN** the root filesystem remains read-only

### Requirement: Preserve writable persistent mounts

The wrapper SHALL retain the existing writable workspace selection and the host `CODEX_HOME` bind mounted at `/codex-home/.codex`. Their contents SHALL persist across sessions, and workspace paths and working directory SHALL retain their existing semantics.

#### Scenario: Workspace and state persist
- **WHEN** a session writes files in the workspace and in `/codex-home/.codex` and exits
- **THEN** a later session with the same host directories can read those files

#### Scenario: Parent workspace remains writable
- **WHEN** a session starts with `--container-git-worktree`
- **THEN** the existing immediate-parent workspace bind remains read/write at its identical absolute path

### Requirement: Writable ephemeral runtime locations

The wrapper SHALL provide writable temporary storage in `/tmp`, `/var/tmp`, `/run`, and the non-persistent portion of `/codex-home` for the mapped runtime user. It SHALL retain persistent `CODEX_HOME` within that home and SHALL discard ephemeral session writes when the container is removed.

#### Scenario: Temporary and home writes succeed
- **WHEN** the mapped user creates files in the temporary locations and in `/codex-home` outside `.codex`
- **THEN** those writes succeed without changing the image filesystem
- **AND** those files are absent in a fresh session
- **AND** writes inside `.codex` remain persistent

### Requirement: Private persistent state directory

The wrapper SHALL create missing `CODEX_HOME` with user-only permissions, resolve its physical absolute path, and require a directory owned by the caller, accessible for reading, writing, and traversal, with no group/other permission bits. The default SHALL remain `${HOME}/.codex`, and validated state SHALL remain mounted read/write at `/codex-home/.codex` in Codex and shell modes.

#### Scenario: Create private state
- **WHEN** the selected state directory is absent on a filesystem enforcing Unix permissions
- **THEN** the wrapper creates it with mode `0700` and validates its ownership and access before image inspection, building, or startup
- **AND** the state creation mask does not change subsequent workspace file creation policy

#### Scenario: Existing valid state through a symbolic path
- **WHEN** `CODEX_HOME` names an accessible caller-owned private directory through a relative or symbolic path
- **THEN** the wrapper uses the resolved physical absolute directory as the persistent bind source
- **AND** existing state contents remain available without copying or migration

#### Scenario: Reject insecure or inaccessible state
- **WHEN** state is not a directory, belongs to another user, grants group/other permissions, is inaccessible, or cannot be resolved
- **THEN** the wrapper exits nonzero before image inspection, building, or startup
- **AND** the error identifies the directory and suggests permission correction or a private `CODEX_HOME` as appropriate
- **AND** the wrapper does not change existing permissions or ownership recursively or silently repair the directory

#### Scenario: Filesystem does not enforce private modes
- **WHEN** state creation succeeds but the filesystem does not enforce user-only permissions
- **THEN** startup fails with guidance to select private storage on a filesystem enforcing Unix permissions

#### Scenario: Help has no state side effects
- **WHEN** `--container-help` is requested with missing or insecure state
- **THEN** help succeeds without creating, validating, or modifying the state directory

### Requirement: Document persistent state protection

The README and runtime guidance SHALL explain state privacy checks, the default shared host `~/.codex`, use of a separate `CODEX_HOME`, and migration errors on insecure directories or filesystems. Documentation SHALL distinguish directory access control from encryption and state that writable persistent state remains available to the agent.

#### Scenario: Existing user migrates
- **WHEN** a user reads the migration instructions
- **THEN** they find an explicit `chmod 700` correction for their own existing directory and a separate private Linux state example
- **AND** they learn that changing the state path selects different configuration and sessions without automatic copying
- **AND** checks on the selected directory do not establish the privacy of every ancestor, ACL, or existing file

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
