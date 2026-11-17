# Codex agent part for the shared launcher core (launcher/core.sh). It mirrors
# agent/profile.json and agent/policies/default.json; tests/test_alignment.py
# compares them. See docs/launcher-contract.md in sandbox-container.
AGENT_NAME=codex-container
AGENT_DISPLAY_NAME=Codex
AGENT_WRAPPER=codex-container.sh
AGENT_ENV_PREFIX=CODEX_CONTAINER
AGENT_LABEL_NAMESPACE=io.codex-container
AGENT_IMAGE=localhost/codex-cli
AGENT_PROXY_IMAGE=localhost/codex-egress
AGENT_HOME=/codex-home
AGENT_COMMAND=codex
AGENT_EXEC=/usr/local/bin/codex
AGENT_CONFIG_DIR_ENV=CODEX_HOME
AGENT_CONFIG_HOME=.codex
AGENT_SHARED_DIRS=()
AGENT_PRIVATE_SHARED_DIRS=0
AGENT_APPROVAL_BYPASS_ENV=CODEX_YOLO
AGENT_EXEC_TMP=0
AGENT_INSTALL_FILES=()
AGENT_CREDENTIALS=(openai-account= openai-api=OPENAI_API_KEY openai-api-docs=OPENAI_API_KEY)
AGENT_POLICY_HOSTS=("openai-account=auth.openai.com chatgpt.com developers.openai.com" "openai-api=api.openai.com")
AGENT_SESSION_ENV=()
AGENT_RESTRICTED_ENV=()
# Codex reads its optional-traffic switches from config.toml or -c, so they are
# protected arguments (agent_command_args), not variables.
AGENT_PROVIDER_ENV=()
AGENT_UNSET_ENV=()
AGENT_RESERVED_ENV=()

agent_help() {
    printf '  CODEX_YOLO              enable Codex --yolo: 1, true or yes (case-insensitive)\n'
    printf '                          (default: disabled; never applied in shell mode)\n'
    printf '  OPENAI_API_KEY          forwarded by name only to provider sessions using\n'
    printf '                          openai-api or openai-api-docs\n'
}

# Restricted sessions: Codex's own sandbox cannot start under the guard
# (Bubblewrap needs Netlink), so the guard is the enforced boundary; a later
# operator --sandbox or -c sandbox_mode remains an explicit choice. The shared
# background server needs a Unix listener the guard denies, so --no-daemon runs
# Codex embedded. Provider sessions also disable optional traffic; -c takes
# precedence over the agent-writable config.toml. Unrestricted sessions keep
# Codex's own sandbox and add nothing.
agent_command_args() {
    ((restricted)) || return 0
    agent_mode_args=(--no-daemon -c 'sandbox_mode="danger-full-access"')
    [[ "$1" == provider ]] || return 0
    agent_mode_args+=(-c check_for_update_on_startup=false -c analytics.enabled=false
        -c feedback.enabled=false -c 'otel.exporter="none"' -c 'otel.trace_exporter="none"'
        -c 'otel.metrics_exporter="none"' -c features.apps=false -c features.plugins=false
        -c features.remote_plugin=false -c features.plugin_discovery_prefetch=false)
}

# CODEX_YOLO: Codex's own approval bypass; the core skips it in shell mode.
agent_approval_bypass() {
    agent_bypass_args=(--yolo)
}
