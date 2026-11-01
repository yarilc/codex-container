# Codex CLI in Podman

`codex-container.sh` runs Codex CLI in a rootless Podman container. The
image filesystem is read-only, with writable workspace, Codex state, and
temporary storage. Set `CODEX_CONTAINER_PODMAN=1` to expose the host Podman
socket and let Codex launch containers for tests and builds. The Podman command
remains installed in both modes.

## Enable rootless Podman on the host

Run this setup on the Linux host (or inside your Linux/WSL distribution),
using the same non-root account that will run `codex-container.sh`.
Install Podman and its rootless dependencies using your distribution's
[installation instructions](https://podman.io/docs/installation).
The account needs subordinate UID/GID ranges in `/etc/subuid` and
`/etc/subgid`, the `newuidmap`/`newgidmap` helpers, and a rootless networking
backend supported by the installed Podman version. If these are missing,
complete the administrator steps in the
[rootless setup guide](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md)
before continuing.

Check that local rootless Podman works:

```bash
podman info --format '{{.Host.Security.Rootless}}'
podman run --rm docker.io/library/alpine:latest id
```

The first command must print `true`; the second must successfully start a
container. Root inside that container is normal for rootless Podman.

## Optional host Podman API access

Default sessions do not require an API service or socket. Skip this section
and continue to Usage unless you want to enable `CODEX_CONTAINER_PODMAN=1`.
Host Podman is still required to build and launch the Codex container.

With that opt-in, the wrapper requires the host API socket at exactly
`/run/user/$(id -u)/podman/podman.sock`. It does not use a custom
`XDG_RUNTIME_DIR` to locate it. Choose **one** of the following methods.

### With a systemd user session

From a normal login session for your account, enable socket activation:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket --no-pager
```

Systemd creates the socket and its parent directory, and starts the API
service when a client connects. An inactive `podman.service` between requests
is normal. To keep the user service available after logout and start it at
boot, optionally enable lingering:

```bash
sudo loginctl enable-linger "$(id -un)"
```

If `systemctl --user` reports that it cannot connect to the bus, ensure you
are logged in directly as the intended user with a working systemd user
session. On systems without systemd, use the manual procedure below.

### Without systemd: create the directories and start the service

An error such as
`bind: no such file or directory` when creating the socket means that a
parent directory is missing. The socket file itself is created by Podman;
do not create it with `touch`.

In a terminal on the host, prepare the runtime directory. On systems without
a login manager, `/run/user/<uid>` may also be absent; creating it under
`/run` usually requires administrator privileges:

```bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$XDG_RUNTIME_DIR"
fi
ls -ld "$XDG_RUNTIME_DIR"
```

The directory must belong to your account and have mode `0700`
(`drwx------`). If an existing directory has incorrect ownership or
permissions, have the administrator correct it before continuing. Then run
the following as your normal user:

```bash
install -d -m 0700 "$XDG_RUNTIME_DIR/podman"
podman system service --time=0 "unix://$XDG_RUNTIME_DIR/podman/podman.sock"
```

Leave this terminal open and use a second terminal for the checks and wrapper
commands below. The service runs in the foreground; Ctrl+C stops it.
Repeat this setup after reboot because `/run` is temporary. Export the same
`XDG_RUNTIME_DIR` in any other terminal used to run local Podman if your
session does not set it automatically. Run the service and wrapper without
`sudo` so they use your rootless containers and configuration.

### Verify the socket before enabling host access

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
test -S "/run/user/$(id -u)/podman/podman.sock" && echo "Socket exists"
podman --remote --url "unix:///run/user/$(id -u)/podman/podman.sock" info
```

Continue only if the socket exists and the API command succeeds. A socket
file alone does not prove that a service is listening. If the API command
fails, check the systemd status or the foreground service output above.
See also the official
[Podman API service documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

## Usage

After completing the rootless host setup above, run from the
repository directory:

```bash
chmod +x codex-container.sh
./codex-container.sh --container-build
./codex-container.sh
./codex-container.sh exec --full-auto
./codex-container.sh --container-shell
./codex-container.sh --container-help
CODEX_YOLO=1 ./codex-container.sh
```

To allow access to the host Podman service, complete the optional socket setup
and verification, then use:

```bash
CODEX_CONTAINER_PODMAN=1 ./codex-container.sh
CODEX_CONTAINER_PODMAN=1 ./codex-container.sh --container-shell
```

Only the exact value `1` enables this integration. Unset, empty, and all other
values (including `true`) disable it: the wrapper does not validate or mount
the API socket and removes `CONTAINER_HOST` from the session environment.
Existing users who launch child containers through the host service must now
set `CODEX_CONTAINER_PODMAN=1`. Both modes use the same image, and
`CODEX_CONTAINER_IMAGE` continues to override its name.

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
The image filesystem remains read-only even with `CODEX_YOLO=1`.

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

Both Codex and shell sessions use a read-only image root filesystem. The
workspace and persistent Codex state remain writable host binds. `/tmp`,
`/var/tmp`, `/run`, and `/codex-home` use writable temporary filesystems;
files there are discarded when the container is removed, except for the
nested persistent mount at `/codex-home/.codex`. Temporary build artifacts
can execute in `/tmp`, `/var/tmp`, and `/codex-home`.

By default, the current workspace is mounted at the same absolute path inside
the container. With `--container-git-worktree`, its immediate physical parent
is mounted at that same absolute path instead; the working directory and
container naming still use the original launch directory. Preserving absolute
paths is required because bind mounts for child containers are resolved by
the host Podman service. Persistent configuration is stored in
`~/.codex` (or the host `CODEX_HOME` override), mounted at
`/codex-home/.codex`, and also selected through the container's `CODEX_HOME`.

When enabled, the socket gives Codex control over containers and volumes
available to the host Podman user. Without the opt-in, the client is still
installed, but the wrapper supplies no connection to that service. This
controls the wrapper's socket integration; it does not block independently
configured endpoints or sockets exposed through workspace files. The wrapper
does not use `--privileged` and does not install SSH clients or remote
repository configuration.

With `--container-git-worktree`, the selected parent can be your home directory
or `/`, exposing all files beneath it read/write. Use the flag from a directory
whose parent you intend to expose. Writable binds take precedence over image
paths they cover; mounting `/` can mask the image root, so the read-only image
policy does not make such host files immutable.

## Included Tools

The image includes Node.js/npm, Python 3, Codex CLI, the OpenSpec CLI
(`openspec`), the Podman client, Bubblewrap (`bwrap`), local Git, Bash, search
and editing tools (`ripgrep`, `grep`, `sed`, `gawk`, `find`, `patch`, `diff`),
archive tools (`tar`, `gzip`, `bzip2`, `xz`, `zip`, `unzip`), JSON support
(`jq`), HTTP/TLS support (`curl`, CA certificates), diagnostics (`procps`,
`util-linux`, `file`, `less`), and standard POSIX utilities.
