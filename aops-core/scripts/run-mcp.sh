#!/bin/bash
# run-mcp.sh — Launch the PKB MCP server.
#
# Called by Claude Code / Cowork / Gemini plugin MCP launchers, which provide a
# minimal PATH and do NOT propagate the user's shell env. We resolve PKB_MCP_URL
# ourselves rather than relying on the launcher's `${VAR}` template substitution
# (Cowork's userConfig path is broken and the env path is unreliable across
# launchers — see specs/observability.md and the now-obsolete
# scripts/patch-cowork-mcp.sh).
#
# Resolution order:
#   1. inherited PKB_MCP_URL (works in dev shell launches)
#   2. ~/.env.local (canonical user-config file used across academicOps)
#   3. unset → pkb_perf_proxy.py falls back to local 'pkb mcp' stdio transport
#
# This eliminates the post-install patch step. Survives plugin reinstall.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/ensure-path.sh"

# Resolve PKB_MCP_URL: env wins; otherwise source ~/.env.local; otherwise leave
# unset and let the proxy fall through to the local stdio binary.
if [[ -z "$PKB_MCP_URL" && -f "$HOME/.env.local" ]]; then
    # shellcheck disable=SC1091
    set -a; source "$HOME/.env.local"; set +a
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

# Launch the PKB Performance Proxy. The proxy reads PKB_MCP_URL from env: if
# set it proxies the remote server with latency tracking; if unset it falls
# back to local `pkb mcp` stdio.
exec "$SCRIPT_DIR/pkb_perf_proxy.py"
