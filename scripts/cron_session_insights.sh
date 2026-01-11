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

# Source nvm and activate node (required for gemini CLI)
# Try standard locations for nvm (use ${USER:-} to handle unset USER in cron)
for nvm_path in "/opt/${USER:-$(id -un)}/nvm" "$HOME/.nvm" "/opt/nvm"; do
    if [[ -s "$nvm_path/nvm.sh" ]]; then
        export NVM_DIR="$nvm_path"
        # shellcheck source=/dev/null
        source "$NVM_DIR/nvm.sh"
        nvm use node >/dev/null 2>&1 || true
        break
    fi
done

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

    # Generate transcript (auto-naming, output to OUTPUT_DIR)
    set +e
    cd "$OUTPUT_DIR"
    uv run python "$FRAMEWORK_ROOT/scripts/session_transcript.py" "$session_path" 2>&1
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

# Step 3: Mine transcripts with Gemini to extract session summaries
echo "$(date '+%Y-%m-%d %H:%M:%S') - Checking for sessions needing mining..."

set +e
MINING_SESSIONS=$(uv run python scripts/session_status.py --mode cron-mining --allowed-projects "$PROJECT_PATTERN" 2>&1)
MINING_EXIT=$?
set -e

if [[ $MINING_EXIT -eq 1 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - No sessions need mining. Done."
    exit 0
elif [[ $MINING_EXIT -ne 0 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Error checking mining sessions (exit $MINING_EXIT): $MINING_SESSIONS" >&2
    exit 1
fi

MINING_COUNT=$(echo "$MINING_SESSIONS" | wc -l)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Found $MINING_COUNT session(s) needing mining"

MINED=0
MINE_FAILED=0
MAX_MINING=3  # Limit mining per run (Gemini calls are slow)

# Minimum transcript size to bother mining
MIN_TRANSCRIPT_SIZE=1000  # bytes

while IFS= read -r transcript_path; do
    [[ -z "$transcript_path" ]] && continue

    # Stop after max mining
    if [[ $MINED -ge $MAX_MINING ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Reached max mining ($MAX_MINING), stopping"
        break
    fi

    # Skip tiny transcripts
    file_size=$(stat -c%s "$transcript_path" 2>/dev/null || echo 0)
    if [[ $file_size -lt $MIN_TRANSCRIPT_SIZE ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping tiny transcript ($file_size bytes): $transcript_path"
        continue
    fi

    # Extract metadata from filename: YYYYMMDD-{project}-{session_id}-{slug}-abridged.md
    filename=$(basename "$transcript_path")
    date_raw="${filename:0:8}"
    # Format date as YYYY-MM-DD
    date_formatted="${date_raw:0:4}-${date_raw:4:2}-${date_raw:6:2}"
    # Extract session_id (8 hex chars after project name)
    session_id=$(echo "$filename" | sed 's/.*-\([a-f0-9]\{8\}\)-.*/\1/')
    # Extract project (between date and session_id)
    without_date="${filename:9}"
    project=$(echo "$without_date" | sed "s/-$session_id.*//")

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Mining: $transcript_path (session: $session_id, project: $project)"

    # Ensure output directory exists
    mkdir -p "$ACA_DATA/dashboard/sessions"

    # Build prompt with substitutions (correct path to insights.md)
    PROMPT=$(cat "$FRAMEWORK_ROOT/skills/session-insights/insights.md" | \
        sed "s/{session_id}/$session_id/g" | \
        sed "s/{date}/$date_formatted/g" | \
        sed "s/{project}/$project/g")

    # Call Gemini to mine the transcript
    # Run from transcript directory so Gemini can access the file
    # Disable MCP servers for headless execution
    OUTPUT_FILE="$ACA_DATA/dashboard/sessions/$session_id.json"
    TRANSCRIPT_DIR=$(dirname "$transcript_path")
    TEMP_OUTPUT=$(mktemp)

    set +e
    cd "$TRANSCRIPT_DIR"
    gemini -y --allowed-mcp-server-names "" "$PROMPT

@$(basename "$transcript_path")" > "$TEMP_OUTPUT" 2>&1
    GEMINI_EXIT=$?
    cd "$FRAMEWORK_ROOT"
    set -e

    if [[ $GEMINI_EXIT -eq 0 ]]; then
        # Extract JSON from markdown code block if present
        if grep -q '```json' "$TEMP_OUTPUT"; then
            sed -n '/```json/,/```/p' "$TEMP_OUTPUT" | sed '1d;$d' > "$OUTPUT_FILE"
        else
            # Try using output directly
            cp "$TEMP_OUTPUT" "$OUTPUT_FILE"
        fi
        rm -f "$TEMP_OUTPUT"

        # Validate JSON output
        if jq empty "$OUTPUT_FILE" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Mined successfully: $session_id"
            MINED=$((MINED + 1))
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Invalid JSON output for: $session_id" >&2
            rm -f "$OUTPUT_FILE"
            MINE_FAILED=$((MINE_FAILED + 1))
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Gemini failed for: $session_id (exit $GEMINI_EXIT)" >&2
        cat "$TEMP_OUTPUT" >&2
        rm -f "$TEMP_OUTPUT" "$OUTPUT_FILE"
        MINE_FAILED=$((MINE_FAILED + 1))
    fi
done <<< "$MINING_SESSIONS"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Mining complete: $MINED mined, $MINE_FAILED failed"

exit 0
