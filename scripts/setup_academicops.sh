#!/usr/bin/env bash
# Setup script for academicOps integration in buttermilk (flat structure)
#
# This script configures buttermilk to work with academicOps framework
# when buttermilk is in a flat directory structure (~/src/buttermilk)
# rather than as a submodule.
#
# Usage:
#   ./scripts/setup_academicops.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== academicOps Setup for Buttermilk ==="
echo

# 1. Verify environment variables
echo "Checking environment variables..."

if [ -z "${ACADEMICOPS_BOT:-}" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT environment variable not set${NC}"
    echo "Please add to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export ACADEMICOPS_BOT=/path/to/academicOps"
    exit 1
fi

if [ ! -d "$ACADEMICOPS_BOT" ]; then
    echo -e "${RED}ERROR: ACADEMICOPS_BOT directory does not exist: $ACADEMICOPS_BOT${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} ACADEMICOPS_BOT=$ACADEMICOPS_BOT"

if [ -n "${ACADEMICOPS_PERSONAL:-}" ]; then
    if [ -d "$ACADEMICOPS_PERSONAL" ]; then
        echo -e "${GREEN}✓${NC} ACADEMICOPS_PERSONAL=$ACADEMICOPS_PERSONAL (optional personal context)"
    else
        echo -e "${YELLOW}⚠${NC}  ACADEMICOPS_PERSONAL set but directory not found: $ACADEMICOPS_PERSONAL"
        echo "    Personal context will not be loaded"
    fi
else
    echo -e "${YELLOW}⚠${NC}  ACADEMICOPS_PERSONAL not set (optional - personal context disabled)"
fi

# 2. Create .claude directory if it doesn't exist
echo
echo "Setting up Claude Code configuration..."

BUTTERMILK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="$BUTTERMILK_ROOT/.claude"

if [ ! -d "$CLAUDE_DIR" ]; then
    mkdir -p "$CLAUDE_DIR"
    echo -e "${GREEN}✓${NC} Created $CLAUDE_DIR"
else
    echo -e "${GREEN}✓${NC} $CLAUDE_DIR already exists"
fi

# 3. Create .claude/settings.json with SessionStart hook
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

cat > "$SETTINGS_FILE" <<'EOF'
{
  "hooks": {
    "SessionStart": {
      "command": [
        "python3",
        "${env:ACADEMICOPS_BOT}/scripts/load_instructions.py"
      ],
      "timeout": 5000
    }
  }
}
EOF

echo -e "${GREEN}✓${NC} Created $SETTINGS_FILE with SessionStart hook"

# 4. Create docs/agents/ directory if needed
AGENTS_DIR="$BUTTERMILK_ROOT/docs/agents"

if [ ! -d "$AGENTS_DIR" ]; then
    mkdir -p "$AGENTS_DIR"
    echo -e "${GREEN}✓${NC} Created $AGENTS_DIR"
else
    echo -e "${GREEN}✓${NC} $AGENTS_DIR already exists"
fi

# 5. Create placeholder INSTRUCTIONS.md if it doesn't exist
INSTRUCTIONS_FILE="$AGENTS_DIR/INSTRUCTIONS.md"

if [ ! -f "$INSTRUCTIONS_FILE" ]; then
    cat > "$INSTRUCTIONS_FILE" <<'EOF'
# Project Instructions

Project-specific instructions for agents working in this repository.

## Project Context

- **Repository**: [owner/repo]
- **Purpose**: [Brief description of what this project does]
- **Priority**: [P0-P3 or other priority scheme]
- **Architecture**: [Key architectural patterns or technologies]

## Development Rules

1. [Project-specific development standards]
2. [Testing requirements]
3. [Code review process]
4. [Any special considerations]

## Key Tools

- [List of commands for common tasks]
- [Testing frameworks]
- [Build/deployment tools]

For generic development methodology, see academicOps core instructions.
EOF
    echo -e "${GREEN}✓${NC} Created placeholder $INSTRUCTIONS_FILE"
else
    echo -e "${GREEN}✓${NC} $INSTRUCTIONS_FILE already exists"
fi

# 6. Verify load_instructions.py exists and is executable
LOAD_SCRIPT="$ACADEMICOPS_BOT/scripts/load_instructions.py"

if [ ! -f "$LOAD_SCRIPT" ]; then
    echo -e "${RED}ERROR: load_instructions.py not found at $LOAD_SCRIPT${NC}"
    exit 1
fi

if [ ! -x "$LOAD_SCRIPT" ]; then
    chmod +x "$LOAD_SCRIPT"
    echo -e "${GREEN}✓${NC} Made $LOAD_SCRIPT executable"
fi

# 7. Test the setup
echo
echo "Testing configuration..."

if python3 "$LOAD_SCRIPT" < /dev/null > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} load_instructions.py executes successfully"
else
    echo -e "${YELLOW}⚠${NC}  load_instructions.py test had warnings (may be expected)"
fi

# 8. Success summary
echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Created/verified:"
echo "  - $CLAUDE_DIR/settings.json (SessionStart hook)"
echo "  - $AGENTS_DIR/INSTRUCTIONS.md (project context)"
echo
echo "Environment configuration:"
echo "  - ACADEMICOPS_BOT=$ACADEMICOPS_BOT"
[ -n "${ACADEMICOPS_PERSONAL:-}" ] && echo "  - ACADEMICOPS_PERSONAL=$ACADEMICOPS_PERSONAL"
echo
echo "Next steps:"
echo "  1. Launch Claude Code from buttermilk directory"
echo "  2. Verify core instructions load at session start"
echo "  3. Customize docs/agents/INSTRUCTIONS.md for your workflow"
echo
