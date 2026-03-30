#!/usr/bin/env bash
# setup-automode.sh — Merge academicOps auto mode rules with Claude Code defaults.
#
# Usage:
#   ./scripts/setup-automode.sh              # Preview merged config (stdout)
#   ./scripts/setup-automode.sh --install    # Write to ~/.claude/settings.json
#
# This script:
#   1. Reads CC built-in defaults via `claude auto-mode defaults`
#   2. Appends aops-specific rules from aops-core/config/automode-rules.json
#   3. Outputs (or installs) the merged autoMode config
#
# IMPORTANT: Setting soft_deny or allow REPLACES the entire CC default list.
# This script preserves all CC defaults and appends our additions.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AOPS_RULES="$REPO_ROOT/aops-core/config/automode-rules.json"
USER_SETTINGS="$HOME/.claude/settings.json"

# Check prerequisites
if ! command -v claude >/dev/null 2>&1; then
    echo "ERROR: claude CLI not found. Install Claude Code first." >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq not found. Install with: brew install jq" >&2
    exit 1
fi

if [ ! -f "$AOPS_RULES" ]; then
    echo "ERROR: aops rules file not found at $AOPS_RULES" >&2
    exit 1
fi

# Get CC defaults
CC_DEFAULTS=$(claude auto-mode defaults 2>/dev/null) || {
    echo "ERROR: Failed to get auto-mode defaults. Is Claude Code up to date?" >&2
    exit 1
}

# Merge: CC defaults + aops additions
# - environment: aops replaces CC defaults (ours is more specific)
# - allow: CC defaults + aops additions
# - soft_deny: CC defaults + aops additions
MERGED=$(echo "$CC_DEFAULTS" | jq --slurpfile aops "$AOPS_RULES" '
{
    environment: $aops[0].environment,
    allow: (.allow + $aops[0].allow),
    soft_deny: (.soft_deny + $aops[0].soft_deny)
}')

if [ "${1:-}" = "--install" ]; then
    # Ensure settings directory exists
    mkdir -p "$(dirname "$USER_SETTINGS")"

    if [ -f "$USER_SETTINGS" ]; then
        # Merge into existing settings
        UPDATED=$(jq --argjson automode "$MERGED" '.autoMode = $automode' "$USER_SETTINGS")
        echo "$UPDATED" > "$USER_SETTINGS"
        echo "Updated autoMode in $USER_SETTINGS"
    else
        # Create new settings file
        jq -n --argjson automode "$MERGED" '{ autoMode: $automode }' > "$USER_SETTINGS"
        echo "Created $USER_SETTINGS with autoMode config"
    fi

    echo ""
    echo "Verify with: claude auto-mode config"
    echo "Review with: claude auto-mode critique"
else
    # Preview mode — output merged config
    echo "$MERGED" | jq .
    echo ""
    echo "# Preview only. Run with --install to write to $USER_SETTINGS"
    echo "# CC defaults: $(echo "$CC_DEFAULTS" | jq '.soft_deny | length') soft_deny, $(echo "$CC_DEFAULTS" | jq '.allow | length') allow"
    echo "# aops additions: $(jq '.soft_deny | length' "$AOPS_RULES") soft_deny, $(jq '.allow | length' "$AOPS_RULES") allow"
    echo "# Merged total: $(echo "$MERGED" | jq '.soft_deny | length') soft_deny, $(echo "$MERGED" | jq '.allow | length') allow"
fi
