#!/bin/bash
# brain-sync.sh - Fallback periodic sync for ~/brain
#
# Commits dirty working tree with meaningful commit messages derived from
# changed file paths, then pushes to origin with rebase-based conflict handling.
#
# Designed to run via systemd timer or cron every 5 minutes.
# Skills should commit with specific messages; this is the fallback for
# manual edits or skills that don't commit.
#
# See also: brain-push.sh (shared helper for skills)

set -euo pipefail

BRAIN_DIR="${HOME}/brain"
LOG_FILE="${BRAIN_DIR}/.sync-failures.log"
LOCK_FILE="${BRAIN_DIR}/.sync.lock"

# Logging helper
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "${LOG_FILE}"
}

log_failure() {
    log "ERROR" "$@"
}

# Cleanup on exit
cleanup() {
    rm -f "${LOCK_FILE}"
}
trap cleanup EXIT

# Acquire lock (prevent concurrent syncs)
acquire_lock() {
    if [ -f "${LOCK_FILE}" ]; then
        local pid
        pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log "INFO" "Sync already running (PID: $pid), exiting"
            exit 0
        fi
        # Stale lock, remove it
        rm -f "${LOCK_FILE}"
    fi
    echo $$ > "${LOCK_FILE}"
}

# Map file path to commit message category
path_to_category() {
    local path="$1"

    case "$path" in
        knowledge/tech/*)
            local name
            name=$(basename "${path}" .md)
            echo "knowledge: tech/${name}"
            ;;
        knowledge/*)
            local topic
            topic=$(dirname "${path}" | sed 's|^knowledge/||')
            local name
            name=$(basename "${path}" .md)
            if [ -n "$topic" ] && [ "$topic" != "." ]; then
                echo "knowledge: ${topic}/${name}"
            else
                echo "knowledge: ${name}"
            fi
            ;;
        aops/tasks/*)
            local task_id
            task_id=$(basename "${path}" .md)
            echo "task: ${task_id}"
            ;;
        daily/*)
            local date_part
            date_part=$(basename "${path}" .md | sed 's/-daily$//' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/')
            echo "daily: ${date_part}"
            ;;
        projects/*)
            local proj
            proj=$(echo "${path}" | sed 's|^projects/||' | cut -d/ -f1)
            echo "project: ${proj}"
            ;;
        context/*)
            local ctx
            ctx=$(basename "${path}" .md)
            echo "context: ${ctx}"
            ;;
        goals/*)
            local goal
            goal=$(basename "${path}" .md)
            echo "goal: ${goal}"
            ;;
        academic/*)
            local acad
            acad=$(basename "${path}" .md)
            echo "academic: ${acad}"
            ;;
        archive/*)
            echo "archive"
            ;;
        *)
            # Default: use first directory or filename
            local first_dir
            first_dir=$(echo "${path}" | cut -d/ -f1)
            echo "${first_dir}"
            ;;
    esac
}

# Generate commit message from changed files
generate_commit_message() {
    local files=("$@")
    local count=${#files[@]}

    if [ "$count" -eq 0 ]; then
        echo "sync: empty commit"
        return
    fi

    if [ "$count" -eq 1 ]; then
        path_to_category "${files[0]}"
        return
    fi

    # Multiple files: group by category
    local -A categories
    for file in "${files[@]}"; do
        local cat
        cat=$(path_to_category "$file" | cut -d: -f1)
        categories["$cat"]=1
    done

    local cat_list
    cat_list=$(printf '%s\n' "${!categories[@]}" | sort | tr '\n' ', ' | sed 's/, $//')

    if [ "$count" -le 3 ]; then
        # Few files: list them
        echo "sync: ${count} files (${cat_list})"
    else
        echo "sync: ${count} files (${cat_list})"
    fi
}

# Pull with rebase, handling conflicts
pull_rebase() {
    log "INFO" "Pulling with rebase..."

    if git pull --rebase origin main 2>/dev/null; then
        return 0
    fi

    # Rebase failed - try abort, stash, pull, stash pop
    log "WARN" "Rebase failed, attempting recovery..."

    git rebase --abort 2>/dev/null || true

    if ! git stash push -m "brain-sync recovery $(date '+%Y%m%d-%H%M%S')"; then
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
    log "INFO" "Pushing to origin..."

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

# Main sync function
main() {
    cd "${BRAIN_DIR}" || {
        log_failure "Cannot cd to ${BRAIN_DIR}"
        exit 1
    }

    acquire_lock

    # Check if working tree is dirty
    if git diff --quiet && git diff --cached --quiet; then
        # Check for untracked files
        local untracked
        untracked=$(git ls-files --others --exclude-standard 2>/dev/null | head -1)
        if [ -z "$untracked" ]; then
            # Clean - nothing to do
            exit 0
        fi
    fi

    log "INFO" "Working tree is dirty, starting sync..."

    # Get list of changed/new files
    local -a changed_files
    mapfile -t changed_files < <(git diff --name-only 2>/dev/null)

    local -a staged_files
    mapfile -t staged_files < <(git diff --cached --name-only 2>/dev/null)

    local -a untracked_files
    mapfile -t untracked_files < <(git ls-files --others --exclude-standard 2>/dev/null)

    # Combine all files
    local -a all_files=("${changed_files[@]}" "${staged_files[@]}" "${untracked_files[@]}")

    # Remove duplicates and empty entries
    local -a unique_files
    mapfile -t unique_files < <(printf '%s\n' "${all_files[@]}" | grep -v '^$' | sort -u)

    if [ ${#unique_files[@]} -eq 0 ]; then
        log "INFO" "No files to commit"
        exit 0
    fi

    # Generate commit message
    local message
    message=$(generate_commit_message "${unique_files[@]}")

    log "INFO" "Committing ${#unique_files[@]} file(s): ${message}"

    # Stage all changes
    git add -A

    # Commit
    if ! git commit -m "${message}"; then
        log_failure "Commit failed"
        exit 1
    fi

    # Pull-rebase and push
    if ! pull_rebase; then
        log_failure "Pull-rebase failed"
        exit 1
    fi

    if ! push_with_retry; then
        log_failure "Push failed"
        exit 1
    fi

    log "INFO" "Sync complete: ${message}"
}

main "$@"
