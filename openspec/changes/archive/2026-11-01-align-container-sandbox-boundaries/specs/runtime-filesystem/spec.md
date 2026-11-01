# Spec Delta

## ADDED Requirements

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
