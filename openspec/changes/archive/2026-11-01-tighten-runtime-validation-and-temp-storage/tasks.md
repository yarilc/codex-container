# Tasks

## 1. Unix endpoints and Podman response validation

- [x] 1.1 Adopt Claude Code's absolute, non-slash-only Unix launch-path check in codex-container.sh; add regressions for `unix://`, `unix:///`, longer slash-only endpoints, relative paths, and valid absolute paths, verifying malformed endpoints make no Podman call in Codex/shell and explicit-build modes and local execution remains supported.
- [x] 1.2 Add Antigravity-style boundary-preserving capture with separate launch/delegation validators and exact-byte fixture output controls; verify zero/one normal final LF, additional leading/interior/trailing blank or nonblank records, CR rejection, required field checks, two-record delegation, socket paths with spaces, query errors with valid-looking output, and no image/session operations after rejection across the existing mode/access matrix.
- [x] 1.3 Update help, README, AGENTS.md runtime guidance, and docs/validation.md for endpoint and response boundaries; verify documentation states early slash-only rejection, one launch record versus two delegated records, optional single final LF, and failure before image operations for invalid responses.

## 2. Case-insensitive YOLO values

- [x] 2.1 Normalize CODEX_YOLO with the reference wrappers' lowercase-before-parse approach; add regressions for mixed-case true/yes/false/no, existing numeric/unset/empty forms, unsupported and whitespace-padded values, shell-mode validation, user argument boundaries and explicit native flags, and independent exact CODEX_CONTAINER_PODMAN=1 behavior.
- [x] 2.2 Update help, README, AGENTS.md guidance, and docs/validation.md for accepted case-insensitive YOLO values; verify examples and accepted/rejected forms match the parser and document that delegation and native application settings keep their existing semantics.

## 3. Bounded executable var tmp storage

- [x] 3.1 Add size=512m to the existing /var/tmp tmpfs without changing its other options; update synthetic mount assertions and verify exact capacity, exec/rw/nosuid/nodev/mode=1777, unchanged /tmp and /run capacities, and unchanged ephemeral home and persistent binds across session/access/YOLO settings.
- [x] 3.2 Extend opted-in runtime checks to inspect /var/tmp's 536870912-byte capacity, mode and mount flags, execute a temporary file, and confirm temporary files disappear on the next session while the capacity remains; verify these checks against a same-host rootless engine using private host-visible state or the native-volume runner, retaining existing storage/exhaustion regressions and recording unavailable checks separately.
- [x] 3.3 Update help, README, AGENTS.md guidance, and docs/validation.md for the new /var/tmp maximum; verify all three bounded mount capacities are documented and remove obsolete statements that /var/tmp has no explicit cap, retaining exec, ephemeral lifetime, and the distinction from total/reserved memory.

## 4. Integration verification

- [x] 4.1 Run `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`, `bash -n codex-container.sh tests/run-runtime.sh`, `git diff --check`, and `openspec validate tighten-runtime-validation-and-temp-storage --strict`; verify they pass and record the synthetic and static results in docs/validation.md.
- [x] 4.2 Run the full opted-in runtime suite with disposable native Linux state, using `bash tests/run-runtime.sh` when needed; verify the new validation accepts actual Podman response terminators and preserves delegated socket remapping, input transport, lifecycle cleanup, persistence, and workspace boundaries, recording endpoint coverage and limitations in docs/validation.md without counting skipped or unavailable checks as passes.

## Workflow follow-up

- Review the completed implementation and evidence before synchronizing specs, archiving the change, or committing through the requested follow-up workflow.
