#!/usr/bin/env bash
# Example custom slash command for this repository
#
# This demonstrates how to create repo-local slash commands in bots/commands/
#
# Usage: /example [args]
#
# When user types "/example", Claude Code will:
# 1. Check bots/commands/example.sh (this file) first
# 2. Fall back to framework commands if not found
#
# To use: Create your own commands in bots/commands/ and delete this example

set -euo pipefail

echo "=== Example Custom Command ==="
echo ""
echo "This is a repo-local command in bots/commands/example.sh"
echo ""
echo "To create your own:"
echo "1. Create bots/commands/yourcommand.sh"
echo "2. Make it executable: chmod +x bots/commands/yourcommand.sh"
echo "3. Use it: /yourcommand"
echo ""
echo "Your command can:"
echo "- Run project-specific scripts"
echo "- Access repo-local tools"
echo "- Call framework commands"
echo "- Do anything bash can do"
echo ""
