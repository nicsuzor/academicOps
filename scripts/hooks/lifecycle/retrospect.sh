#!/bin/bash
# retrospect.sh — Post-merge protocol retrospection
#
# Reads recent session transcripts and task completion notes,
# identifies process-level friction, and delegates to /learn
# when patterns are general enough.
#
# Trigger: post-merge (manual, cron, or git hook)
# Decision logic: NONE — this script only gathers artifacts
# and starts an agent session. The agent makes all judgments.

#<!-- NS: i don't think we need this. replace with a task that is blocked until after merging, and an agent can do all this work. we only need to edit the main workflow to ensure that step is created at the right time. -->
set -euo pipefail

AOPS="${AOPS:-$HOME/src/academicOps}"
WRITING="${WRITING:-$HOME/writing}"
LOOKBACK_HOURS="${LOOKBACK_HOURS:-24}"
PATTERNS_FILE="${WRITING}/data/aops/patterns/pending.md"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --lookback) LOOKBACK_HOURS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Gather recent session transcripts
RECENT_TRANSCRIPTS=$(find "${WRITING}/sessions/claude" -name "*-abridged.md" -mmin -$((LOOKBACK_HOURS * 60)) 2>/dev/null | sort -t/ -k6)

if [ -z "$RECENT_TRANSCRIPTS" ]; then
    echo "RETROSPECT: No transcripts in last ${LOOKBACK_HOURS}h. Nothing to review."
    exit 0
fi

TRANSCRIPT_COUNT=$(echo "$RECENT_TRANSCRIPTS" | wc -l)
echo "RETROSPECT: Found ${TRANSCRIPT_COUNT} transcripts from last ${LOOKBACK_HOURS}h"

if $DRY_RUN; then
    echo "DRY RUN — would start retrospector session with:"
    echo "$RECENT_TRANSCRIPTS"
    exit 0
fi

# Start agent session with retrospector skill
# The agent reads transcripts, extracts observations, applies flexibility gate,
# and delegates to /learn when appropriate.
claude -p "/framework retrospect

Review the ${TRANSCRIPT_COUNT} most recent session transcripts for process-level friction.
Transcript paths:
${RECENT_TRANSCRIPTS}

Pattern accumulator: ${PATTERNS_FILE}

Follow the retrospector protocol."
