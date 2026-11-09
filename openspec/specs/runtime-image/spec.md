# runtime-image Specification

## Purpose

Make runtime image selection and building predictable, preserving operational errors and excluding unrelated or sensitive repository content from application build inputs.

## Requirements

### Requirement: Build automatically only for a missing image

Without an explicit build request, the wrapper SHALL use an existing selected image on image-existence status 0 and, only with exact `CODEX_CONTAINER_MAINTENANCE=1`, build it on status 1. Without it a missing image SHALL stop startup with maintenance guidance before any pull or build. Any other inspection status SHALL stop startup with no build, creation or application start. Engine, delegation, network-mode, policy and state preconditions SHALL run before image operations.

#### Scenario: Image exists
- **WHEN** inspection of the selected image returns 0
- **THEN** the wrapper uses that image without building it

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
- **WHEN** a restricted session selects an invalid policy, an unsupported backend or enabled socket delegation
- **THEN** startup fails before any build, even with maintenance authorization

### Requirement: Preserve explicit image selection and builds

The wrapper SHALL retain `CODEX_CONTAINER_IMAGE` and the existing default image. An explicit `--container-build` SHALL build the selected image without a successful existence check, and only with exact `CODEX_CONTAINER_MAINTENANCE=1`. A failed explicit or automatic build SHALL stop startup. These behaviors SHALL apply to Codex and shell sessions independently of delegation and YOLO. Maintenance SHALL NOT select a network mode.

#### Scenario: Explicit build with override
- **WHEN** either session mode is invoked with `--container-build`, an image override and `CODEX_CONTAINER_MAINTENANCE=1`
- **THEN** the wrapper builds the overridden image from the project's Containerfile and uses that image on success

#### Scenario: Build fails
- **WHEN** a requested explicit or automatic build fails
- **THEN** the wrapper reports the build failure and creates no session container

#### Scenario: Explicit build without authorization
- **WHEN** `--container-build` is requested without exact maintenance authorization
- **THEN** the wrapper exits before any build with maintenance guidance

### Requirement: Exclude repository content from build inputs by default

The project SHALL provide a `.containerignore` that excludes all application build inputs except the current `Containerfile` and the agent-side relay inputs `network/relay.py` and `network/mux.py`. Repository metadata, local configuration and state, credentials, caches, documentation, tests, other network files, and newly added unrelated files SHALL be excluded at every depth. Build tooling metadata required to apply the ignore policy SHALL remain usable.

#### Scenario: Repository includes sensitive and unrelated files
- **WHEN** a build context contains `.git`, `.codex`, `.env`, nested credentials or caches, test state, documentation, tests, and an otherwise unknown file
- **THEN** these files are unavailable as application build inputs and the Containerfile remains available

#### Scenario: Build needs no local source files
- **WHEN** the current Containerfile is built with the exclusion policy
- **THEN** its package installation and image construction can complete with only the admitted relay inputs from the repository

#### Scenario: Relay inputs are the only network files
- **WHEN** the build context is evaluated
- **THEN** only `network/relay.py` and `network/mux.py` are available from `network/`, and they are installed at `/opt/sandbox-egress/`

### Requirement: Document image and build-context policy

The README SHALL explain that builds need exact maintenance authorization, automatic builds only for missing images, failure on inspection errors, explicit builds, and the default-deny build context with its relay exceptions. It SHALL explain that future local build inputs require deliberate inclusion, that context filtering does not restrict runtime workspace mounts, and that runtime network modes do not filter host image pulls or build RUN steps.

#### Scenario: Maintainer adds a local build input
- **WHEN** a maintainer reads the build guidance before adding a local COPY or ADD instruction
- **THEN** they learn that the required input must be explicitly included in `.containerignore`
- **AND** they can distinguish build exclusions from runtime mount access

### Requirement: Runtime image inputs are pinned
The image recipe SHALL install exact versions of `@openai/codex` and `@fission-ai/openspec` recorded in the repository. It SHALL reference the base image by registry digest. No floating tag, `latest` specifier or version range SHALL select an image input. Codex self-update SHALL NOT change the installed version inside a session.

#### Scenario: Build uses recorded versions
- **WHEN** the image is built with `--container-build`
- **THEN** `codex --version` and `openspec --version` in the resulting image report exactly the recorded versions
- **AND** the base layer comes from the recorded digest

#### Scenario: Unpinned input is rejected by tests
- **WHEN** the recipe names a package without an exact version, uses `@latest`, or references the base image without a digest
- **THEN** the credential-free unit suite fails

### Requirement: Version updates follow explicit maintenance
Documentation SHALL describe the update procedure: change the recorded versions or base digest in the recipe, update the policy's tested CLI version, rebuild explicitly with `CODEX_CONTAINER_MAINTENANCE=1` and `--container-build`, rerun the credential-free and real-engine checks and `--container-qualify`, and record the tested versions with the date in the validation record. Sessions SHALL NOT update the pinned inputs.

#### Scenario: Maintainer updates Codex
- **WHEN** a maintainer follows the documented procedure to move to a new Codex version
- **THEN** the procedure requires an explicit rebuild, a rerun of the checks and a dated validation entry naming the tested versions
- **AND** the OpenAI host inventory is re-measured for the new version before the policy's tested CLI version changes

### Requirement: Pinned CLI matches the tested policy version
The pinned Codex version SHALL equal the CLI version recorded in the protected network policy's tested metadata. A version change SHALL update both in the same change and record the tested version in the validation record.

#### Scenario: Versions diverge
- **WHEN** the pinned Codex version differs from the policy's tested CLI field
- **THEN** the credential-free unit suite fails and names both versions

### Requirement: Restricted sessions use an immutable runtime image identity
Offline and provider launches SHALL resolve the selected runtime image to its immutable image ID before preparation and SHALL create the agent container from that ID. An unresolvable or malformed identity SHALL stop startup. Unrestricted launches MAY keep using the image name.

#### Scenario: Image tag moves during a launch
- **WHEN** the selected tag is rebuilt after a restricted launch has resolved its identity
- **THEN** the session and its qualification check use the resolved ID, not the moved tag

#### Scenario: Identity cannot be resolved
- **WHEN** image inspection fails or returns a malformed ID in a restricted mode
- **THEN** startup fails before agent execution

### Requirement: Proxy image acquisition requires maintenance and a digest
Provider mode SHALL use the immutable egress proxy image named by `CODEX_CONTAINER_EGRESS_IMAGE`. An absent proxy image SHALL be pulled only with exact `CODEX_CONTAINER_MAINTENANCE=1` and only when the reference is pinned by digest. Otherwise startup SHALL fail with maintenance guidance before agent execution.

#### Scenario: Proxy image absent without authorization
- **WHEN** the proxy image is absent and maintenance is not authorized or the reference has no digest
- **THEN** startup fails without pulling and names the required operator action
