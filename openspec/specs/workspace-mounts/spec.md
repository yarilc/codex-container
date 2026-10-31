# workspace-mounts Specification

## Purpose

Define how the wrapper exposes host workspace files to Codex and child containers, including an explicit parent-directory mount for Git worktree layouts.

## Requirements

### Requirement: Workspace-only access by default

Without `--container-git-worktree`, the wrapper SHALL bind mount the physical launch directory read/write at its identical absolute path as the workspace mount.

#### Scenario: Existing invocation
- **WHEN** the wrapper starts from `/projects/repo/main` without the flag
- **THEN** its workspace mount is `/projects/repo/main:/projects/repo/main:rw`
- **AND** it does not add a workspace mount for `/projects/repo`

### Requirement: Explicit parent-directory workspace mount

With `--container-git-worktree`, the wrapper SHALL replace the workspace mount with a read/write bind mount of the immediate parent of the physical launch directory at its identical absolute path. It SHALL select that parent without requiring a Git repository or searching for a Git or worktree root.

#### Scenario: Sibling worktrees and shared metadata
- **WHEN** the wrapper starts from `/projects/repo/main` with the flag
- **THEN** its workspace mount is `/projects/repo:/projects/repo:rw`
- **AND** shared Git metadata, sibling worktrees, and other files under that parent are exposed read/write

#### Scenario: Launch from a nested directory
- **WHEN** the wrapper starts from `/projects/repo/main/src` with the flag
- **THEN** its workspace mount is `/projects/repo/main:/projects/repo/main:rw`
- **AND** it does not discover or additionally mount `/projects/repo`

#### Scenario: Launch through a symbolic link
- **WHEN** the wrapper starts through a symbolic link resolving to `/projects/repo/main` with the flag
- **THEN** its workspace mount is `/projects/repo:/projects/repo:rw`

#### Scenario: Non-Git directory
- **WHEN** the wrapper starts from an ordinary directory with the flag
- **THEN** it selects that directory's physical parent without a Git repository validation error

#### Scenario: Filesystem root
- **WHEN** the physical launch directory is `/` and the flag is supplied
- **THEN** the workspace mount remains `/:/:rw`

### Requirement: Preserve launch context and absolute paths

The wrapper SHALL retain the physical launch directory as its container working directory and the basis for its existing container naming scheme in both Codex and shell modes. Workspace paths SHALL remain identical between host and container so child bind mounts resolve through the host Podman service.

#### Scenario: Codex session with parent mount
- **WHEN** Codex starts from `/projects/repo/main` with the flag
- **THEN** its working directory is `/projects/repo/main`
- **AND** container naming uses the existing `main-<index>` scheme

#### Scenario: Shell session with parent mount
- **WHEN** the wrapper starts from `/projects/repo/main` with `--container-shell --container-git-worktree`
- **THEN** Bash starts in `/projects/repo/main` with `/projects/repo` mounted at its host path

#### Scenario: Child container bind mount
- **WHEN** a session using the flag launches a child container with a bind mount of a directory under the selected parent
- **THEN** the same absolute source path resolves on the host through the Podman socket

### Requirement: Wrapper argument compatibility

The wrapper SHALL consume `--container-git-worktree` as a boolean option, preserve all other Codex arguments in order with their boundaries intact, and allow the flag alongside existing container options. Repeating the flag SHALL have the same effect as supplying it once.

#### Scenario: Forward arguments and preserve spaces
- **WHEN** the wrapper receives `--container-git-worktree exec "inspect this worktree"`
- **THEN** Codex receives `exec` and `inspect this worktree` as two arguments, without the wrapper flag

#### Scenario: Build and repeated flag
- **WHEN** the wrapper receives `--container-build --container-git-worktree --container-git-worktree`
- **THEN** it retains the existing image build behavior and selects the immediate parent once

### Requirement: Document mount scope and limitations

Wrapper help and the README SHALL explain the flag's parent mount and preserved working directory. The README SHALL include Codex and shell examples from a worktree root, describe physical-directory selection without Git discovery, and explain that the parent and all its contents become writable while Git metadata outside that workspace mount is not exposed by the flag.

#### Scenario: Review help and worktree guidance
- **WHEN** a user reads `--container-help` and the README
- **THEN** the flag and its mount behavior are documented
- **AND** the README explains nested-directory behavior and warns that the selected parent can expose the user's home directory or filesystem root
