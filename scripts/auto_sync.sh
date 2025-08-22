#!/bin/bash
set -euo pipefail
# Auto sync append-only task repo + rebuild view
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
cd "$REPO_ROOT"

# Stage any local changes first to avoid rebase conflicts
if [[ -n $(git status -s) ]]; then
  git add -A
  git commit -m "Auto-sync $(hostname) $(date -u +%Y%m%d-%H%M%S)" || true
fi

# Now pull and rebase
git pull --rebase || { echo '{"error":"pull_failed"}'; exit 1; }

# Push all changes
git push || { echo '{"error":"push_failed"}'; exit 1; }
# No separate rebuild step required; task_view.py rebuilds inline when run.
echo '{"status":"synced"}'
