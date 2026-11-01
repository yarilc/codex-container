# container-image Specification

## Purpose

Make runtime image selection and building predictable, preserving operational errors and excluding unrelated or sensitive repository content from application build inputs.

## Requirements

### Requirement: Build automatically only for a missing image

Without an explicit build request, the wrapper SHALL use an existing selected image on image-existence status 0 and build on status 1. Every other inspection status SHALL stop startup with an actionable diagnostic and no build, container creation, or application startup. Existing engine, delegation, and state preconditions SHALL run before image operations.

#### Scenario: Image exists
- **WHEN** inspection of the selected image returns 0
- **THEN** the wrapper uses that image without building it

#### Scenario: Image is missing
- **WHEN** inspection returns 1
- **THEN** the wrapper builds the selected image and proceeds only if the build succeeds

#### Scenario: Inspection fails
- **WHEN** inspection returns 125 or another status other than 0 or 1
- **THEN** the wrapper reports an inspection failure and does not build or start a session

### Requirement: Preserve explicit image selection and builds

The wrapper SHALL retain `CODEX_CONTAINER_IMAGE` and the existing default image. An explicit `--container-build` SHALL build the selected image without requiring a successful existence check. A failed explicit or automatic build SHALL stop startup. These behaviors SHALL apply to both Codex and shell sessions independently of delegation and YOLO.

#### Scenario: Explicit build with override
- **WHEN** either session mode is invoked with `--container-build` and an image override
- **THEN** the wrapper builds the overridden image from the project's Containerfile and uses that image on success

#### Scenario: Build fails
- **WHEN** a requested explicit or automatic build fails
- **THEN** the wrapper reports the build failure and creates no session container

### Requirement: Exclude repository content from build inputs by default

The project SHALL provide a `.containerignore` that excludes all application build inputs except the current `Containerfile`. Repository metadata, local configuration and state, credentials, caches, documentation, tests, and newly added unrelated files SHALL be excluded at every depth. Build tooling metadata required to apply the ignore policy SHALL remain usable.

#### Scenario: Repository includes sensitive and unrelated files
- **WHEN** a build context contains `.git`, `.codex`, `.env`, nested credentials or caches, test state, documentation, tests, and an otherwise unknown file
- **THEN** these files are unavailable as application build inputs and the Containerfile remains available

#### Scenario: Build needs no local source files
- **WHEN** the current Containerfile is built with the exclusion policy
- **THEN** its package installation and image construction can complete without including repository source or local state

### Requirement: Document image and build-context policy

The README SHALL explain automatic builds only for missing images, failure on inspection errors, explicit builds, and the default-deny build context. It SHALL explain that future local build inputs require deliberate inclusion and that context filtering does not restrict runtime workspace mounts.

#### Scenario: Maintainer adds a local build input
- **WHEN** a maintainer reads the build guidance before adding a local COPY or ADD instruction
- **THEN** they learn that the required input must be explicitly included in `.containerignore`
- **AND** they can distinguish build exclusions from runtime mount access
