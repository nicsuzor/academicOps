#!/bin/bash
# repo-sync-cron.sh - Periodic maintenance: repo sync + PKB visualizations
#
# This script is intended to be run via cron. It handles:
# 1. Syncing all configured git repositories (brain, dotfiles, sessions, etc.)
# 2. Generating PKB visualizations (graph JSON, task map)
# 3. Generating recent transcripts
#
# Usage:
#   ./scripts/repo-sync-cron.sh          # Full maintenance (sync + viz)
#   ./scripts/repo-sync-cron.sh --quick  # Only sync (no viz)
#
# Crontab suggested setup:
#   */5 * * * * /path/to/repo/scripts/repo-sync-cron.sh --quick >> /tmp/repo-sync-quick.log 2>&1
#   0 * * * * /path/to/repo/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1

set -euo pipefail

# 1. Identify AOPS root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AOPS="${AOPS:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# 2. Source environment
if [[ -f "$HOME/.zshrc.local" ]]; then
    eval "$(grep '^export ' "$HOME/.zshrc.local")"
fi

export ACA_DATA="${ACA_DATA:-$HOME/brain}"
export AOPS_SESSIONS="${AOPS_SESSIONS:-$HOME/.aops/sessions}"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH"

# Ensure we are in the AOPS directory for uv run commands
cd "${AOPS}"

TS="$(date '+%Y-%m-%d %H:%M:%S')"
QUICK=false
[[ "${1:-}" == "--quick" ]] && QUICK=true

echo "${TS} repo-sync-cron starting (quick=${QUICK})"

# 3. Repo sync
# This syncs ACA_DATA and other repos defined in polecat.yaml
if [[ -f "${SCRIPT_DIR}/repo-sync.sh" ]]; then
    echo "==> Syncing repositories..."
    "${SCRIPT_DIR}/repo-sync.sh" --quiet 2>&1 || echo "Warning: repo-sync failed"
else
    echo "Warning: ${SCRIPT_DIR}/repo-sync.sh not found"
fi

# 4. Generate graph JSON (task index) - frequent updates are good for UI/CLI
echo "==> Updating task index..."
"${AOPS_BIN:-aops}" graph -f json -o "${AOPS_SESSIONS}/tasks.json" > /dev/null 2>&1 || echo "Warning: task index update failed"

# 5. Transcript generation (every 5 mins is fine)
echo "==> Generating recent transcripts..."
if [[ -f "${AOPS}/aops-core/scripts/transcript.py" ]]; then
    uv run python3 "${AOPS}/aops-core/scripts/transcript.py" --recent > /dev/null 2>&1 || echo "Warning: transcript generation failed"
fi

if [[ "$QUICK" == "true" ]]; then
    echo "${TS} repo-sync-cron quick done"
    exit 0
fi

# 6. Generate PKB visualizations (heavier, run less frequently)
echo "==> Generating PKB visualizations..."
if [[ -f "${SCRIPT_DIR}/generate-viz.sh" ]]; then
    "${SCRIPT_DIR}/generate-viz.sh" --quick 2>&1 || echo "Warning: generate-viz failed"
else
    echo "Warning: ${SCRIPT_DIR}/generate-viz.sh not found"
fi

# 7. Full sync AOPS_SESSIONS: pull remote, commit local artifacts, push
if [[ -d "${AOPS_SESSIONS}/.git" ]]; then
    echo "==> Syncing AOPS_SESSIONS artifacts..."
    cd "${AOPS_SESSIONS}"

    # Pull remote changes first
    git fetch --quiet 2>/dev/null || true
    git pull --rebase --quiet 2>/dev/null || {
        echo "Warning: AOPS_SESSIONS pull failed, aborting rebase"
        git rebase --abort 2>/dev/null || true
    }

    # Commit any new/changed local artifacts (viz, transcripts, summaries)
    if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
        git add -A
        git commit -m "sync: auto-generated viz and transcripts" --quiet 2>/dev/null || true
    fi

    # Push everything
    git push --quiet 2>/dev/null || echo "Warning: AOPS_SESSIONS push failed"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
