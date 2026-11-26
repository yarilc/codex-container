# Spec Delta

## MODIFIED Requirements

### Requirement: Build automatically only for a missing image
Without an explicit build request, the wrapper SHALL use an existing selected image on image-existence status 0 and, only with exact `CODEX_CONTAINER_MAINTENANCE=1`, build it on status 1. Without it a missing image SHALL stop startup with maintenance guidance before any pull or build. Any other inspection status SHALL stop startup with no build, creation or application start. An existing image whose `build-inputs-hash` label does not match the current build inputs SHALL be refused with rebuild guidance. Engine, leftover delegation opt-in, network-mode, policy and state preconditions SHALL run before image operations.

#### Scenario: Image exists
- **WHEN** inspection of the selected image returns 0 and its `build-inputs-hash` label matches
- **THEN** the wrapper uses that image without building it

#### Scenario: Stale image
- **WHEN** the Containerfile or another build input changed after the image was built, or the image has no `build-inputs-hash` label
- **THEN** a launch without `--container-build` stops before creation and names the rebuild command

#### Scenario: Image is missing
- **WHEN** inspection returns 1 and `CODEX_CONTAINER_MAINTENANCE=1` is set
- **THEN** the wrapper builds the selected image and proceeds only if the build succeeds

#### Scenario: Image is missing without maintenance authorization
- **WHEN** inspection returns 1 and maintenance is not exactly authorized
- **THEN** the wrapper exits before any pull or build with guidance for an operator maintenance invocation
- **AND** neither provider nor unrestricted mode implicitly authorizes the build

#### Scenario: Inspection fails
- **WHEN** inspection returns 125 or another status other than 0 or 1
- **THEN** the wrapper reports an inspection failure and does not build or start a session

#### Scenario: Restricted preconditions gate the build
- **WHEN** a restricted session, including the default provider mode, lacks a protected installation or its provider settings, selects an invalid policy or an unsupported backend, or carries a leftover exact `CODEX_CONTAINER_PODMAN=1`
- **THEN** startup fails before any build, even with maintenance authorization

### Requirement: Preserve explicit image selection and builds
The wrapper SHALL retain `CODEX_CONTAINER_IMAGE` and the existing default image. An image name with whitespace or control characters SHALL be refused before any engine operation. An explicit `--container-build` SHALL build the selected image without a successful existence check, and only with exact `CODEX_CONTAINER_MAINTENANCE=1`. A build SHALL pull any missing exact `FROM` base, then run `podman build --pull=never --format docker` without a timeout. `--container-build` with no Codex argument SHALL validate every launch setting, build and exit without a session; `--container-git-worktree` and `--container-shell` do not count as Codex arguments. A failed build SHALL stop startup. Maintenance SHALL NOT select a network mode.

#### Scenario: Explicit build with override
- **WHEN** either session mode is invoked with `--container-build`, an image override, a Codex argument and `CODEX_CONTAINER_MAINTENANCE=1`
- **THEN** the wrapper builds the overridden image from the project's Containerfile and uses that image on success

#### Scenario: Build-only operation
- **WHEN** `--container-build` is given with maintenance authorization and no Codex argument, also together with `--container-git-worktree`
- **THEN** the wrapper validates its settings, builds the image and exits with the build status without creating a container
- **AND** an invalid setting, such as a leftover delegation opt-in, stops it before the build

#### Scenario: Build fails
- **WHEN** a requested explicit or automatic build fails
- **THEN** the wrapper reports the build failure and creates no session container

#### Scenario: Explicit build without authorization
- **WHEN** `--container-build` is requested without exact maintenance authorization
- **THEN** the wrapper exits before any build with maintenance guidance

#### Scenario: Invalid image name
- **WHEN** `CODEX_CONTAINER_IMAGE` contains a space, tab or control character
- **THEN** the launch stops before any engine operation
