## ADDED Requirements

### Requirement: Launcher files are protected restricted inputs
The shared launcher core and the agent launcher part SHALL be part of the protected code identity recorded in local qualification reports. Restricted preflight SHALL require each of them to be a protected file. Any change to either SHALL invalidate matching qualification evidence.

#### Scenario: Writable launcher core
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` in the installation is writable by others or reachable through a writable mount
- **THEN** restricted preflight fails naming the file

#### Scenario: Launcher core changed after qualification
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` differs from the one recorded in the report
- **THEN** ordinary restricted startup requires requalification

## MODIFIED Requirements

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CODEX_CONTAINER_NETWORK=offline|provider|unrestricted` from explicit operator configuration or the validated managed launcher. An ordinary launch with an unset or empty mode SHALL select `provider`, and SHALL stop with setup guidance before engine calls, state creation or image operations when the provider settings are missing. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Missing and invalid selection
- **WHEN** an ordinary invocation leaves the mode unset or empty without provider settings
- **THEN** it exits nonzero with setup-required guidance naming `--container-setup` and `CODEX_CONTAINER_NETWORK`, before any engine call or state creation
- **AND** an unknown nonempty mode fails with an invalid-mode diagnostic without image operations or agent startup

#### Scenario: Provider by default
- **WHEN** the mode is unset and the provider settings select a protected installation, policy and proxy image
- **THEN** the session runs in provider mode with all provider requirements

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
- **THEN** the session has direct networking and optional delegation with the common launcher hardening, and needs no host Python, guard or qualification report

#### Scenario: Qualification is not an ordinary session
- **WHEN** `--container-qualify` runs with no effective mode
- **THEN** it qualifies offline mode by default with its protected fixtures
- **AND** neither the operation nor its internal probe admits an arbitrary application command or bypasses enforcement

### Requirement: Separate OpenAI authentication profiles
Provider mode SHALL require a named protected profile. `openai-api` SHALL allow only `api.openai.com:443`. `openai-account` SHALL authorize only the measured hosts for ChatGPT sign-in without a browser callback, token refresh, model use and the OpenAI documentation MCP server. The explicitly selected extension `openai-api-docs` SHALL add only the measured documentation MCP hosts to `openai-api`. Wildcards SHALL NOT be used; other providers SHALL need separately named profiles.

#### Scenario: API profile
- **WHEN** `openai-api` is selected
- **THEN** only `api.openai.com:443` is reachable, and account login and unrelated feature hosts are denied

#### Scenario: Account profile inventory
- **WHEN** `openai-account` is selected
- **THEN** exactly its measured, dated host list (`auth.openai.com`, `chatgpt.com` and `developers.openai.com`, on 443) is reachable
- **AND** the inventory records the Codex version and the source documentation date

#### Scenario: Browser-callback sign-in remains unsupported
- **WHEN** a user starts the ChatGPT browser sign-in that needs a host browser to reach a callback port in the container
- **THEN** no port is published and no host-network exception is added
- **AND** documentation names the supported sign-in methods, such as device-code login or an API key

#### Scenario: API key reaches only the API profile
- **WHEN** a provider session uses `openai-api` or `openai-api-docs` and the host sets `OPENAI_API_KEY`
- **THEN** the key is passed to the container by name
- **AND** `openai-account`, operator-defined profiles, offline and unrestricted sessions receive no API key from the wrapper

#### Scenario: Extra variables cannot carry the key to another method
- **WHEN** `CODEX_CONTAINER_ENV_VARS` lists `OPENAI_API_KEY` in a provider session using `openai-account`
- **THEN** the name is skipped with a notice
- **AND** in an unrestricted session the listed key is forwarded by name

#### Scenario: Documentation MCP with an extension profile
- **WHEN** an operator selects `openai-account` or `openai-api-docs` and the shared configuration declares the OpenAI documentation MCP server
- **THEN** the MCP server starts through the relay and reaches only the measured documentation host, in addition to the sign-in or API hosts
- **AND** other remote MCP servers stay denied

#### Scenario: Base profiles stay unchanged and default
- **WHEN** an operator runs setup or uses `openai-api`
- **THEN** setup proposes `openai-account` for the account method and `openai-api` for the API method, `openai-api` denies the documentation host, and `openai-api-docs` requires an explicit `CODEX_CONTAINER_NETWORK_PROFILE` and its own qualification

### Requirement: Credential-free local enforcement qualification
`--container-qualify` SHALL run a bounded credential-free gate through the production launch and guard path and SHALL write a protected report. The qualified code identity SHALL include the shared launcher core and the agent launcher part. Required denial checks SHALL have positive controls or show enforcing syscall rejection. Missing fixtures, unrelated connectivity failure, skipped checks and unavailable transport evidence SHALL fail qualification.

#### Scenario: Mandatory IP and IPC controls
- **WHEN** offline or provider mode is qualified
- **THEN** the gate verifies direct IPv4/IPv6 denial, no external DNS/UDP path, denial of existing and late external Unix endpoints, host-bind socket publication, alternate socket families and pair retargeting
- **AND** loopback and connected-pair exchange, descendant enforcement and caller-owned file persistence succeed

#### Scenario: Provider boundary qualification
- **WHEN** provider mode is qualified
- **THEN** controlled TLS endpoints exercise matching CONNECT/SNI with certificate verification, zero-byte rejection of mismatched SNI, denied authority and fail-closed channel or proxy loss
- **AND** fixture policies and certificates never modify production inventories or CA defaults

#### Scenario: Probe or smoke check is insufficient
- **WHEN** only an ABI query, socket creation, version query or a smoke check succeeds
- **THEN** no successful report is issued and restricted startup stays blocked

#### Scenario: Documented requalification triggers
- **WHEN** the host reboots, or the active SELinux/AppArmor policy cannot be identified
- **THEN** a reboot requires `--container-qualify` again, and an unidentifiable policy forces full qualification on every launch
- **AND** the shipped release acceptance inventory is empty and the gate cannot add entries, so no installation reports release-measured

#### Scenario: Host kernel without IPv6
- **WHEN** the engine host has no IPv6 support, observed as a missing `/proc/sys/net/ipv6` and `EAFNOSUPPORT` on `AF_INET6` socket creation
- **THEN** the gate uses an IPv4-only positive-control network and peer
- **AND** the IPv6 denial is evidenced by `EAFNOSUPPORT` on `AF_INET6` socket creation in both the unconfined control and the guarded probe
- **AND** every other required check runs unchanged

#### Scenario: Inconsistent IPv6 evidence
- **WHEN** the detected IPv6 state is neither clearly present nor clearly absent, or the fixture network, peer addresses, control or guarded probe contradict it
- **THEN** qualification fails without a report and without falling back to the other path

#### Scenario: IPv6 state is bound to the report
- **WHEN** a report was issued for one IPv6 state and the host later runs with the other state
- **THEN** the report is stale and restricted startup requires requalification

### Requirement: Single protected agent profile
All Codex-specific values used by the shared network, launcher and setup components SHALL come from one data-only `agent/profile.json` and its provider policy file. The agent launcher part SHALL mirror them for the launcher and SHALL be checked against them. They include wrapper and variable names, images, labels, installation and state names, native home, command, application path (`native.exec`), executable temporary storage (`native.exec_tmp`), configuration variables, authentication methods and policy profiles. The profile SHALL NOT select who builds the runtime image. It SHALL be schema-validated, trusted-path checked and outside agent-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails validation, or is reachable through a writable mount or escaped symlink
- **THEN** qualification and restricted startup fail before the agent runs, name the profile and use no built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected checkout

#### Scenario: Profile changed after qualification
- **WHEN** the installed profile or policy differs from the one recorded in the current report
- **THEN** ordinary restricted launches are refused with requalification guidance

#### Scenario: Obsolete or mistyped launcher fields
- **WHEN** the profile declares `install.runtime_build`, a relative `native.exec` or a non-boolean `native.exec_tmp`
- **THEN** profile validation fails naming the field

### Requirement: Residual exfiltration disclosure
Provider help, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign API key or account. Help SHALL print the hosts of each base profile from the default policy. The README and the network contract SHALL also name the hosts of the `openai-api-docs` extension. They SHALL state that only offline mode removes the channel, and SHALL NOT present host reduction as preventing it.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.openai.com` and every other allowed host of the selected profile, including `developers.openai.com` for `openai-account`
- **AND** the README and the network contract also name `developers.openai.com` for `openai-api-docs`

### Requirement: Agent-neutral shared sandbox components
The shared `launcher/`, `network/` and `setup/` components and shared tests, including the compiled guard, `tests/test_launcher.py` and `tests/fake_podman.py`, SHALL contain no agent identifiers. They SHALL stay byte-identical to the reference copies in `sandbox-container`, checked by the unchanged `tests/test_alignment.py` and the per-agent SHA-256 manifest. In-container paths, the guard name and the multiplex protocol marker SHALL be agent-neutral. Host-visible images, labels, variables and installation paths SHALL come from the profile.

#### Scenario: Shared component contains an agent identifier
- **WHEN** a shared launcher, network or setup file contains an identifier declared by the profile outside the documented allow-list
- **THEN** the credential-free alignment check fails

#### Scenario: Shared component differs from the reference
- **WHEN** a copied shared file differs from its SHA-256 recorded for the reference tag, or `diff -r` against a sibling `sandbox-container` checkout at that tag reports a difference
- **THEN** the credential-free alignment check fails

#### Scenario: Unlisted file in a shared directory
- **WHEN** `launcher/` contains a file that the manifest does not list
- **THEN** the reference-copy check fails naming the file

#### Scenario: Two wrappers on the same host
- **WHEN** Codex and another wrapper run restricted sessions or qualification concurrently
- **THEN** each creates, inspects and cleans up only resources carrying its own labels and image names
