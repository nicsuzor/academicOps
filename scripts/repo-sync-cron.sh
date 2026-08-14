#!/usr/bin/env bash
# repo-sync-cron.sh - Periodic maintenance: transcripts, repo sync.
#
# Composable functions:
#   do_transcript    - Generate recent session transcripts via lib/py/transcripts
#   do_sync          - Fetch and prune the aops repository
#
# Usage:
#   ./scripts/repo-sync-cron.sh              # Full: transcript + sync
#   ./scripts/repo-sync-cron.sh --quick      # Quick run: all functions

set -euo pipefail

# 1. Identify AOPS root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AOPS="${AOPS:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# 1a. Failure alerting.
STATUS_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/repo-sync-cron.status"
mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null || true
# Set by any step that survives its own failure, so the status file does not
# report OK while a step is silently failing every cycle.
SYNC_WARN=0
_now() { date '+%Y-%m-%d %H:%M:%S'; }
fail() {
    local msg="$1"
    echo "$(_now) FATAL: ${msg}" >&2
    echo "FAIL $(_now) ${msg}" > "$STATUS_FILE" 2>/dev/null || true
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"${msg//\"/}\" with title \"repo-sync-cron FAILED\"" >/dev/null 2>&1 || true
    fi
    exit 1
}

# 2. Source environment
if [[ -f "$HOME/.env.local" ]]; then
    while IFS= read -r line; do
        if [[ "$line" =~ ^export[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)= ]]; then
            value="${line#*=}"
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

# 2a. Load secrets
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
_secrets_file="$HOME/dotfiles/secrets/aops-secrets.env"
if command -v sops >/dev/null 2>&1 && [[ -f "$_secrets_file" ]]; then
    if _sops_plain="$(sops -d "$_secrets_file" 2>&1)"; then
        set -a; source /dev/stdin <<< "$_sops_plain"; set +a
    else
        echo "$(_now) WARN: sops failed to decrypt $_secrets_file — secrets NOT loaded: $_sops_plain" >&2
    fi
    unset _sops_plain
fi
unset _secrets_file

# Required env
: "${ACA_DATA:?ACA_DATA must be exported (set in ~/.env.local).}"
: "${AOPS_SESSIONS:?AOPS_SESSIONS must be exported (set in ~/.env.local).}"

# 2b. Source system paths
export USER="${USER:-$(whoami)}"
[[ -f "$HOME/.env.system-paths" ]] && source "$HOME/.env.system-paths"

export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$HOME/.local/bin:/usr/local/bin:$PATH"

# Git HTTPS auth for cron
if [[ -z "${AOPS_BOT_GH_TOKEN:-}" ]]; then
    fail "AOPS_BOT_GH_TOKEN unset after loading ~/.env.local and sops secrets."
fi
_auth_code="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Authorization: token ${AOPS_BOT_GH_TOKEN}" https://api.github.com/user || echo 000)"
if [[ "$_auth_code" != "200" ]]; then
    fail "AOPS_BOT_GH_TOKEN present but GitHub auth returned HTTP ${_auth_code}"
fi
unset _auth_code
export GH_TOKEN="${AOPS_BOT_GH_TOKEN}"
# Force every git subprocess spawned from here — including whatever
# transcripts.runner shells out to for the sessions and brain repos — onto
# HTTPS + token auth. Cron has no SSH agent, so any remote configured with an
# SSH URL (a stray `origin-ssh`, a colleague's clone convention, a submodule)
# fails with "Permission denied (publickey)" on every cycle. The two insteadOf
# entries deliberately share one key: git treats each numbered
# GIT_CONFIG_KEY_n/VALUE_n pair as a separate multi-valued config line.
export GIT_CONFIG_COUNT=3
export GIT_CONFIG_KEY_0="credential.helper"
export GIT_CONFIG_VALUE_0='!f() { echo "username=x-access-token"; echo "password=${AOPS_BOT_GH_TOKEN}"; }; f'
export GIT_CONFIG_KEY_1="url.https://github.com/.insteadOf"
export GIT_CONFIG_VALUE_1="git@github.com:"
export GIT_CONFIG_KEY_2="url.https://github.com/.insteadOf"
export GIT_CONFIG_VALUE_2="ssh://git@github.com/"

# Ensure we are in the AOPS directory for uv run commands
cd "${AOPS}"

# 3. Verify critical dependencies
if ! command -v uv &>/dev/null; then
    echo "Error: 'uv' not found on PATH." >&2
    echo "PATH=$PATH" >&2
    exit 1
fi

TS="$(date '+%Y-%m-%d %H:%M:%S')"

# ============================================================================
# Functions
# ============================================================================

do_transcript() {
    echo "==> Generating recent transcripts using new pipeline..."
    # Call the new transcripts runner. Do NOT pass --no-sync to ensure git commit/push runs.
    PYTHONPATH="${AOPS}/lib/py" uv run python -m transcripts.runner --recent || echo "Warning: transcript generation failed" >&2
}

do_sync() {
    echo "==> Syncing repositories..."
    # NOTE: this used to also shell out to `polecat/cli.py sync`, but that
    # subcommand was never implemented (polecat's cli only exposes `run`) —
    # it always failed with "Error: No such command 'sync'." and was a no-op
    # dead fallback. Removed rather than repaired: there is nothing to call.
    # Name the remote explicitly. A bare `git fetch` resolves to
    # branch.<current-branch>.remote, so a branch tracking a stray remote sends
    # cron down a path it cannot authenticate. `origin` is the remote this
    # script authenticates above.
    if ! git -C "${AOPS}" fetch origin --prune --quiet 2>&1; then
        echo "Warning: git fetch origin --prune failed" >&2
        SYNC_WARN=1
    fi
}

# ============================================================================
# Single-instance guard
# ============================================================================
LOCK_FILE="${TMPDIR:-/tmp}/repo-sync-cron.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "${TS} repo-sync-cron: previous run still active (${LOCK_FILE}), skipping this cycle" >&2
    exit 0
fi

# ============================================================================
# Dispatch
# ============================================================================

if [[ $# -eq 0 ]]; then
    echo "${TS} repo-sync-cron starting (full)"
    do_transcript
    do_sync
else
    echo "${TS} repo-sync-cron starting ($*)"
    for func in "$@"; do
        case "$func" in
            transcript) do_transcript ;;
            sync)       do_sync ;;
            --quick)    do_transcript; do_sync ;;
            *)          echo "Unknown function: $func" >&2; exit 1 ;;
        esac
    done
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') repo-sync-cron done"
if [[ "${SYNC_WARN}" -ne 0 ]]; then
    echo "WARN $(_now) git fetch origin --prune failed" > "$STATUS_FILE" 2>/dev/null || true
else
    echo "OK $(_now)" > "$STATUS_FILE" 2>/dev/null || true
fi
