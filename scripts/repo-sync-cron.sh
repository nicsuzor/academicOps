#!/usr/bin/env bash
# repo-sync-cron.sh - Periodic maintenance: transcripts, repo sync, PKB visualizations
#
# Three functions, composable via CLI:
#   do_transcript - Generate recent session transcripts
#   do_sync       - Sync all git repositories (brain, dotfiles, sessions, etc.)
#   do_viz        - Generate PKB visualizations (graph JSON, task map, etc.)
#
# Usage:
#   ./scripts/repo-sync-cron.sh              # Full: transcript + sync + viz
#   ./scripts/repo-sync-cron.sh --quick      # Quick: transcript + sync only
#   ./scripts/repo-sync-cron.sh transcript   # Just transcript
#   ./scripts/repo-sync-cron.sh sync         # Just sync
#   ./scripts/repo-sync-cron.sh viz          # Just viz
#   ./scripts/repo-sync-cron.sh transcript sync  # Specific combination
#
# Crontab suggested setup:
#   */5 * * * * /path/to/repo/scripts/repo-sync-cron.sh --quick >> /tmp/repo-sync-quick.log 2>&1
#   0 * * * * /path/to/repo/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1

set -euo pipefail

# 1. Identify AOPS root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AOPS="${AOPS:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# 2. Source environment — avoid eval; only process simple export VAR=VALUE lines
#    Expand $HOME and ~ since read -r preserves them literally.
if [[ -f "$HOME/.env.local" ]]; then
    while IFS= read -r line; do
        if [[ "$line" =~ ^export[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)= ]]; then
            value="${line#*=}"
            value_expanded="${value//\$HOME/$HOME}"
            if [[ "$value_expanded" == "~" || "$value_expanded" == '"~"' || "$value_expanded" == "'~'" ]]; then
                value_expanded="$HOME"
            else
                value_expanded="${value_expanded//\~\//$HOME/}"
            fi
            line="${line%%=*}=$value_expanded"
            export "${line#export }"
        fi
    done < "$HOME/.env.local"
fi

export ACA_DATA="${ACA_DATA:-$HOME/brain}"
export AOPS_SESSIONS="${AOPS_SESSIONS:-$HOME/.aops/sessions}"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH"

# Ensure we are in the AOPS directory for uv run commands
cd "${AOPS}"

# 3. Verify critical dependencies
if ! command -v uv &>/dev/null; then
    echo "Error: 'uv' not found on PATH. Ensure uv is installed and accessible in non-login shells." >&2
    echo "PATH=$PATH" >&2
    exit 1
fi

TS="$(date '+%Y-%m-%d %H:%M:%S')"

# ============================================================================
# Functions
# ============================================================================

do_transcript() {
    echo "==> Generating recent transcripts..."
    if [[ -f "${AOPS}/aops-core/scripts/transcript.py" ]]; then
        uv run python3 "${AOPS}/aops-core/scripts/transcript.py" --recent > /dev/null 2>&1 || echo "Warning: transcript generation failed"
    else
        echo "Warning: transcript.py not found"
    fi
}

do_sync() {
    # Sync all configured git repos
    if [[ -f "${SCRIPT_DIR}/repo-sync.sh" ]]; then
        echo "==> Syncing repositories..."
        "${SCRIPT_DIR}/repo-sync.sh" --check --quiet 2>&1 || echo "Warning: repo-sync failed"
    else
        echo "Warning: ${SCRIPT_DIR}/repo-sync.sh not found"
    fi

    # Sync AOPS_SESSIONS: pull remote, commit local artifacts, push
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

        # Push everything with retry loop to handle concurrent updates
        local max_push_attempts=3
        local push_attempt=1
        while (( push_attempt <= max_push_attempts )); do
            if git push --quiet 2>/dev/null; then
                break
            fi
            echo "Warning: AOPS_SESSIONS push failed (attempt ${push_attempt}/${max_push_attempts}), trying to rebase and retry..."
            git fetch --quiet 2>/dev/null || true
            if ! git pull --rebase --quiet 2>/dev/null; then
                echo "Warning: AOPS_SESSIONS pull --rebase failed during push retry, aborting rebase"
                git rebase --abort 2>/dev/null || true
                break
            fi
            (( push_attempt++ ))
        done
        if (( push_attempt > max_push_attempts )); then
            echo "Warning: AOPS_SESSIONS push failed after ${max_push_attempts} attempts"
        fi

        cd "${AOPS}"
    fi
}

do_viz() {
    echo "==> Generating PKB visualizations..."
    if [[ -f "${SCRIPT_DIR}/generate-viz.sh" ]]; then
        "${SCRIPT_DIR}/generate-viz.sh" --quick 2>&1 || echo "Warning: generate-viz failed"
    else
        echo "Warning: ${SCRIPT_DIR}/generate-viz.sh not found"
    fi
}

# ============================================================================
# Dispatch
# ============================================================================

if [[ $# -eq 0 ]]; then
    # Full run: transcript -> sync -> viz
    echo "${TS} repo-sync-cron starting (full)"
    do_transcript
    do_sync
    do_viz
elif [[ "${1:-}" == "--quick" ]]; then
    # Quick run: transcript -> sync only
    echo "${TS} repo-sync-cron starting (quick)"
    do_transcript
    do_sync
else
    # Named functions: ./repo-sync-cron.sh transcript sync
    echo "${TS} repo-sync-cron starting ($*)"
    for func in "$@"; do
        case "$func" in
            transcript) do_transcript ;;
            sync)       do_sync ;;
            viz)        do_viz ;;
            *)          echo "Unknown function: $func (valid: transcript, sync, viz)" >&2; exit 1 ;;
        esac
    done
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
