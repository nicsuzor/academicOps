#!/bin/bash
# brain-push.sh - Shared helper for skills to commit and push ~/brain changes
#
# Usage: brain-push.sh "commit message"
#
# Skills should call this after writing to ~/brain to ensure changes are
# committed with a specific message and pushed to origin.
#
# Exit codes:
#   0 - Success
#   1 - No changes to commit (not an error, just nothing to do)
#   2 - Commit failed
#   3 - Push failed (after retry)
#
# See also: brain-sync.sh (fallback for uncommitted changes)

set -euo pipefail

BRAIN_DIR="${HOME}/brain"
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
    if git pull --rebase origin main 2>/dev/null; then
        return 0
    fi

    # Rebase failed - try abort, stash, pull, stash pop
    log "WARN" "Rebase failed, attempting recovery..."

    git rebase --abort 2>/dev/null || true

    if ! git stash push -m "brain-push recovery $(date '+%Y%m%d-%H%M%S')"; then
        log_failure "Failed to stash local changes"
        return 1
    fi

    if ! git pull --rebase origin main; then
        log_failure "Pull failed even after stashing"
        git stash pop 2>/dev/null || true
        return 1
    fi

    if ! git stash pop; then
        log_failure "Stash pop failed - conflict needs manual resolution"
        log_failure "Your changes are in: git stash list"
        return 1
    fi

    return 0
}

# Push with retry on rejection
push_with_retry() {
    if git push origin main 2>/dev/null; then
        return 0
    fi

    # Push rejected - retry once with pull-rebase
    log "WARN" "Push rejected, retrying with pull-rebase..."

    if ! pull_rebase; then
        log_failure "Pull-rebase failed during push retry"
        return 1
    fi

    if git push origin main 2>/dev/null; then
        return 0
    fi

    log_failure "Push failed after retry - giving up"
    return 1
}

main() {
    local message="${1:-}"

    if [ -z "$message" ]; then
        echo "Usage: brain-push.sh \"commit message\"" >&2
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
            # Clean working tree - nothing to commit
            exit 1
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
