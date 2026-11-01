# Tasks

## 1. Atomic reservation and owned cleanup

- [x] 1.1 Extend the synthetic Podman fixture to model checked listings, create results and CID files, candidate-existence statuses, attachment, and owned removal; migrate existing assertions from run arguments to creation arguments and verify existing wrapper contracts still pass.
- [x] 1.2 Implement checked all-container enumeration and bounded decimal parsing with existing prefix rules; verify stopped names, `08`, absent matches, foreign prefixes, malformed and oversized suffixes, spaces, symlinks, root-directory fallback, and listing failure in wrapper tests.
- [x] 1.3 Reserve with create and at most 20 confirmed-collision retries; verify successful collision recovery, exhaustion, noncollision creation failure, existence-query failure, and that no existing container is replaced or removed.
- [x] 1.4 Add full-ID ownership, private creation artifacts, and idempotent EXIT cleanup; verify normal exit, failed start, already removed containers, removal failures, temporary-file cleanup, and preservation of application exit codes 0, 23, and 125 without additional creates.
- [x] 1.5 Update README naming and ownership guidance plus applicable AGENTS.md runtime guidance; verify documentation describes stopped containers, retry bounds, full-ID cleanup, and no change to physical-directory naming or mount scope.

## 2. Signals and terminal transport

- [x] 2.1 Add pending-interruption handling during tracked creation and before start, including CID reconciliation; verify TERM/INT/HUP with deterministic fixture barriers before creation finishes and after reservation, proving owned cleanup and no application start after a pending interruption.
- [x] 2.2 Attach through a tracked client with explicit stdin forwarding and coordinated signal proxy behavior; verify TERM/INT/HUP reach only the owned running ID and produce wrapper statuses 143/130/129 for both entrypoint modes.
- [x] 2.3 Add five-second graceful shutdown, bounded control commands and client reaping, and forced owned cleanup; verify an application ignoring signals, a failed or stalled control command, repeated signals, cleanup diagnostics, and preservation of primary status without indefinite waits.
- [x] 2.4 Select TTY only when stdin and stdout are terminals while retaining interactive stdin; verify all four terminal combinations using PTYs and pipes, file input, EOF delivery, output, argument boundaries, and shell-mode compatibility.
- [x] 2.5 Add opted-in runtime regressions for competing starts and stopped-name allocation, actual signal delivery, cleanup isolation and residual-container checks, application exit 125, and PTY/non-PTY input; verify against a same-host rootless engine using disposable state, recording any unavailable execution separately.
- [x] 2.6 Update wrapper help, README examples, AGENTS.md terminal guidance, and docs/validation.md for signal and transport behavior; verify examples and document application terminal requirements, interruption statuses, shutdown deadlines, and SIGKILL/service-loss limitations.

## 3. Image failures and build inputs

- [x] 3.1 Split explicit builds from checked image-existence handling; verify inspection statuses 0/1/125 and an additional error, explicit-build bypass, build failures, image overrides, and absence of create/start after failure across Codex/shell and access/YOLO settings.
- [x] 3.2 Add the default-deny .containerignore with only the root Containerfile as an application input; add an opted-in disposable-context build test proving root/nested sensitive and unknown sentinels are excluded, and verify the production image still builds with that policy.
- [x] 3.3 Update README image and build-context guidance and docs/validation.md evidence; verify the documented status distinction, explicit-build behavior, future COPY/ADD inclusion requirement, and distinction from runtime workspace mounts match the tests.

## 4. Temporary storage capacities

- [x] 4.1 Set /tmp to 512 MiB and /run to 32 MiB while retaining existing mount options; verify exact synthetic creation arguments across session/access/YOLO modes and preservation of the other tmpfs and persistent bind options.
- [x] 4.2 Extend opted-in runtime checks to inspect actual capacities and mount options, execute temporary files in /tmp, /var/tmp, and ephemeral home, and exercise bounded storage exhaustion in a disposable mount; verify persistent state, writable workspace, and fresh-session ephemeral reset remain intact.
- [x] 4.3 Update help, README, AGENTS.md runtime guidance, and docs/validation.md for capacities; verify both values, executable locations, per-mount maximum semantics, and absence of a new total-memory-limit claim.

## 5. Integration verification

- [x] 5.1 Run `python3 -B -m unittest discover -s tests -p test_wrapper.py -v`, `bash -n codex-container.sh tests/run-runtime.sh`, `git diff --check`, and `openspec validate harden-container-session-lifecycle --strict`; verify all pass and record the results in docs/validation.md.
- [x] 5.2 Run the opted-in suite with a built image and private host-visible CODEX_TEST_ROOT, or `bash tests/run-runtime.sh` with disposable native Linux volume storage; verify lifecycle changes coexist with read-only root, persistent private state, worktree mounts, child binds, and same-host socket remapping, recording local/Unix endpoint coverage and unavailable checks without marking them passed.

## Workflow follow-up

- Review implementation and validation evidence before synchronizing delta specs and archiving the change.
- Keep real-engine tasks unchecked if their required verification remains unavailable; do not infer results from mocks or adjacent projects.
