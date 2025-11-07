#!/usr/bin/env bash
# Sync dprint.json configuration to all known project repos
# Usage: sync_dprint_config.sh [--dry-run]

set -euo pipefail

# Determine academicOps location
if [ -n "${ACADEMICOPS:-}" ] && [ -d "$ACADEMICOPS" ]; then
    AOPS_DIR="$ACADEMICOPS"
elif [ -d "/home/nic/src/writing/aops" ]; then
    AOPS_DIR="/home/nic/src/writing/aops"
else
    echo "Error: Cannot locate academicOps directory"
    exit 1
fi

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    echo "DRY RUN MODE - no files will be modified"
    echo ""
fi

# Known project repositories
REPOS=(
    "/home/nic/src/writing"
    "/home/nic/src/buttermilk"
    "/home/nic/src/zotmcp"
    "/home/nic/src/osbchatmcp"
    "/home/nic/src/omcp"
    "/home/nic/src/mediamarkets"
)

SOURCE_CONFIG="$AOPS_DIR/templates/dprint.json"

if [ ! -f "$SOURCE_CONFIG" ]; then
    echo "Error: Source config not found: $SOURCE_CONFIG"
    exit 1
fi

echo "Source: $SOURCE_CONFIG"
echo "Target repos: ${#REPOS[@]}"
echo ""

UPDATED=0
SKIPPED=0
FAILED=0

for repo in "${REPOS[@]}"; do
    if [ ! -d "$repo" ]; then
        echo "⚠ SKIP: $repo (directory not found)"
        ((SKIPPED++))
        continue
    fi

    TARGET="$repo/dprint.json"

    if [ ! -f "$TARGET" ]; then
        echo "⚠ SKIP: $repo (no dprint.json)"
        ((SKIPPED++))
        continue
    fi

    # Check if files differ
    if cmp -s "$SOURCE_CONFIG" "$TARGET"; then
        echo "✓ OK: $repo (already up to date)"
        continue
    fi

    if [ $DRY_RUN -eq 1 ]; then
        echo "→ WOULD UPDATE: $repo"
        ((UPDATED++))
    else
        if cp "$SOURCE_CONFIG" "$TARGET"; then
            echo "✓ UPDATED: $repo"
            ((UPDATED++))
        else
            echo "✗ FAILED: $repo"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Summary:"
echo "  Updated: $UPDATED"
echo "  Skipped: $SKIPPED"
echo "  Failed: $FAILED"
if [ $DRY_RUN -eq 1 ]; then
    echo ""
    echo "This was a dry run. Run without --dry-run to apply changes."
fi
echo "═══════════════════════════════════════════════════════════"
