# Codex CLI in Podman

`codex-container.sh` runs Codex CLI in a rootless Podman container. The
container uses the host Podman socket, allowing Codex to launch containers for
tests and builds without running a nested daemon.

## Usage

```bash
chmod +x codex-container.sh
podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
./codex-container.sh --build
./codex-container.sh
./codex-container.sh exec --full-auto
./codex-container.sh --shell
CODEX_YOLO=1 ./codex-container.sh
```

Each container is named from the last component of the current directory and
the next highest numeric index among running instances, for example
`codex-container-0`, `codex-container-1`.

`CODEX_YOLO=1` starts Codex with `--yolo`, disabling approvals and sandboxing.
Use it only when the container and its mounts are considered an isolated,
trusted environment.

The current workspace is mounted at the same absolute path inside the
container. This is required because bind mounts for child containers are
resolved by the host Podman service. Persistent configuration is stored in
`~/.codex`, mounted at `$HOME/.codex`, and also selected through `CODEX_HOME`.

The socket gives Codex control over containers and volumes available to the
host Podman user. The wrapper does not use `--privileged` and does not install
SSH clients or remote repository configuration.

## Included Tools

The image includes Node.js/npm and Codex CLI, the Podman client, local Git,
Bash, search and editing tools (`ripgrep`, `grep`, `sed`, `gawk`, `find`,
`patch`, `diff`), archive tools (`tar`, `gzip`, `bzip2`, `xz`, `zip`, `unzip`),
JSON support (`jq`), HTTP/TLS support (`curl`, CA certificates), diagnostics
(`procps`, `util-linux`, `file`, `less`), and standard POSIX utilities.
