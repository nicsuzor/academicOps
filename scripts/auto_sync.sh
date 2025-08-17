#!/bin/bash
set -euo pipefail
# Auto sync append-only task repo + rebuild view
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
cd "$REPO_ROOT"

git pull --rebase || { echo '{"error":"pull_failed"}'; exit 1; }
if [[ -n $(git status -s) ]]; then
  git add -A
  git commit -m "Auto-sync $(hostname) $(date -u +%Y%m%d-%H%M%S)" || true
  git push || { echo '{"error":"push_failed"}'; exit 1; }
fi
# No separate rebuild step required; task_view.py rebuilds inline when run.
echo '{"status":"synced"}'
