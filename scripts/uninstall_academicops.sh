#!/usr/bin/env bash
# Uninstall academicOps from a repository
#
# Removes all academicOps-managed files and configuration

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== academicOps Uninstall ==="
echo

# Determine target
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
PROJECT_ROOT="$PWD"

echo "Uninstalling from: $PROJECT_ROOT"
echo

# Safety check
if [ ! -L ".academicOps" ] && [ ! -d ".academicOps" ]; then
    echo -e "${YELLOW}No .academicOps found - nothing to uninstall${NC}"
    exit 0
fi

# 1. Remove .academicOps symlink/directory
echo "Removing .academicOps..."

if [ -L ".academicOps" ]; then
    rm ".academicOps"
    echo -e "${GREEN}✓${NC} Removed .academicOps symlink"
elif [ -d ".academicOps" ]; then
    echo -e "${YELLOW}⚠${NC}  .academicOps is a directory (not symlink)"
    read -p "Delete it? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf ".academicOps"
        echo -e "${GREEN}✓${NC} Deleted .academicOps directory"
    else
        echo "Skipped .academicOps"
    fi
fi

# 2. Remove .claude directory
if [ -d ".claude" ]; then
    echo
    echo -e "${YELLOW}⚠${NC}  Found .claude/ directory"
    read -p "Delete .claude/? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf ".claude"
        echo -e "${GREEN}✓${NC} Deleted .claude/"
    else
        echo "Kept .claude/"
    fi
fi

# 3. Remove bots/agents if only contains template
if [ -d "bots/agents" ]; then
    echo
    FILE_COUNT=$(find bots/agents -type f | wc -l)
    if [ "$FILE_COUNT" -eq 1 ] && [ -f "bots/agents/_CORE.md" ]; then
        echo "bots/agents/ only contains template"
        read -p "Delete bots/agents/? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "bots/agents"
            # Remove bots/ if empty
            if [ -d "bots" ] && [ -z "$(ls -A bots)" ]; then
                rmdir "bots"
            fi
            echo -e "${GREEN}✓${NC} Deleted bots/agents/"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  bots/agents/ contains $FILE_COUNT files (kept)"
    fi
fi

# 4. Clean .gitignore
if [ -f ".gitignore" ]; then
    echo
    if grep -q "# academicOps managed files" ".gitignore"; then
        echo "Removing academicOps section from .gitignore..."

        # Remove from marker to end of file, or to next section
        sed -i '/# academicOps managed files/,/^$/d' ".gitignore"

        echo -e "${GREEN}✓${NC} Cleaned .gitignore"
    fi
fi

echo
echo -e "${GREEN}=== Uninstall Complete ===${NC}"
echo
echo "Removed:"
echo "  - .academicOps/"
echo "  - .claude/ (if confirmed)"
echo "  - bots/agents/ (if only template)"
echo "  - .gitignore academicOps section"
echo
