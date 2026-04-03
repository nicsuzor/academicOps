#!/bin/bash
# run-mcp.sh — Launch the PKB MCP server via uvx/fastmcp.
#
# Called by Claude Code's plugin MCP launcher, which provides a minimal PATH.
# We source ensure-path.sh to find uvx, then exec into it.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

if ! command -v uvx &> /dev/null; then
    echo "CRITICAL: 'uvx' not found on PATH after probing common locations." >&2
    echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

if [[ -z "$PKB_MCP_URL" ]]; then
    echo "CRITICAL: PKB_MCP_URL is not set." >&2
    exit 1
fi

# Ensure uv has a writable cache dir (minimal env may lack $USER,
# causing ~/.env.system-paths UV_CACHE_DIR to resolve to /opt//cache/uv).
if [[ -z "$UV_CACHE_DIR" ]] || ! mkdir -p "$UV_CACHE_DIR" 2>/dev/null; then
    export UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache-$(id -u)"
fi

exec uvx fastmcp run "$PKB_MCP_URL"
