#!/usr/bin/env bash
# brain-sync.sh - Fallback periodic sync for PKB ($ACA_DATA)
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

: "${ACA_DATA:?ACA_DATA environment variable must be set}"
BRAIN_DIR="${ACA_DATA}"
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

# Acquire lock atomically using mkdir (prevents concurrent syncs)
acquire_lock() {
    if mkdir "${LOCK_FILE}.d" 2>/dev/null; then
        echo $$ > "${LOCK_FILE}"
        rmdir "${LOCK_FILE}.d"
        return 0
    fi

    # Check if existing lock is stale
    local pid
    pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        log "INFO" "Sync already running (PID: $pid), exiting"
        exit 0
    fi

    # Stale lock, overwrite it
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
        notes/mobile-captures/*)
            local name
            name=$(basename "${path}" .md | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//')
            echo "capture: ${name//-/ }"
            ;;
        daily/*)
            local base date_part
            base=$(basename "${path}" .md | sed 's/-daily$//')
            if [[ "${base}" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})$ ]]; then
                date_part="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]}"
            else
                date_part="${base}"
            fi
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

    echo "sync: ${count} files (${cat_list})"
}

# Pull with rebase, handling conflicts
pull_rebase() {
    log "INFO" "Pulling with rebase..."

    local pull_output
    if pull_output=$(git pull --rebase origin main 2>&1); then
        return 0
    fi

    # Rebase failed - try abort, stash, pull, stash pop
    log "WARN" "Rebase failed: ${pull_output}"
    log "WARN" "Attempting recovery..."

    git rebase --abort 2>&1 || true

    if ! git stash push -m "brain-sync recovery $(date '+%Y%m%d-%H%M%S')"; then
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
    log "INFO" "Pushing to origin..."

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

# Main sync function
main() {
    if [ ! -d "${BRAIN_DIR}" ]; then
        echo "${BRAIN_DIR} (\$ACA_DATA) does not exist. Please initialise it as a git repository first." >&2
        exit 1
    fi

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

    # Combine all files, remove duplicates and empty entries
    # Use safe array expansion to handle empty arrays with set -u
    local -a all_files unique_files
    all_files=(
        ${changed_files[@]+"${changed_files[@]}"}
        ${staged_files[@]+"${staged_files[@]}"}
        ${untracked_files[@]+"${untracked_files[@]}"}
    )
    mapfile -t unique_files < <(printf '%s\n' "${all_files[@]+"${all_files[@]}"}" | grep -v '^$' | sort -u)

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
