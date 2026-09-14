#!/bin/bash
# run-mcp.sh — stdio launcher for the PKB MCP server.
#
# For clients that cannot speak streamable HTTP directly: it proxies stdio to
# the server at $PKB_MCP_URL. This is the launcher the Cowork channel ships
# (ruling, 2026-09-14): a plugin `type: http` server there becomes a claude.ai
# connector fetched from Anthropic's side, which cannot reach a tailnet host.
#
# The endpoint arrives by one of two routes, checked in this order:
#
#   1. $1 — the first argument, when the client substitutes into `args`.
#   2. $PKB_MCP_URL — from this process's environment, when it substitutes
#      into `env` or the launching shell exported it.
#
# Both are carried in the manifest so that whichever substitution a client
# performs, one of them lands. A client that expands NEITHER leaves an
# unexpanded `${...}` placeholder behind; that is detected below and treated
# as absent, so a stale literal can never be handed to fastmcp as a URL.
#
# There is no default, no config-file fallback, and no local server to fall
# back to.

set -u

export USER="${USER:-$(id -un)}"

# An argument that still contains `${` is a placeholder the client did not
# substitute — not a URL. Same test for the env var.
_unexpanded() { [[ "$1" == *'${'* ]]; }

_url="${1:-}"
if [[ -z "$_url" ]] || _unexpanded "$_url"; then
    _url="${PKB_MCP_URL:-}"
fi
if _unexpanded "$_url"; then
    _url=""
fi
PKB_MCP_URL="$_url"
unset _url

# Clients launch MCP servers with a minimal PATH that often omits the user's
# tool directories. Probe before giving up on uvx.
if ! command -v uvx &>/dev/null; then
    if [[ -n "${AOPS_UVX_SEARCH_PATH:-}" ]]; then
        IFS=':' read -ra _search_dirs <<<"$AOPS_UVX_SEARCH_PATH"
    else
        _search_dirs=("$HOME/.local/bin" "$HOME/.cargo/bin" /usr/local/bin /opt/homebrew/bin /usr/bin)
    fi
    for _dir in "${_search_dirs[@]}"; do
        if [[ -x "$_dir/uvx" ]]; then
            export PATH="$_dir:$PATH"
            break
        fi
    done
    unset _dir _search_dirs
fi


if [[ -z "$PKB_MCP_URL" ]]; then
    echo "run-mcp.sh: no PKB endpoint." >&2
    echo "Pass it as the first argument, or set PKB_MCP_URL in this process's" >&2
    echo "environment. If the client was meant to substitute one of those and" >&2
    echo "an unexpanded \${...} placeholder arrived instead, it was discarded." >&2
    exit 1
fi

if ! command -v uvx &>/dev/null; then
    echo "run-mcp.sh: 'uvx' not found on PATH." >&2
    echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# The streamable-HTTP endpoint is served without a trailing slash; a trailing
# slash 404s. Client and container configs routinely carry one.
while [[ "$PKB_MCP_URL" == */ ]]; do
    PKB_MCP_URL="${PKB_MCP_URL%/}"
done

# uv needs a writable cache directory; a minimal environment can point it at an
# unwritable path.
if [[ -z "${UV_CACHE_DIR:-}" ]] || ! mkdir -p "$UV_CACHE_DIR" 2>/dev/null; then
    export UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache-$(id -u)"
fi

exec uvx --from "fastmcp-slim[server]" fastmcp run "$PKB_MCP_URL"
