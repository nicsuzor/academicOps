#!/bin/bash
# run-mcp.sh — Launch the PKB MCP client.
#
# Called by Claude Code / Cowork / Gemini plugin MCP launchers, which provide a
# minimal PATH and do NOT propagate the user's shell env.
#
# PKB_MCP_URL MUST arrive via this process's environment — there is no file
# fallback. Each launcher is responsible for supplying it:
#   - Claude: the plugin manifest declares `userConfig.pkb_mcp_url`, which Claude
#     Code substitutes into this server's `env` block as PKB_MCP_URL. In headless
#     containers the value is pre-seeded into settings.json
#     (pluginConfigs["aops-core@academicOps"].options.pkb_mcp_url) from the
#     container env — see polecat/entrypoint.sh.
#   - Gemini: the extension's pkb env block sets PKB_MCP_URL: ${PKB_MCP_URL},
#     expanded from the host/container env.
#   - Cowork / dev shells: PKB_MCP_URL must be exported in the launching env.
# (specs: brain PKB framework-observability.)
#
# Resolution: inherited PKB_MCP_URL from the environment, or hard fail. No
# silent fallback to ~/.env.local or to a broken local stdio server.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

if [[ -z "$PKB_MCP_URL" ]]; then
    echo "CRITICAL: PKB_MCP_URL is not set in the environment." >&2
    echo "It must be supplied via the launcher (Claude userConfig / Gemini env" >&2
    echo "block) or exported in your shell. There is no ~/.env.local fallback." >&2
    exit 1
fi

if ! command -v uvx &> /dev/null; then
    echo "CRITICAL: 'uvx' not found on PATH after probing common locations." >&2
    echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# Ensure uv has a writable cache dir (minimal env may lack $USER,
# causing ~/.env.system-paths UV_CACHE_DIR to resolve to /opt//cache/uv).
if [[ -z "$UV_CACHE_DIR" ]] || ! mkdir -p "$UV_CACHE_DIR" 2>/dev/null; then
    export UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache-$(id -u)"
fi

exec uvx fastmcp run "$PKB_MCP_URL"
