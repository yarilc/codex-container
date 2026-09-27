# Proposal

## Why

The runtime image does not currently include Python 3 or Bubblewrap, so Codex and tools it launches cannot rely on those executables being present in the container. Adding both packages makes them available in the standard runtime image.

## What Changes

- Install the Debian `python3` and `bubblewrap` packages in the container image.
- Update the README's included-tools list to document Python 3 and Bubblewrap (`bwrap`).

## Capabilities

### New Capabilities

None. This is a runtime-image tooling change and introduces no new application behavior.

### Modified Capabilities

None.

## Impact

- `Containerfile`: add two packages to the existing apt installation.
- `README.md`: list Python 3 and Bubblewrap among the included tools.
- The built image gains the `python3` and `bwrap` executables; no wrapper options, mounts, or Podman permissions change.
