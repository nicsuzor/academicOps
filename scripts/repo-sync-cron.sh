#!/usr/bin/env bash
# repo-sync-cron.sh - Periodic maintenance: transcripts, repo sync.
#
# Four functions, composable via CLI:
#   do_cowork_ingest - Normalize and sync Cowork audit logs into sessions repo
#   do_gha_sync      - Sync claude-session artifacts from configured GHA repos
#   do_transcript    - Generate recent session transcripts
#   do_sync          - Sync all git repositories via polecat sync
#   do_pr_state      - Dump raw PR state from tracked repos to $AOPS_SESSIONS/state/
#
# Note: Automated PR-state dumping for task-auto-close is handled here.
# Consumers (like /daily) use the resulting artefact to close the loop.
#
# Usage:
#   ./scripts/repo-sync-cron.sh              # Full: cowork_ingest + gha_sync + transcript + sync + pr_state
#   ./scripts/repo-sync-cron.sh cowork_ingest # Just Cowork audit log ingestion
#   ./scripts/repo-sync-cron.sh gha_sync     # Just GHA artifact sync
#   ./scripts/repo-sync-cron.sh transcript   # Just transcript
#   ./scripts/repo-sync-cron.sh sync         # Just sync
#   ./scripts/repo-sync-cron.sh pr_state     # Just PR state dump
#   ./scripts/repo-sync-cron.sh gha_sync transcript sync # Specific combination
#
# Crontab suggested setup:
#   */5 * * * * /path/to/repo/scripts/repo-sync-cron.sh >> /tmp/repo-sync-cron.log 2>&1

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
            # Strip surrounding quotes (single or double) — .env.local commonly
            # uses export VAR="value" and the quotes must not become part of the value.
            # Use regex via variables to ensure BOTH ends carry the same quote type
            # before stripping (plain parameter expansion would strip mismatched quotes).
            _dq='^"(.*)"$' _sq="^'(.*)'$"
            if   [[ "$value" =~ $_dq ]]; then value="${BASH_REMATCH[1]}"
            elif [[ "$value" =~ $_sq ]]; then value="${BASH_REMATCH[1]}"
            fi
            unset _dq _sq
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

# Required env: must come from ~/.env.local (sourced above) or the cron
# environment. No defaults — silent fallback to $HOME/brain or
# $HOME/.polecat/sessions has bitten us before by writing to the wrong
# repo on machines where these paths differ. See issue #930.
: "${ACA_DATA:?ACA_DATA must be exported (set in ~/.env.local). No default — refusing to guess.}"
: "${AOPS_SESSIONS:?AOPS_SESSIONS must be exported (set in ~/.env.local). No default — refusing to guess.}"

# 2b. Source system paths (CARGO_HOME, UV_CACHE_DIR, Homebrew, GOPATH, etc.)
# Cron doesn't set $USER; .env.system-paths needs it for /opt/$USER paths.
# `whoami` is a syscall, not a literal default — defensible.
export USER="${USER:-$(whoami)}"
[[ -f "$HOME/.env.system-paths" ]] && source "$HOME/.env.system-paths"

export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$HOME/.local/bin:/usr/local/bin:$PATH"

# Git HTTPS auth for cron (no SSH agent available)
# Uses env-based git config so nothing persists to ~/.gitconfig
if [[ -n "${AOPS_BOT_GH_TOKEN:-}" ]]; then
    export GH_TOKEN="${AOPS_BOT_GH_TOKEN}"
    export GIT_CONFIG_COUNT=1
    export GIT_CONFIG_KEY_0="credential.helper"
    export GIT_CONFIG_VALUE_0='!f() { echo "username=x-access-token"; echo "password=${AOPS_BOT_GH_TOKEN}"; }; f'
fi

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

do_cowork_ingest() {
    echo "==> Ingesting Cowork audit logs..."
    if [[ -f "${AOPS}/aops-core/scripts/ingest_cowork.py" ]]; then
        uv run python "${AOPS}/aops-core/scripts/ingest_cowork.py" || echo "Warning: Cowork ingestion failed" >&2
    fi
}

do_gha_sync() {
    # Pull claude-session artifacts from configured GHA repos into
    # $AOPS_SESSIONS/github/. The script invokes transcript.py --no-sync
    # on each downloaded artifact, so transcripts/summaries land before
    # do_transcript runs and the final commit-and-push picks them up.
    echo "==> Syncing GHA claude-session artifacts..."
    if [[ ! -f "${AOPS}/aops-core/scripts/sync_gha_sessions.py" ]]; then
        echo "Warning: sync_gha_sessions.py not found, skipping" >&2
        return 0
    fi
    if ! command -v gh &>/dev/null; then
        echo "skipping gha sync (gh CLI not installed)"
        return 0
    fi
    if ! gh auth status &>/dev/null; then
        echo "skipping gha sync (gh not authed)"
        return 0
    fi
    local gha_repos="${AOPS_GHA_REPOS:-nicsuzor/academicOps}"  # allow-fallback: cron-only convenience for single-repo users; multi-repo users must export AOPS_GHA_REPOS in ~/.env.local
    timeout 300 uv run python "${AOPS}/aops-core/scripts/sync_gha_sessions.py" \
        --repos "$gha_repos" \
        --limit 100 \
        || echo "Warning: gha sync failed or timed out" >&2
}

do_transcript() {
    echo "==> Generating recent transcripts..."
    if [[ -f "${AOPS}/aops-core/scripts/transcript.py" ]]; then
        uv run python "${AOPS}/aops-core/scripts/transcript.py" --recent --no-sync || echo "Warning: transcript generation failed" >&2
    else
        echo "Warning: transcript.py not found" >&2
    fi
}

do_sync() {
    # Sync all configured git repos and bare mirrors via polecat sync
    echo "==> Syncing repositories..."
    uv run --project "${AOPS}" "${AOPS}/polecat/cli.py" sync --quiet 2>&1 || echo "Warning: polecat sync failed"
    # Prune stale remote-tracking refs (branches deleted on remote after squash-merge)
    git -C "${AOPS}" fetch --prune --quiet 2>&1 || echo "Warning: git fetch --prune failed"
}

do_pr_state() {
    # Fetch raw PR data from tracked repos and dump to JSON artefact
    echo "==> Dumping PR state..."
    if [[ -f "${AOPS}/aops-core/scripts/dump_pr_state.py" ]]; then
        uv run python "${AOPS}/aops-core/scripts/dump_pr_state.py" || echo "Warning: PR state dump failed" >&2
    fi
}

# ============================================================================
# Single-instance guard
# ============================================================================
# Cron fires this every 5 min, but a run can take longer than that (transcript
# generation now does per-branch `gh pr list` lookups). Without a guard the runs
# stack and waste CPU + duplicate gh calls. Take a non-blocking exclusive lock on
# fd 9; if a previous run still holds it, skip this cycle cleanly (exit 0). The
# lock auto-releases when this process exits (fd closes). flock(1) is part of
# util-linux and present on the Linux/WSL hosts this cron runs on.
LOCK_FILE="${TMPDIR:-/tmp}/repo-sync-cron.lock"  # allow-fallback: /tmp is the universal POSIX temp dir; lock location is non-critical
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "${TS} repo-sync-cron: previous run still active (${LOCK_FILE}), skipping this cycle" >&2
    exit 0
fi

# ============================================================================
# Dispatch
# ============================================================================

if [[ $# -eq 0 ]]; then
    # Full run: cowork_ingest + gha_sync + transcript + sync + pr_state
    echo "${TS} repo-sync-cron starting (full)"
    do_cowork_ingest
    do_gha_sync
    do_transcript
    do_sync
    do_pr_state
else
    # Named functions: ./repo-sync-cron.sh gha_sync transcript sync
    echo "${TS} repo-sync-cron starting ($*)"
    for func in "$@"; do
        case "$func" in
            cowork_ingest) do_cowork_ingest ;;
            gha_sync)   do_gha_sync ;;
            transcript) do_transcript ;;
            sync)       do_sync ;;
            pr_state)   do_pr_state ;;
            --quick)    do_cowork_ingest; do_gha_sync; do_transcript; do_sync; do_pr_state ;;
            *)          echo "Unknown function: $func (valid: cowork_ingest, gha_sync, transcript, sync, pr_state, --quick)" >&2; exit 1 ;;
        esac
    done
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
