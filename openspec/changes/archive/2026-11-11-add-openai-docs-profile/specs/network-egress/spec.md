## MODIFIED Requirements

### Requirement: Separate OpenAI authentication profiles
Provider mode SHALL require a named protected profile. `openai-api` SHALL allow only `api.openai.com:443` as its base destination. `openai-account` SHALL authorize only the hosts measured from the installed Codex CLI for ChatGPT sign-in without a browser callback, token refresh and model use. The extension profiles `openai-api-docs` and `openai-account-docs` SHALL add only the measured hosts of the OpenAI documentation MCP server to their base hosts, and SHALL be selected explicitly. Wildcards such as `*.openai.com` SHALL NOT be used; gateways and other providers SHALL need separately named profiles.

#### Scenario: API profile
- **WHEN** `openai-api` is selected
- **THEN** only `api.openai.com:443` is reachable, and account login and unrelated feature hosts are denied

#### Scenario: Account profile inventory
- **WHEN** `openai-account` is selected
- **THEN** exactly its measured, dated host list is reachable on 443
- **AND** the inventory records the Codex version and the source documentation date

#### Scenario: Browser-callback sign-in remains unsupported
- **WHEN** a user starts the ChatGPT browser sign-in that needs a host browser to reach a callback port in the container
- **THEN** no port is published and no host-network exception is added
- **AND** documentation names the supported sign-in methods, such as device-code login or an API key

#### Scenario: API key reaches only the API profile
- **WHEN** a provider session uses `openai-api` or `openai-api-docs` and the host sets `OPENAI_API_KEY`
- **THEN** the key is passed to the container, while `openai-account`, `openai-account-docs` and offline sessions receive no API key from the wrapper

#### Scenario: Documentation MCP with an extension profile
- **WHEN** an operator selects `openai-account-docs` or `openai-api-docs` and the shared configuration declares the OpenAI documentation MCP server
- **THEN** the MCP server starts through the relay and reaches only the measured documentation hosts, in addition to the base hosts
- **AND** other remote MCP servers and documentation hosts stay denied

#### Scenario: Base profiles stay unchanged and default
- **WHEN** an operator runs setup or uses a base profile
- **THEN** the documentation hosts are denied, setup still proposes only the base profiles, and an extension profile requires an explicit `CODEX_CONTAINER_NETWORK_PROFILE` and its own qualification

### Requirement: Optional traffic remains opt-in
Provider sessions SHALL disable Codex update checks, analytics, feedback upload, OTEL export and remote MCP or connectors where the tested CLI supports it, using protected launch arguments or variables that writable `config.toml` cannot override. The only remote MCP endpoint a profile MAY admit is the OpenAI documentation MCP of an explicitly selected extension profile. A missing disable control SHALL NOT broaden the allowlist. Shell and YOLO modes SHALL keep the same outer restrictions.

#### Scenario: Optional feature attempts outbound access
- **WHEN** a disabled feature or writable setting attempts an update check, telemetry, connector or MCP request to an unapproved host
- **THEN** the proxy denies it without adding vendor or CDN wildcards

#### Scenario: Provider-hosted tools
- **WHEN** Codex uses a provider-hosted tool such as remote web search
- **THEN** documentation states that this network activity happens at the provider, outside the local boundary

#### Scenario: Embedded mode message
- **WHEN** a restricted session starts Codex with the protected `-c` overrides
- **THEN** documentation explains Codex's "Running without the shared background server" notice as expected, because the shared server needs a Unix listener that the guard denies

### Requirement: Residual exfiltration disclosure
Provider help, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign API key or account. They SHALL name the hosts of each base and extension profile, state that only offline mode removes the channel, and SHALL NOT present host reduction as preventing it.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.openai.com` and every other allowed host of the selected profile, including the documentation hosts of the extension profiles
