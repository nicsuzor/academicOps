#!/bin/bash
# patch-cowork-mcp.sh — Patch the installed aops-cowork plugin with machine-local MCP config.
#
# Cowork's userConfig prompting doesn't work (as of 2026-04-03), so
# ${user_config.PKB_MCP_URL} in .mcp.json is never resolved. This script
# patches the installed plugin with the actual PKB_MCP_URL from the environment.
#
# Run after every aops-cowork plugin install/reinstall in Claude Desktop.
#
# Usage:
#   ./scripts/patch-cowork-mcp.sh
#   PKB_MCP_URL=http://... ./scripts/patch-cowork-mcp.sh

set -euo pipefail

# Resolve PKB_MCP_URL from environment or .env.local
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

# Find the Cowork plugin directory via manifest.json
SESSIONS_BASE="$HOME/Library/Application Support/Claude/local-agent-mode-sessions"
MANIFEST=$(find "$SESSIONS_BASE" -path "*/rpm/manifest.json" 2>/dev/null | head -1)

if [[ -z "$MANIFEST" ]]; then
    echo "ERROR: No Cowork rpm/manifest.json found. Is the plugin installed?" >&2
    exit 1
fi

RPM_DIR=$(dirname "$MANIFEST")

# Find the aops-cowork plugin ID from manifest
PLUGIN_ID=$(python3 -c "
import json, sys
with open('$MANIFEST') as f:
    m = json.load(f)
for p in m['plugins']:
    if p['name'] == 'aops-cowork':
        print(p['id'])
        sys.exit(0)
print('', file=sys.stderr)
sys.exit(1)
" 2>/dev/null) || {
    echo "ERROR: aops-cowork not found in $MANIFEST" >&2
    exit 1
}

MCP_JSON="$RPM_DIR/$PLUGIN_ID/.mcp.json"

if [[ ! -f "$MCP_JSON" ]]; then
    echo "ERROR: $MCP_JSON does not exist" >&2
    exit 1
fi

# Patch the .mcp.json
python3 -c "
import json

with open('$MCP_JSON') as f:
    config = json.load(f)

pkb = config.get('mcpServers', {}).get('pkb', {})
env = pkb.get('env', {})
old_url = env.get('PKB_MCP_URL', '')
env['PKB_MCP_URL'] = '$PKB_MCP_URL'
pkb['env'] = env

with open('$MCP_JSON', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

if old_url == '$PKB_MCP_URL':
    print(f'Already patched: {old_url}')
else:
    print(f'Patched: {old_url} → $PKB_MCP_URL')
"

echo "Plugin: $RPM_DIR/$PLUGIN_ID"
echo "Done. Start a new Cowork conversation to pick up the change."
