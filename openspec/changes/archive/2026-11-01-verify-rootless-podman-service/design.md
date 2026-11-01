# Design

## Context

See `proposal.md` for motivation. The existing enabled-access branch in `codex-container.sh` checks `-S` on `/run/user/$(id -u)/podman/podman.sock` before image inspection and building. Later, both startup modes mount that socket and set the in-container connection URL. Disabled access skips this branch. The README currently offers manual API verification but the wrapper does not perform it.

The reference is the socket-specific rootless query in [antigravity-container.sh](https://github.com/yarilc/antigravity-container/blob/main/antigravity-container.sh). That wrapper also performs broader runtime checks and supports other socket-selection behavior; those features are not prerequisites for this change.

## Goals / Non-Goals

**Goals:** Establish positive evidence from the exposed service during preflight, using the installed Podman CLI and existing error conventions. Preserve argument forwarding, startup modes, socket location, and mounts.

**Non-Goals:** Validate the general engine used by host build/run commands, add endpoint configuration, import Antigravity's transport restrictions or socket remapping, or change the image. Rootless verification does not restrict the host resources available to the service account.

## Decisions

### Query the exact mounted socket

After the existing socket existence check, invoke `podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}}'` inside the exact opt-in branch. The explicit remote URL verifies the exposed service independently of client connection defaults. A plain `podman info` could inspect a different engine; socket location, ownership, or caller UID alone cannot establish the service's rootless state. No HTTP parsing or new host dependency is needed.

### Fail closed before image operations

Capture the query output with explicit handling of command failure under `set -Eeuo pipefail`. Accept only the exact string `true` after Bash command substitution removes trailing newlines. Do not trim whitespace, coerce booleans, or treat unknown output as success. Distinguish query failure from a negative or invalid rootless result; use `die` with the selected socket and useful service/permission or rootless guidance. Preserve Podman's underlying stderr for troubleshooting.

Keep the check before `podman image exists`, `podman build`, container naming, and `podman run`, including explicit rebuilds. The existing creation of `CODEX_HOME` may still occur earlier; this change promises no image or session operations on verification failure, not a preflight without any filesystem side effects.

An advisory warning was rejected because it would still expose an engine whose required rootless state was not established. A new unconditional runtime check was rejected because the requested boundary is enabled service access.

### Verify behavior with disposable command stubs and a real rootless service

Use a temporary Podman stub with a call log and a disposable Unix socket fixture to exercise the wrapper without needing a rootful daemon. Verify the exact endpoint, accepted output, all failure paths, both startup modes, explicit rebuilds, and disabled values. Keep fixtures outside tracked code unless the apply phase identifies a reusable repository need. Run an enabled shell smoke check against a real rootless API when available, and report unavailable integration checks separately from stub results.

## Risks / Trade-offs

- [An older or incompatible service cannot supply the requested field] → Reject it with an actionable diagnostic rather than infer rootless operation.
- [Each enabled invocation adds an API round trip] → Use a single formatted query; disabled sessions make no additional service request.
- [The service or socket changes after verification] → Treat this as startup validation, not continuous identity attestation; retain the existing socket and host trust boundary.
- [Ambient configuration affects other host Podman operations] → Scope this guarantee to the explicitly queried and mounted socket; broader runtime context handling remains a separate change.

## Migration Plan

Update the wrapper, help, README verification instructions, and relevant runtime guidance together. No image rebuild or new setting is needed. Existing enabled invocations with a reachable rootless service continue normally; rejected invocations must fix or restart that service. Reverting the preflight and documentation changes restores prior behavior without state migration.
