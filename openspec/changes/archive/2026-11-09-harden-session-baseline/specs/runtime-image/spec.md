## ADDED Requirements

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
Documentation SHALL describe the update procedure: change the recorded versions or base digest in the recipe, rebuild explicitly with `--container-build`, rerun the credential-free and real-engine checks, and record the tested versions with the date in the validation record. Sessions SHALL NOT update the pinned inputs.

#### Scenario: Maintainer updates Codex
- **WHEN** a maintainer follows the documented procedure to move to a new Codex version
- **THEN** the procedure requires an explicit rebuild, a rerun of the checks and a dated validation entry naming the tested versions
