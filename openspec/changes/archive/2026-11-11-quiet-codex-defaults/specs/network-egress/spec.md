## MODIFIED Requirements

### Requirement: Codex native sandbox under the outer boundary
Because Codex's own command sandbox cannot run under the guard, the wrapper SHALL add a protected `-c sandbox_mode="danger-full-access"` before the user's arguments in `offline` and `provider` Codex launches, and SHALL NOT add it in `unrestricted`. Because Codex's shared background server needs a Unix listener that the guard denies, those launches SHALL also add a protected `--no-daemon` before the overrides. Codex sandbox settings SHALL NOT broaden the outer boundary or weaken the guard.

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
- **THEN** no sandbox override and no `--no-daemon` are added, and Codex's own sandbox works as before

#### Scenario: Restricted launch without the embedded-mode notice
- **WHEN** Codex starts in offline or provider mode, interactively or with a subcommand such as `exec`, `login` or `mcp`
- **THEN** it runs embedded without printing `Running without the shared background server`

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
- **THEN** the key is passed to the container, while `openai-account` and offline sessions receive no API key from the wrapper

#### Scenario: Documentation MCP with an extension profile
- **WHEN** an operator selects `openai-account` or `openai-api-docs` and the shared configuration declares the OpenAI documentation MCP server
- **THEN** the MCP server starts through the relay and reaches only the measured documentation host, in addition to the sign-in or API hosts
- **AND** other remote MCP servers stay denied

#### Scenario: Base profiles stay unchanged and default
- **WHEN** an operator runs setup or uses `openai-api`
- **THEN** setup proposes `openai-account` for the account method and `openai-api` for the API method, `openai-api` denies the documentation host, and `openai-api-docs` requires an explicit `CODEX_CONTAINER_NETWORK_PROFILE` and its own qualification

### Requirement: Optional traffic remains opt-in
Provider sessions SHALL disable Codex update checks, analytics, feedback upload, OTEL export and remote MCP or connectors where supported, with protected launch arguments or variables that writable `config.toml` cannot override. The only remote MCP endpoint a profile MAY admit is the OpenAI documentation MCP, under `openai-account` or the explicitly selected `openai-api-docs`. A missing disable control SHALL NOT broaden the allowlist. Shell and YOLO modes SHALL keep the same outer restrictions.

#### Scenario: Optional feature attempts outbound access
- **WHEN** a disabled feature or writable setting attempts an update check, telemetry, connector or MCP request to an unapproved host
- **THEN** the proxy denies it without adding vendor or CDN wildcards

#### Scenario: Provider-hosted tools
- **WHEN** Codex uses a provider-hosted tool such as remote web search
- **THEN** documentation states that this network activity happens at the provider, outside the local boundary

#### Scenario: Embedded mode message
- **WHEN** a restricted session starts Codex with the protected `-c` overrides
- **THEN** the protected `--no-daemon` keeps Codex from printing the "Running without the shared background server" notice, and documentation explains why the shared server is not used under the guard

### Requirement: Residual exfiltration disclosure
Provider help, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign API key or account. They SHALL name the hosts of each base and extension profile, state that only offline mode removes the channel, and SHALL NOT present host reduction as preventing it.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.openai.com` and every other allowed host of the selected profile, including `developers.openai.com` for `openai-account` and `openai-api-docs`
