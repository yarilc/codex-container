# Verification

Verified on 2026-11-01 using the existing rootless host Podman service and `localhost/codex-cli:latest` (Codex CLI 0.166.0, OpenSpec CLI 1.16.0). Disposable workspaces and isolated host Codex state were used; no credentials or model requests were needed.

## Captured wrapper arguments

- Passed 15 disabled-mode cases: unset, empty, `0`, `true`, and `2`, each with Codex, shell, and YOLO entry behavior. Confirmed read-only flags, four writable temporary filesystems, no socket bind or connection variable, and explicit removal of `CONTAINER_HOST` despite a caller-provided value.
- Passed enabled-mode captures for Codex and shell: expected host socket source, container socket destination, connection variable, and read-only flags.
- Passed argument boundary and order checks including spaces, an empty argument, literal shell metacharacters, symbolic-link launch paths, repeated parent flags, naming with existing numeric suffixes, build mode, and a custom image name.

These captures verify wrapper construction only; the following checks used real containers.

## Real runtime checks

- Default wrapper startup succeeded where `/run/user/1000/podman/podman.sock` was absent in the invoking container. Host launch calls used the already-connected external Podman service. Inside the runtime, Podman remained installed, `CONTAINER_HOST` was unset, and the wrapper socket was absent.
- Effective root mount was read-only. A separate mapped-user probe attempted a write in the image's mode-1777 `/codex-home` without a covering tmpfs and received `EROFS`, distinguishing filesystem protection from ordinary permission denial.
- `/tmp`, `/var/tmp`, `/run`, and `/codex-home` accepted writes. Effective mount options were inspected; temporary scripts executed successfully in `/tmp`, `/var/tmp`, and `/codex-home`.
- Workspace and nested `/codex-home/.codex` state persisted across fresh sessions; temporary files outside that persistent bind disappeared.
- Enabled startup without the expected socket failed with its path and an actionable service-start message.
- For enabled integration, a helper runtime exposed the host socket at its expected absolute source path. The actual wrapper started a read-only runtime, mounted the socket beneath the temporary `/run`, reached the rootless host API, and launched an Alpine child container with an identical absolute workspace bind. Child writes were visible in the parent session.
- A subsequent disabled session retained the client and removed the host connection again.
- Real Git worktrees under a parent directory containing spaces exposed shared Git metadata and writable sibling files with `--container-git-worktree`.
- Codex entrypoint startup passed via `--version` with default, enabled, and YOLO settings. OpenSpec availability passed via `openspec --version` inside the read-only runtime. Authenticated interactive model execution was outside these smoke checks.
- `--container-build --version` passed with the isolated tag `localhost/codex-runtime-readonly-verify:latest`; the existing Containerfile build used cached layers. No Containerfile changes were required.

## Static and specification checks

All passed:

```bash
bash -n codex-container.sh
git diff --check
openspec validate readonly-container-opt-in-podman --strict
openspec validate --specs --strict
```

No required runtime check was unavailable. Temporary harness files, fixtures, and the isolated build tag were removed after verification; no test containers were left running.
