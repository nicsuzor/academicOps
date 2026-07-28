#!/bin/bash
# run-mcp.sh — stdio launcher for the PKB MCP server.
#
# For clients that cannot speak streamable HTTP directly: it proxies stdio to
# the server at $PKB_MCP_URL. Claude Code does not use this script — its
# .mcp.json points at the HTTP endpoint itself.
#
# $PKB_MCP_URL must arrive in this process's environment. There is no default,
# no config-file fallback, and no local server to fall back to. The launching
# client supplies it, from its own plugin configuration or from the shell that
# started it.

set -u

export USER="${USER:-$(id -un)}"

# Clients launch MCP servers with a minimal PATH that often omits the user's
# tool directories. Probe before giving up on uvx.
if ! command -v uvx &>/dev/null; then
    for _dir in ${AOPS_UVX_SEARCH_PATH:-"$HOME/.local/bin $HOME/.cargo/bin /usr/local/bin /opt/homebrew/bin /usr/bin"}; do
        if [[ -x "$_dir/uvx" ]]; then
            export PATH="$_dir:$PATH"
            break
        fi
    done
    unset _dir
fi


if [[ -z "${PKB_MCP_URL:-}" ]]; then
    echo "run-mcp.sh: PKB_MCP_URL is not set." >&2
    echo "Supply it from the client's plugin configuration, or export it in the" >&2
    echo "environment that launches this script. There is no default." >&2
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
