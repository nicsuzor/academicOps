#!/bin/bash
# run-mcp.sh — Launch the PKB MCP client.
#
# Called by Claude Code / Cowork / Gemini plugin MCP launchers, which provide a
# minimal PATH and do NOT propagate the user's shell env.
#
# On Claude, the plugin manifest declares a `userConfig.pkb_mcp_url` value that
# Claude Code substitutes into this server's `env` block as PKB_MCP_URL — so the
# URL arrives reliably via the launcher, no shell-env propagation required. On
# Cowork the userConfig substitution path is unreliable and Gemini has no such
# mechanism, so this script still resolves PKB_MCP_URL itself for those launchers.
# (specs: brain PKB framework-observability.)
#
# Resolution order:
#   1. inherited PKB_MCP_URL (Claude userConfig env block; or dev shell launches)
#   2. ~/.env.local (canonical user-config file used across academicOps)
#   3. unset → hard fail (no silent fallback to broken local stdio)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

# Resolve PKB_MCP_URL: env wins; otherwise source ~/.env.local.
if [[ -z "$PKB_MCP_URL" && -f "$HOME/.env.local" ]]; then
    # shellcheck disable=SC1091
    set -a; source "$HOME/.env.local"; set +a
fi

if [[ -z "$PKB_MCP_URL" ]]; then
    echo "CRITICAL: PKB_MCP_URL is not set." >&2
    echo "Set it in ~/.env.local or your shell environment." >&2
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
