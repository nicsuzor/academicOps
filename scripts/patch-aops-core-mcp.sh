#!/bin/bash
# patch-aops-core-mcp.sh — Patch the installed aops-core plugin with machine-local MCP config.
#
# Claude Code's userConfig prompting isn't wired up for aops-core, so
# ${user_config.PKB_MCP_URL} in .mcp.json is never resolved. This script
# patches the installed plugin with the actual PKB_MCP_URL from the environment
# (or ~/.env.local).
#
# Run after every aops-core plugin install/reinstall.
#
# Usage:
#   ./scripts/patch-aops-core-mcp.sh
#   PKB_MCP_URL=http://... ./scripts/patch-aops-core-mcp.sh

set -euo pipefail

PLUGIN_KEY="aops-core@academicOps"
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"

if [[ -z "${PKB_MCP_URL:-}" ]]; then
    if [[ -f "$HOME/.env.local" ]]; then
        # shellcheck disable=SC1091
        source "$HOME/.env.local"
    fi
fi

if [[ -z "${PKB_MCP_URL:-}" ]]; then
    echo "ERROR: PKB_MCP_URL not set. Export it or add to ~/.env.local" >&2
    exit 1
fi

if [[ ! -f "$INSTALLED_PLUGINS" ]]; then
    echo "ERROR: $INSTALLED_PLUGINS not found. Is Claude Code installed?" >&2
    exit 1
fi

INSTALL_PATH=$(python3 -c "
import json, sys
with open('$INSTALLED_PLUGINS') as f:
    data = json.load(f)
entries = data.get('plugins', {}).get('$PLUGIN_KEY', [])
if not entries:
    sys.exit(1)
print(entries[-1].get('installPath', ''))
") || {
    echo "ERROR: $PLUGIN_KEY not found in $INSTALLED_PLUGINS" >&2
    exit 1
}

if [[ -z "$INSTALL_PATH" || ! -d "$INSTALL_PATH" ]]; then
    echo "ERROR: installPath '$INSTALL_PATH' does not exist" >&2
    exit 1
fi

MCP_JSON="$INSTALL_PATH/.mcp.json"

if [[ ! -f "$MCP_JSON" ]]; then
    echo "ERROR: $MCP_JSON does not exist" >&2
    exit 1
fi

python3 - "$MCP_JSON" "$PKB_MCP_URL" <<'PY'
import json, sys
path, url = sys.argv[1], sys.argv[2]
with open(path) as f:
    config = json.load(f)
pkb = config.setdefault('mcpServers', {}).setdefault('pkb', {})
env = pkb.setdefault('env', {})
old = env.get('PKB_MCP_URL', '')
env['PKB_MCP_URL'] = url
with open(path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
if old == url:
    print(f'Already patched: {old}')
else:
    print(f'Patched: {old or "(unset)"} → {url}')
PY

echo "Plugin: $INSTALL_PATH"
echo "Done. Start a new Claude Code session to pick up the change."
