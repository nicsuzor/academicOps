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

# 1a. Failure alerting. A silent cron failure (lost credentials + no alerting of
# any kind) once hid a ~24h sync outage. These make failures LOUD: a durable
# status file, a best-effort desktop notification, and a non-zero exit so the run
# stops cleanly instead of churning auth errors and starving other jobs.
STATUS_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/repo-sync-cron.status"
mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null || true
_now() { date '+%Y-%m-%d %H:%M:%S'; }
fail() {
    local msg="$1"
    echo "$(_now) FATAL: ${msg}" >&2
    echo "FAIL $(_now) ${msg}" > "$STATUS_FILE" 2>/dev/null || true
    # Best-effort native notification; harmless no-op off-GUI or on non-macOS.
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"${msg//\"/}\" with title \"repo-sync-cron FAILED\"" >/dev/null 2>&1 || true
    fi
    exit 1
}

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

# 2a. Decrypt sops-managed secrets (AOPS_BOT_GH_TOKEN et al). The interactive
# shell loads these via dotfiles/.zsh/01-env.zsh, but cron is non-interactive and
# never sources it — so without this block cron silently loses every secret. This
# is exactly the regression that broke sync: a shell env-loading refactor moved
# secrets into sops, and cron (still reading only ~/.env.local) lost the bot
# token. Keep this in sync with 01-env.zsh: same secrets path, same age key.
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
_secrets_file="$HOME/dotfiles/secrets/aops-secrets.env"
if command -v sops >/dev/null 2>&1 && [[ -f "$_secrets_file" ]]; then
    if _sops_plain="$(sops -d "$_secrets_file" 2>&1)"; then
        # Use a here-string, NOT process substitution: `source <(...)` silently
        # fails in a stripped cron environment (no usable /dev/fd), leaving every
        # secret unset — which is precisely how this breaks without a peep.
        set -a; source /dev/stdin <<< "$_sops_plain"; set +a
    else
        echo "$(_now) WARN: sops failed to decrypt $_secrets_file — secrets NOT loaded: $_sops_plain" >&2
    fi
    unset _sops_plain
fi
unset _secrets_file

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
# Uses env-based git config so nothing persists to ~/.gitconfig.
# Fail LOUD on missing/invalid credentials rather than running blind: without a
# working token every git/gh call 401s, the run churns retries, holds the shared
# flock, and starves the hourly job — silently, for as long as it takes someone
# to notice. Refuse to proceed instead.
if [[ -z "${AOPS_BOT_GH_TOKEN:-}" ]]; then
    fail "AOPS_BOT_GH_TOKEN unset after loading ~/.env.local and sops secrets. Check that secrets/aops-secrets.env decrypts and defines it, and that ~/.config/sops/age/keys.txt is readable by cron."
fi
# A present-but-expired token is the other way this breaks silently — one cheap
# call catches it before we do any real work.
_auth_code="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Authorization: token ${AOPS_BOT_GH_TOKEN}" https://api.github.com/user || echo 000)"
if [[ "$_auth_code" != "200" ]]; then
    fail "AOPS_BOT_GH_TOKEN present but GitHub auth returned HTTP ${_auth_code} (expired/revoked?). Rotate it in secrets/aops-secrets.env."
fi
unset _auth_code
export GH_TOKEN="${AOPS_BOT_GH_TOKEN}"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="credential.helper"
export GIT_CONFIG_VALUE_0='!f() { echo "username=x-access-token"; echo "password=${AOPS_BOT_GH_TOKEN}"; }; f'

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
echo "OK $(_now)" > "$STATUS_FILE" 2>/dev/null || true
