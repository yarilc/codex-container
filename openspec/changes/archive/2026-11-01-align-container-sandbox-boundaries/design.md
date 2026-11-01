# Design

## Context

See `proposal.md` for motivation and scope. `codex-container.sh` currently creates `CODEX_HOME` without privacy checks, verifies only the fixed optional delegation socket, and runs image/container commands using the ambient Podman context. The existing three capabilities already define the workspace, persistent state, and optional service boundary. `../antigravity-container` supplies a reference implementation and test patterns, not a new runtime dependency.

The current script always allocates a terminal. The new real-runtime checks must accommodate that with a pseudo-terminal rather than changing terminal behavior in this change. Host services resolve bind sources; a caller inside a container must see workspace and state at their real host absolute paths.

## Goals / Non-Goals

**Goals:** Make failed preconditions stop before image operations, distinguish launch authority from delegated authority, and verify observable filesystem boundaries using disposable state.

**Non-Goals:** Rework CLI permissions, container lifecycle, image refresh semantics, default state location, or temporary mount policy. No authentication helper, namespace workaround, general network sandbox, or broader host mount is introduced. Main specifications are synchronized only after implementation verification through the normal completion workflow.

## Decisions

### 1. Validate launch and delegation independently

Keep the existing command-array approach. Process wrapper help first, then validate arguments, the launch engine, optional delegation, and state before image inspection/build/startup. Move the current early `mkdir` into state validation. Small Bash helpers should report actionable errors without printing state contents.

For launch operations, inspect the engine using `podman info` for `Host.Security.Rootless`, `Host.OS`, and `Host.ServiceIsRemote`. Require explicit `true`, `linux`, and a recognized boolean service-remote field. Reject nonempty `CONTAINER_CONNECTION` and any nonempty `CONTAINER_HOST` other than an absolute Unix URL; service-remote execution requires that explicit Unix URL. Use the same Podman invocation context for the query and subsequent image/container commands. Apply this in shell/build modes and regardless of opt-ins.

Alternative: reuse only the delegated service check. Rejected because it does not verify the engine that actually launches the container and does nothing when delegation is disabled. Forcing every invocation through the API is also rejected: local rootless operation must still work without an API service.

### 2. Separate client-visible socket paths from host bind sources

Preserve exact `CODEX_CONTAINER_PODMAN=1`. Only in enabled mode, select a socket from the first nonempty explicit override, Unix launch URL path, or XDG/UID default. Require an absolute path, canonicalize it, check socket/access properties, and explicitly query that endpoint for rootless operation and `Host.RemoteSocket.Path`. Require a nonempty absolute reported path and bind that source at `/run/podman/podman.sock`, with the existing in-session `CONTAINER_HOST` value. A missing/unsupported host-path report is an error rather than a fallback to the caller-visible path.

The override selects delegation only; it does not change the launch context. Two independently verified engines are allowed only in the documented same-host deployment model, where host source paths are meaningful to both. A Unix transport alone cannot prove physical host identity or path equivalence; proxied/forwarded services on another host are unsupported. Do not claim automatic detection of those deployments. The host-side path need not exist in the caller's namespace, so do not test it there as if it were local.

Alternative: mount the selected client-visible socket directly. Rejected because a containerized caller may see a remapped path which the host engine cannot bind. Keep `--unsetenv CONTAINER_HOST` in disabled mode and do not inspect even an invalid delegation override there. Launch-engine queries remain mandatory and are not delegation-socket verification.

### 3. Validate state without migrating it or changing the session mask

Preserve `${CODEX_HOME:-${HOME}/.codex}` and `/codex-home/.codex`. Create absent directories with a creation-scoped `umask 077`, resolve the physical absolute path, and verify UID ownership, directory type, read/write/traverse access, and zero group/other bits using existing coreutils. Do not leave the restrictive umask active for later workspace operations. Use quoted operands and `--` where supported for paths containing spaces or beginning with a dash.

Reject invalid existing state before image operations. Do not automatically chmod/chown or recursively inspect/repair credentials. Symlinks are supported by validating their resolved target; this is a point-in-time check, not race-proof validation of an untrusted mutable directory tree. Directory mode checks do not audit ancestors, ACLs, hard links, or every existing file.

Alternative: make a dedicated application state location the new default. Deferred because it changes which configuration and sessions users see and needs a separate migration decision. Users can already opt into isolated state through `CODEX_HOME`.

### 4. Verify contracts with two separate test layers

Add standard-library Python wrapper tests with a fake Podman executable that records argv and simulates launch info independently from delegated service info. Cover rejection ordering, malformed responses, exact opt-in values, precedence, socket remapping, state modes/ownership/access, spaces/symlinks, and preservation of mounts and argument boundaries. The fake must return distinct client-visible and host-side socket paths so it can catch remapping regressions. Ownership cases requiring unavailable privileges must be reported as skipped or exercised through a controlled fixture, never counted as real ownership proof.

Add explicitly opted-in runtime checks against a real rootless service using the selected runtime image and disposable projects/state only. Allocate a pseudo-terminal for the current wrapper; preserve its exit status and collect output without credentials. Exercise external sentinels, read-only system files, mapped ownership, persistence of `.codex`, recreation of ephemeral home and all temporary locations, real linked worktrees, and child binds. Run a same-host containerized-caller case with a remapped socket and workspace/state mounted at host absolute paths. Failures of an attempted supported test must remain failures; unavailable Podman, architecture, or SELinux environments are recorded separately.

Alternative: rely on mock argv checks alone. Rejected because they cannot establish kernel-enforced mount boundaries, actual permissions, or service-side bind resolution. The reference suite and its recorded results are not test results for Codex.

## Risks / Trade-offs

- Existing `~/.codex` may be mode `0755`, or live on Windows storage ignoring modes -> fail with a path-specific correction and private Linux `CODEX_HOME` example; do not modify user data automatically.
- Older engines may omit required info fields -> fail closed and document the tested engine version rather than guessing a valid value.
- An exposed rootless socket permits additional host binds -> explicitly document the loss of project-only access and the service user's authority, including all YOLO/delegation combinations.
- Parent mounting can expose home or `/` and mask image paths -> retain the existing warning and tests; read-only image root does not make covered host binds immutable.
- Synthetic wrapper checks cannot prove internal CLI sandbox compatibility -> test actual operation separately when relevant and do not transfer Antigravity's `sethostname` workaround or failure claim.
- A containerized caller's private home may not exist at the same host path -> require a host-visible absolute `CODEX_HOME`; socket remapping alone does not translate state or build context paths.

## Migration Plan

Ship wrapper changes together with README/help/AGENTS guidance. Existing valid Linux rootless users keep their default state and mount behavior. Users with insecure owned state can explicitly run `chmod 700` on that directory; wrong ownership requires an appropriate user/admin correction, and non-enforcing storage requires a different `CODEX_HOME`. No state copying is automatic. Socket users may set the new override; without overrides or XDG/Unix context changes, the UID-based default is retained.

Record exact environment, commands, pass/fail/skip outcomes, and runtime limitations in `docs/validation.md`. Rolling back restores the earlier wrapper and fixed-socket selection; data remains in its existing directory and newly private directory permissions remain valid. No image format or state schema migration is involved.
