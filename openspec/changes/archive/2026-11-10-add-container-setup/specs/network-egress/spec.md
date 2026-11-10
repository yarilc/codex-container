## MODIFIED Requirements

### Requirement: Codex native sandbox under the outer boundary
Because Codex's own command sandbox cannot run under the guard, the wrapper SHALL add a protected `-c sandbox_mode="danger-full-access"` before the user's arguments in `offline` and `provider` Codex launches, and SHALL NOT add it in `unrestricted`. Codex sandbox settings SHALL NOT broaden the outer boundary, and the guard SHALL NOT be weakened to accommodate them.

#### Scenario: Codex runs a command in a restricted session
- **WHEN** Codex executes a shell command in offline or provider mode without operator sandbox arguments
- **THEN** the command runs under the guard with Codex's own sandbox disabled by the protected override
- **AND** the command has no network or IPC access beyond the selected mode

#### Scenario: Codex sandbox disabled by the agent
- **WHEN** writable configuration or `--yolo` disables Codex's own sandbox
- **THEN** the outer guard, network and proxy restrictions remain unchanged

#### Scenario: Operator selects a sandbox explicitly
- **WHEN** the operator passes `--sandbox` or `-c sandbox_mode=...` after the protected override in a restricted mode
- **THEN** the operator's value takes effect, and a Codex sandbox that cannot start fails before the command with the guard unchanged

#### Scenario: Unrestricted keeps Codex's sandbox
- **WHEN** an unrestricted Codex launch starts
- **THEN** no sandbox override is added and Codex's own sandbox works as before

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CODEX_CONTAINER_NETWORK=offline|provider|unrestricted` only from explicit operator configuration or the validated managed launcher. An ordinary launch with an unset or empty mode SHALL stop before engine calls, state creation or image operations. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Missing and invalid selection
- **WHEN** an ordinary invocation leaves the mode unset or empty
- **THEN** it exits nonzero with setup-required guidance naming `--container-setup` and `CODEX_CONTAINER_NETWORK`, before any engine call or state creation
- **AND** an unknown nonempty mode fails with an invalid-mode diagnostic without image operations or agent startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, `config.toml`, application state or commands request a broader policy or remove proxy variables
- **THEN** the running session keeps its operator-selected outer boundary

#### Scenario: Explicit offline operation
- **WHEN** an operator selects offline mode
- **THEN** all restricted platform, protected-installation, guard and qualification requirements apply
- **AND** the session cannot reach external services, including the OpenAI API

#### Scenario: Explicit provider or unrestricted operation
- **WHEN** an operator selects provider or unrestricted mode
- **THEN** the mode keeps its policy, authority, prerequisite and separate maintenance requirements
- **AND** failed restricted preparation never falls back to unrestricted networking

#### Scenario: Unrestricted keeps current behavior
- **WHEN** an operator selects `unrestricted`
- **THEN** the session has the networking, delegation and hardening behavior the wrapper had before this change, and needs no host Python, guard or qualification report

#### Scenario: Qualification is not an ordinary session
- **WHEN** `--container-qualify` runs with no effective mode
- **THEN** it qualifies offline mode by default with its protected fixtures
- **AND** neither the operation nor its internal probe admits an arbitrary application command or bypasses enforcement

### Requirement: Agent-neutral shared sandbox components
The shared `network/` and `setup/` components and shared tests, including the compiled guard, SHALL contain no agent identifiers and SHALL stay byte-identical to the reference copies in `claude-container`, checked by the unchanged `tests/test_alignment.py` and the per-agent SHA-256 manifest. In-container paths, the guard name and the multiplex protocol marker SHALL be agent-neutral. Host-visible images, labels, variables and installation paths SHALL come from the profile.

#### Scenario: Shared component contains an agent identifier
- **WHEN** a shared network or setup file contains an identifier declared by the profile outside the documented allow-list
- **THEN** the credential-free alignment check fails

#### Scenario: Shared component differs from the reference
- **WHEN** a copied shared file differs from its SHA-256 recorded for the reference tag, or `diff -r` against a sibling `claude-container` checkout at that tag reports a difference
- **THEN** the credential-free alignment check fails

#### Scenario: Two wrappers on the same host
- **WHEN** Codex and another wrapper run restricted sessions or qualification concurrently
- **THEN** each creates, inspects and cleans up only resources carrying its own labels and image names

### Requirement: Evidence and common contract documentation
Documentation SHALL map N01–N14 and C01–C12 to implementation and acceptance, publish the mode and profile contract and the five-wrapper parity table, and date and version the endpoint inventories. `docs/validation.md` SHALL separate synthetic enforcement, real-rootless bypass checks and operator-run authenticated checks. Untested checks SHALL be recorded as unavailable, and automated tests SHALL NOT use real credentials.

#### Scenario: Provider profile readiness
- **WHEN** a profile is declared verified for a Codex version
- **THEN** operator-run evidence covers login, token refresh, streaming, long-lived requests, supported WebSockets, CA behavior, shell and YOLO modes
- **AND** credential-free tests separately cover DNS/UDP/IPv6, direct IPs and ports, deceptive hosts, redirects, host/LAN/metadata, administration, concurrency, delegation rejection, failure closure and cleanup

#### Scenario: Authenticated check unavailable
- **WHEN** a real API key or account check has not been run by the operator
- **THEN** it is recorded as unavailable and no provider verification is claimed, while mandatory enforcement tests are not waived

#### Scenario: User reviews limits
- **WHEN** a user reads the network documentation
- **THEN** it explains that allowed services can receive session data, provider-hosted tools are outside local filtering, and runtime filtering does not constrain host-side image pulls or builds

#### Scenario: Parity table
- **WHEN** a reader compares the five wrappers
- **THEN** `docs/network-contract.md` here and in `claude-container` show the same Codex row, with authenticated compatibility recorded as pending until the operator checks run
