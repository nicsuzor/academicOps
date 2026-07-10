#!/bin/bash
# run-mcp.sh — Launch the PKB MCP client.
#
# This is the sole tracked copy of this launcher (single-source-of-truth);
# aops-core's cowork build copies these same two files in at build time
# (scripts/build.py, build_aops_core's cowork branch) rather than keeping a
# second copy in aops-core/scripts/.
#
# Called by the Cowork and Antigravity plugin MCP launchers, which provide a
# minimal PATH and do NOT propagate the user's shell env. Claude does NOT use
# this script — aops-pkb serves pkb for the "claude" platform over HTTP
# transport directly.
#
# PKB_MCP_URL MUST arrive via this process's environment — there is no file
# fallback. Each launcher is responsible for supplying it:
#   - Antigravity: the plugin's pkb env block sets PKB_MCP_URL: ${PKB_MCP_URL},
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
    echo "It must be supplied via the launcher (Cowork/Antigravity env block)" >&2
    echo "or exported in your shell. There is no ~/.env.local fallback." >&2
    exit 1
fi

# Normalise the URL: strip trailing slashes. The streamable-HTTP endpoint is
# served at `…/mcp` (no trailing slash); a `…/mcp/` value 404s and the proxy
# fails to connect. Container/env configs routinely carry a trailing slash, so
# tolerate it here rather than depending on every supplier getting it exact.
while [[ "$PKB_MCP_URL" == */ ]]; do
    PKB_MCP_URL="${PKB_MCP_URL%/}"
done

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
