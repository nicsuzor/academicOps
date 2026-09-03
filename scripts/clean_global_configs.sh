#!/bin/sh
# Definitively remove plugins and mcp servers from global configs for claude, agy, claude code, and openclaw.
#
# SAFETY: This script mutates and deletes user-scoped state under $HOME. It is intentionally
# opt-in and must never run implicitly (e.g. from Makefile targets).

set -eu

if [ "${AOPS_ALLOW_GLOBAL_CONFIG_CLEAN:-}" != "1" ]; then
    echo "clean_global_configs.sh: refusing to modify \$HOME (set AOPS_ALLOW_GLOBAL_CONFIG_CLEAN=1 to run)." >&2
    exit 0
fi
$HOME/.creds/claude/.claude.json
$HOME/.config/claude/config.json
$HOME/.claude-code.json
$HOME/.config/claude-code/config.json
$HOME/.openclaw.json
$HOME/.config/openclaw/config.json
$HOME/.gemini/config.json
$HOME/.config/agy/config.json
$HOME/.gemini/config/mcp.json
"

for conf in $CONFIGS; do
    if [ -f "$conf" ]; then
        python3 -c "
import sys, json, os
try:
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    changed = False
    for k in ['plugins', 'mcpServers', 'mcp', 'marketplace', 'marketplaces', 'customMarketplaces']:
        if k in data:
            del data[k]
            changed = True
    if changed:
        with open(sys.argv[1], 'w') as f:
            json.dump(data, f, indent=2)
except Exception:
    pass
" "$conf"
    fi
done

# Remove known plugin and MCP directories
rm -rf "$HOME/.claude/plugins" "$HOME/.claude/mcp"
rm -rf "$HOME/.claude-code/plugins" "$HOME/.claude-code/mcp"
rm -rf "$HOME/.openclaw/plugins" "$HOME/.openclaw/mcp"
rm -rf "$HOME/.gemini/config/plugins" "$HOME/.gemini/config/mcp" "$HOME/.gemini/config/mcpServers"
rm -rf "$HOME/.config/claude/plugins" "$HOME/.config/claude/mcp"
rm -rf "$HOME/.config/claude-code/plugins" "$HOME/.config/claude-code/mcp"
rm -rf "$HOME/.config/openclaw/plugins" "$HOME/.config/openclaw/mcp"
rm -rf "$HOME/.config/agy/plugins" "$HOME/.config/agy/mcp"

# Clean Claude plugin cache and Cowork GUI packages
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/clean_plugins.py" ]; then
    python3 "$SCRIPT_DIR/clean_plugins.py"
fi
