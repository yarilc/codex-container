# Workspace Mounts Spec Delta

## MODIFIED Requirements

### Requirement: Preserve launch context and absolute paths

The wrapper SHALL retain the physical launch directory as its container working directory and the basis for its existing container naming scheme in both Codex and shell modes. Workspace paths SHALL remain identical between host and container. Child bind mounts through the host Podman service SHALL require `CODEX_CONTAINER_PODMAN=1`.

#### Scenario: Codex session with parent mount
- **WHEN** Codex starts from `/projects/repo/main` with the flag
- **THEN** its working directory is `/projects/repo/main`
- **AND** container naming uses the existing `main-<index>` scheme

#### Scenario: Shell session with parent mount
- **WHEN** the wrapper starts from `/projects/repo/main` with `--container-shell --container-git-worktree`
- **THEN** Bash starts in `/projects/repo/main` with `/projects/repo` mounted at its host path

#### Scenario: Child container bind mount
- **WHEN** a session using the flag and `CODEX_CONTAINER_PODMAN=1` launches a child container with a bind mount of a directory under the selected parent
- **THEN** the same absolute source path resolves on the host through the Podman socket

#### Scenario: Parent mount without Podman access
- **WHEN** a session uses the flag without the Podman opt-in
- **THEN** the parent workspace remains writable at its host path
- **AND** the Podman command remains installed but the wrapper supplies neither the host socket nor `CONTAINER_HOST`
