#!/usr/bin/env bash
# repo-sync-cron.sh - Periodic maintenance: transcripts and repo sync
#
# Two functions, composable via CLI:
#   do_transcript - Generate recent session transcripts
#   do_sync       - Sync all git repositories via polecat sync
#
# Usage:
#   ./scripts/repo-sync-cron.sh              # Full: transcript + sync
#   ./scripts/repo-sync-cron.sh transcript   # Just transcript
#   ./scripts/repo-sync-cron.sh sync         # Just sync
#   ./scripts/repo-sync-cron.sh transcript sync  # Specific combination
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

export ACA_DATA="${ACA_DATA:-$HOME/brain}"
export AOPS_SESSIONS="${AOPS_SESSIONS:-${POLECAT_HOME:-$HOME/.polecat}/sessions}"
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
}

# ============================================================================
# Dispatch
# ============================================================================

if [[ $# -eq 0 ]]; then
    # Full run: transcript + sync
    echo "${TS} repo-sync-cron starting (full)"
    do_transcript
    do_sync
else
    # Named functions: ./repo-sync-cron.sh transcript sync
    echo "${TS} repo-sync-cron starting ($*)"
    for func in "$@"; do
        case "$func" in
            transcript) do_transcript ;;
            sync)       do_sync ;;
            *)          echo "Unknown function: $func (valid: transcript, sync)" >&2; exit 1 ;;
        esac
    done
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
