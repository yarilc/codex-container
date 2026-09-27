# Design

## Context

See `proposal.md` for motivation. The image is based on Debian Bookworm and installs operating-system utilities together in one `apt-get install --no-install-recommends` layer in `Containerfile`.

## Goals / Non-Goals

**Goals:**

- Make `python3` and `bwrap` available on `PATH` in the built image.
- Keep package installation consistent with the image's existing Debian package management.

**Non-Goals:**

- Change Podman runtime flags, namespace configuration, mounts, or host permissions.
- Install Python modules or configure a particular Python environment.
- Guarantee that Bubblewrap can create every sandbox under all host kernel and Podman security configurations; this change provides the executable.

## Decisions

- Install the Debian `python3` and `bubblewrap` packages in the existing apt package list. This keeps both tools managed by the base distribution and avoids adding a separate Python installer or package manager.
- Document Python 3 and Bubblewrap (`bwrap`) in the README's existing included-tools list so the documented runtime matches the image.
- Verify the resulting image by checking that `python3 --version` and `bwrap --version` run in the container. A successful version check confirms package availability without broadening this change into Podman sandbox configuration.

## Risks / Trade-offs

- The added system packages increase the image size. Continue using the existing `--no-install-recommends` apt installation to avoid unnecessary recommended packages.
- Bubblewrap sandbox operations can depend on runtime namespace and security support that this package-only change does not configure. If sandbox execution is the goal, validate it separately under the target host's Podman setup.

## Migration Plan

Rebuild the image using the wrapper's existing `--container-build` option. To roll back, remove the two package entries and rebuild the image.
