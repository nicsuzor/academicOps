#!/bin/bash
# Session End Protocol for Gemini

echo "=== SESSION END PROTOCOL ==="

# 1. Format
echo "1. Formatting codebase..."
if [ -f "./scripts/format.sh" ]; then
    ./scripts/format.sh
else
    echo "Warning: ./scripts/format.sh not found. Skipping format."
fi

# 2. Git Status
echo "2. Git Status:"
git status

# 3. Instructions
echo "======================="
echo "NEXT STEPS (MANDATORY):"
echo "1. If changes are staged/unstaged: git add -A"
echo "2. Commit: git commit -m 'type: description'"
echo "3. Sync: git pull --rebase"
echo "4. Push: git push"
echo "5. Log: Record session insights if applicable."
echo "======================="
