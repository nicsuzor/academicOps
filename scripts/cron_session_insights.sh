#!/bin/bash
# Cron wrapper: generate transcripts and mine sessions
#
# Pipeline:
#   1. session_status.py --mode cron-transcript → list sessions needing transcripts
#   2. session_transcript.py → generate markdown transcripts
#   3. (future) gemini mining script → extract summaries from transcripts
#
# Called by cron every 5 minutes. Uses flock to prevent concurrent runs.
#
# Exit codes:
#   0 - Success (either processed sessions or nothing to do)
#   1 - Error (missing dependencies, script failure)
#   99 - Another instance is running (lock held)

set -euo pipefail

# Ensure PATH includes uv (cron runs with minimal PATH)
export PATH="/opt/nic/bin:$PATH"

# Change to framework root
cd "$(dirname "$0")/.."
FRAMEWORK_ROOT="$(pwd)"

# Prevent concurrent runs using flock
LOCKFILE="/tmp/cron_session_insights.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Another instance is running. Skipping."
    exit 99
fi

# Release lock on exit (success or error)
cleanup() {
    flock -u 200 2>/dev/null || true
    rm -f "$LOCKFILE" 2>/dev/null || true
}
trap cleanup EXIT

# Source environment from settings.local.json if ACA_DATA not set
if [[ -z "${ACA_DATA:-}" ]]; then
    if [[ -f "$HOME/.claude/settings.local.json" ]]; then
        ACA_DATA=$(jq -r '.env.ACA_DATA // empty' "$HOME/.claude/settings.local.json")
        export ACA_DATA
    fi
fi

# Fail-fast if ACA_DATA still not set
if [[ -z "${ACA_DATA:-}" ]]; then
    echo "ERROR: ACA_DATA not set and not found in settings.local.json" >&2
    exit 1
fi

# Derive project pattern from AOPS or framework root
if [[ -n "${AOPS:-}" ]]; then
    PROJECT_PATTERN=$(basename "$AOPS")
else
    PROJECT_PATTERN=$(basename "$FRAMEWORK_ROOT")
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Checking for sessions needing transcripts (project: $PROJECT_PATTERN)..."

# Step 1: Find sessions needing transcripts
set +e
SESSIONS=$(uv run python scripts/session_status.py --mode cron-transcript --allowed-projects "$PROJECT_PATTERN" 2>&1)
CHECK_EXIT=$?
set -e

if [[ $CHECK_EXIT -eq 1 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - No sessions need transcripts. Done."
    exit 0
elif [[ $CHECK_EXIT -ne 0 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Error checking sessions (exit $CHECK_EXIT): $SESSIONS" >&2
    exit 1
fi

# Count sessions
SESSION_COUNT=$(echo "$SESSIONS" | wc -l)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Found $SESSION_COUNT session(s) needing transcripts"

# Step 2: Generate transcripts for each session
GENERATED=0
SKIPPED=0
FAILED=0

# Minimum session file size to bother transcribing (skip empty/trivial sessions)
MIN_SESSION_SIZE=1000  # bytes

# Maximum transcripts per run (avoid long-running cron jobs)
MAX_TRANSCRIPTS=5

while IFS= read -r session_path; do
    [[ -z "$session_path" ]] && continue

    # Stop after max transcripts
    if [[ $GENERATED -ge $MAX_TRANSCRIPTS ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Reached max transcripts ($MAX_TRANSCRIPTS), stopping"
        break
    fi

    # Skip tiny session files (empty or trivial)
    file_size=$(stat -c%s "$session_path" 2>/dev/null || echo 0)
    if [[ $file_size -lt $MIN_SESSION_SIZE ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping tiny session ($file_size bytes): $session_path"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Transcribing: $session_path"

    # Determine output directory based on source type
    if [[ "$session_path" == *".json" ]]; then
        OUTPUT_DIR="$ACA_DATA/sessions/gemini"
    else
        OUTPUT_DIR="$ACA_DATA/sessions/claude"
    fi
    mkdir -p "$OUTPUT_DIR"

    # Generate transcript (auto-naming, then move to output dir)
    set +e
    cd "$OUTPUT_DIR"
    uv run python "$FRAMEWORK_ROOT/scripts/session_transcript.py" "$session_path" --abridged-only 2>&1
    TRANSCRIPT_EXIT=$?
    cd "$FRAMEWORK_ROOT"
    set -e

    if [[ $TRANSCRIPT_EXIT -eq 0 ]]; then
        GENERATED=$((GENERATED + 1))
    elif [[ $TRANSCRIPT_EXIT -eq 2 ]]; then
        # Exit 2 = skipped (no meaningful content) - don't count toward limit
        SKIPPED=$((SKIPPED + 1))
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to transcribe: $session_path" >&2
        FAILED=$((FAILED + 1))
    fi
done <<< "$SESSIONS"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Transcripts complete: $GENERATED generated, $SKIPPED skipped (tiny), $FAILED failed"

# Step 3: TODO - Add Gemini mining for sessions with transcripts but no summaries
# Only mine transcripts > 1KB (skip empty sessions)
# This will be: session_status.py --mode cron-mining | while read path; do gemini_mine.py "$path"; done

exit 0
