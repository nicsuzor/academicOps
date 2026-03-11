#!/usr/bin/env bash
# brain-push.sh - Shared helper for skills to commit and push PKB changes
#
# Usage: brain-push.sh "commit message"
#
# Skills should call this after writing to $ACA_DATA to ensure changes are
# committed with a specific message and pushed to origin.
#
# Exit codes:
#   0 - Success (including "nothing to commit")
#   2 - Commit failed
#   3 - Push failed (after retry)
#
# See also: brain-sync.sh (fallback for uncommitted changes)

set -euo pipefail

: "${ACA_DATA:?ACA_DATA environment variable must be set}"
BRAIN_DIR="${ACA_DATA}"
LOG_FILE="${BRAIN_DIR}/.sync-failures.log"

# Logging helper
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "${LOG_FILE}"
}

log_failure() {
    log "ERROR" "$@"
}

# Pull with rebase, handling conflicts
pull_rebase() {
    local pull_output
    if pull_output=$(git pull --rebase origin main 2>&1); then
        return 0
    fi

    # Rebase failed - try abort, stash, pull, stash pop
    log "WARN" "Rebase failed: ${pull_output}"
    log "WARN" "Attempting recovery..."

    git rebase --abort 2>&1 || true

    if ! git stash push -m "brain-push recovery $(date '+%Y%m%d-%H%M%S')"; then
        log_failure "Failed to stash local changes"
        return 1
    fi

    local pull2_output
    if ! pull2_output=$(git pull --rebase origin main 2>&1); then
        log_failure "Pull failed even after stashing: ${pull2_output}"
        git stash pop 2>&1 || true
        return 1
    fi

    if ! git stash pop; then
        log_failure "Stash pop failed - conflict needs manual resolution"
        log_failure "Your changes are preserved in the stash (see: git stash list)"
        log_failure "Next steps: run 'git status', resolve conflicts, then 'git stash apply' to re-apply"
        return 1
    fi

    return 0
}

# Push with retry on rejection
push_with_retry() {
    local push_output
    if push_output=$(git push origin main 2>&1); then
        return 0
    fi

    # Push rejected - retry once with pull-rebase
    log "WARN" "Push rejected (${push_output}), retrying with pull-rebase..."

    if ! pull_rebase; then
        log_failure "Pull-rebase failed during push retry"
        return 1
    fi

    if push_output=$(git push origin main 2>&1); then
        return 0
    fi

    log_failure "Push failed after retry - giving up: ${push_output}"
    return 1
}

main() {
    local message="${1:-}"

    if [ -z "$message" ]; then
        echo "Usage: brain-push.sh \"commit message\"" >&2
        exit 2
    fi

    if [ ! -d "${BRAIN_DIR}" ]; then
        echo "${BRAIN_DIR} (\$ACA_DATA) does not exist. Please initialise it as a git repository first." >&2
        exit 2
    fi

    cd "${BRAIN_DIR}" || {
        log_failure "Cannot cd to ${BRAIN_DIR}"
        exit 2
    }

    # Check if there are changes to commit
    if git diff --quiet && git diff --cached --quiet; then
        local untracked
        untracked=$(git ls-files --others --exclude-standard 2>/dev/null | head -1)
        if [ -z "$untracked" ]; then
            # Clean working tree - nothing to commit (not an error)
            exit 0
        fi
    fi

    # Stage all changes
    git add -A

    # Commit with provided message
    if ! git commit -m "${message}"; then
        log_failure "Commit failed: ${message}"
        exit 2
    fi

    # Pull-rebase first to reduce push rejection
    if ! pull_rebase; then
        log_failure "Pull-rebase failed before push"
        exit 3
    fi

    # Push with retry
    if ! push_with_retry; then
        log_failure "Push failed: ${message}"
        exit 3
    fi

    log "INFO" "Pushed: ${message}"
    exit 0
}

main "$@"
