# Codex CLI in Podman

`codex-container.sh` runs Codex CLI in a rootless Podman container. The
container uses the host Podman socket, allowing Codex to launch containers for
tests and builds without running a nested daemon.

## Usage

```bash
chmod +x codex-container.sh
podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
./codex-container.sh --container-build
./codex-container.sh
./codex-container.sh exec --full-auto
./codex-container.sh --container-shell
./codex-container.sh --container-help
CODEX_YOLO=1 ./codex-container.sh
```

OpenSpec is installed globally in the image. Initialize it once in each
workspace where you want to use spec-driven development:

```bash
./codex-container.sh --container-shell
cd /absolute/path/to/your-project
openspec init
```

After initialization, use the generated OpenSpec instructions from Codex,
including `/opsx:explore` and `/opsx:propose`. Refresh them with
`openspec update` after upgrading OpenSpec.

The wrapper is designed to replace the `codex` command through a shell alias:

```bash
alias codex=/absolute/path/to/codex-container.sh
```

The wrapper handles `--container-build`, `--container-shell`,
`--container-git-worktree`, and `--container-help`. Every other argument is
forwarded unchanged, so `codex --help`, `codex resume --last`, and other normal
Codex invocations keep their original meaning.

Each container is named from the last component of the current directory and
the next highest numeric index among running instances, for example
`codex-container-0`, `codex-container-1`.

`CODEX_YOLO=1` starts Codex with `--yolo`, disabling approvals and sandboxing.
Use it only when the container and its mounts are considered an isolated,
trusted environment.

### Using Git worktrees

When shared Git metadata and sibling worktrees are beneath a common parent,
run the wrapper from the worktree root with `--container-git-worktree`:

```bash
cd /path/to/root/main
codex --container-git-worktree
codex --container-git-worktree --container-shell
```

Here `codex` is the alias shown above. The option mounts `/path/to/root` at
`/path/to/root` read/write, while the container starts in `/path/to/root/main`.
All files beneath that parent, including sibling worktrees, become writable.
Git metadata outside the selected parent is not exposed by this option.

The wrapper selects the immediate parent of the physical launch directory,
resolving symbolic links without searching for a Git or worktree root. For
example, launching from `/path/to/root/main/src` mounts `/path/to/root/main`.
The flag does not create worktrees or require a Git repository.

## Mounts and security

By default, the current workspace is mounted at the same absolute path inside
the container. With `--container-git-worktree`, its immediate physical parent
is mounted at that same absolute path instead; the working directory and
container naming still use the original launch directory. Preserving absolute
paths is required because bind mounts for child containers are resolved by
the host Podman service. Persistent configuration is stored in
`~/.codex`, mounted at `$HOME/.codex`, and also selected through `CODEX_HOME`.

The socket gives Codex control over containers and volumes available to the
host Podman user. The wrapper does not use `--privileged` and does not install
SSH clients or remote repository configuration.

With `--container-git-worktree`, the selected parent can be your home directory
or `/`, exposing all files beneath it read/write. Use the flag from a directory
whose parent you intend to expose.

## Included Tools

The image includes Node.js/npm, Python 3, Codex CLI, the OpenSpec CLI
(`openspec`), the Podman client, Bubblewrap (`bwrap`), local Git, Bash, search
and editing tools (`ripgrep`, `grep`, `sed`, `gawk`, `find`, `patch`, `diff`),
archive tools (`tar`, `gzip`, `bzip2`, `xz`, `zip`, `unzip`), JSON support
(`jq`), HTTP/TLS support (`curl`, CA certificates), diagnostics (`procps`,
`util-linux`, `file`, `less`), and standard POSIX utilities.
