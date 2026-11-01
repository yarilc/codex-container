# Runtime Filesystem Spec Delta

## Purpose

Protect the runtime image from session writes while retaining writable project files, persistent Codex state, and temporary storage.

## ADDED Requirements

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
