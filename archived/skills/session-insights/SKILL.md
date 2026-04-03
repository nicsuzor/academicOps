---
name: session-insights
type: skill
category: analysis
description: Generate comprehensive session insights from transcripts using a Claude subagent
triggers:
  - "session summary"
  - "generate insights"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Bash,Read,Write,Agent,mcp__pkb__create_memory
version: 4.0.0
tags:
  - analysis
  - insights
---

# Session Insights (Claude-native Post-hoc Analysis)

> **Taxonomy note**: This skill provides domain expertise (HOW) for generating session insights from transcripts. See [[TAXONOMY.md]] for the skill/workflow distinction.

Generate comprehensive session insights from transcripts using a Claude subagent.

## Overview

This skill analyzes Claude Code session transcripts to extract structured insights including:

- Summary and accomplishments
- Learning observations and skill compliance
- Context gaps and user satisfaction
- Conversation flow and verbatim prompts

Insights are saved to `$ACA_DATA/../sessions/summaries/YYYYMMDD-{session_id}.json` using the unified schema (combining insights + dashboard data).

## Usage

### Analyze Current Session

```bash
/session-insights
```

Generates insights for the current session.

### Analyze Specific Session

```bash
/session-insights {session_id}
```

Where `{session_id}` is an 8-character session hash (e.g., `a1b2c3d4`).

### Batch Mode

```bash
/session-insights batch
```

Processes up to 5 sessions that have transcripts but no insights yet.

## Workflow

### Step 1: Check if Insights Already Exist

```bash
SESSION_ID="a1b2c3d4"
DATE="20260113"  # Extract from transcript filename (YYYYMMDD format)
INSIGHTS_FILE="$ACA_DATA/../sessions/summaries/${DATE}-${SESSION_ID}.json"

if [ -f "$INSIGHTS_FILE" ]; then
    echo "⚠️  Insights already exist for session ${SESSION_ID}"
    echo "Generated: $(jq -r '.date' "$INSIGHTS_FILE")"
    echo "Summary: $(jq -r '.summary' "$INSIGHTS_FILE")"
    echo ""
    echo "Update/Merge with existing? (yes/no)"
    # Ask user - if no, exit
fi
```

**Important**: DO NOT overwrite existing insights without user confirmation.

### Step 2: Locate Transcript

Transcripts are typically stored in:

- `$ACA_DATA/../sessions/claude/{transcript}.md` (Claude sessions)
- `$ACA_DATA/../sessions/gemini/{transcript}.md` (Gemini sessions)

Transcript filename format: `YYYYMMDD-{project}-{session_id}-{suffix}.md`

```bash
# Find transcript for session
TRANSCRIPT=$(find "$ACA_DATA/../sessions/claude" -name "*-${SESSION_ID}-*.md" | head -1)

if [ -z "$TRANSCRIPT" ]; then
    echo "❌ No transcript found for session ${SESSION_ID}"
    echo "Transcript should be in: $ACA_DATA/../sessions/claude/"
    echo ""
    echo "Generate transcript now? (yes/no)"
    # If yes, continue to Step 2a
    exit 1
fi

echo "✓ Found transcript: $(basename "$TRANSCRIPT")"
```

### Step 2a: Generate Transcript (if missing)

If transcript doesn't exist, generate it using transcript_push.py:

```bash
# Find session file in Claude Code session directory
# Session files are in ~/.claude/projects/{project}/{date}-{hash}/
SESSION_PROJECT=$(pwd | tr '/' '-' | sed 's/^-//')
SESSION_DIR="$HOME/.claude/projects/-${SESSION_PROJECT}"

# Find session directory by session ID
SESSION_PATH=$(find "$SESSION_DIR" -name "*.jsonl" -path "*${SESSION_ID}*" | head -1)

if [ -z "$SESSION_PATH" ]; then
    echo "❌ No session file found for ${SESSION_ID}"
    echo "Session should be in: $SESSION_DIR"
    exit 1
fi

echo "Generating transcript from: $SESSION_PATH"

# Generate transcript
cd "$AOPS" && uv run python aops-core/scripts/transcript_push.py "$SESSION_PATH"

# Transcript is now in $ACA_DATA/../sessions/claude/
TRANSCRIPT=$(find "$ACA_DATA/../sessions/claude" -name "*-${SESSION_ID}-*.md" | head -1)
```

### Step 3: Extract Metadata from Transcript Filename

Parse the transcript filename to extract metadata. The filename format is `YYYYMMDD-{project}-{session_id}-{suffix}.md`.

```bash
BASENAME=$(basename "$TRANSCRIPT" .md)
DATE=$(echo "$BASENAME" | cut -d'-' -f1)
SESSION_ID=$(echo "$BASENAME" | rev | cut -d'-' -f2 | rev)  # second-to-last segment
# Handle both YYYYMMDD and YYYYMMDD-HH formats
if [[ "$BASENAME" =~ ^[0-9]{8}-[0-9]{2}- ]]; then
    PROJECT=$(echo "$BASENAME" | cut -d'-' -f3- | rev | cut -d'-' -f3- | rev)
else
    PROJECT=$(echo "$BASENAME" | cut -d'-' -f2- | rev | cut -d'-' -f3- | rev)
fi
```

### Step 4: Launch Claude Subagent for Analysis

Launch a Claude subagent to analyze the transcript. The subagent:

1. Reads the prompt template from `specs/session-insights-prompt.md`
2. Reads the transcript file
3. Substitutes `{session_id}`, `{date}`, `{project}` placeholders with the extracted metadata
4. Analyzes the transcript following the prompt template instructions
5. Writes the resulting JSON directly to the summaries directory

**Agent prompt** (pass all of this to the subagent):

```
You are a session insights extraction agent. Your job is to analyze a session transcript and produce structured JSON insights.

## Instructions

1. Read the prompt template at: specs/session-insights-prompt.md
2. Read the transcript at: {TRANSCRIPT}
3. Use these metadata values EXACTLY:
   - session_id: {SESSION_ID}
   - date: {DATE}
   - project: {PROJECT}
4. Follow the prompt template to analyze the transcript and produce the JSON output
5. Use the Write tool to save the JSON output to: $ACA_DATA/../sessions/summaries/{INSIGHTS_FILE}

Output ONLY valid JSON — no markdown fences, no commentary.
```

**Error Handling**:

- If the subagent fails to produce valid JSON, proceed to Step 5 for validation and retry
- If the transcript is too large, suggest using an abridged transcript (if available)

### Step 5: Validate Output

After the subagent writes the JSON file, validate it:

```python
import sys
import os
import json
from lib.insights_generator import validate_insights_schema, InsightsValidationError

insights_file = os.environ.get('INSIGHTS_FILE', '')
with open(insights_file) as f:
    data = json.load(f)

try:
    validate_insights_schema(data)
except InsightsValidationError as e:
    # Re-run the subagent with the validation errors included in the prompt
    # Ask it to fix the specific issues
    print(f'Validation failed: {e}')
    pass
```

**Known issue**: Approximately 13% of extractions produce null values for required fields (`summary`, `outcome`, `accomplishments`). When validation fails, re-launch the subagent with the validation errors appended to the prompt and ask it to fix only the failing fields while preserving everything else.

### Step 6: Confirm File Written

The subagent writes the insights file directly. Verify:

```bash
if [ -f "$INSIGHTS_FILE" ]; then
    echo "✓ Insights written to: $INSIGHTS_FILE"
else
    echo "❌ Insights file not created"
    exit 1
fi
```

### Step 6.5: Sync to PKB

Sync key insights to PKB for semantic search:

```python
# Extract summary content for memory
summary = insights.get('summary', '')
accomplishments = insights.get('accomplishments', [])
learning_obs = insights.get('learning_observations', [])
proposed_changes = insights.get('proposed_changes', [])

# Build memory content - concise for embeddings
memory_content = f"""Session {session_id} ({date}): {summary}

Accomplishments: {', '.join(accomplishments[:5]) if accomplishments else 'None recorded'}

Key learnings: {'; '.join([obs.get('evidence', '')[:100] for obs in learning_obs[:3]]) if learning_obs else 'None'}

Proposed changes: {', '.join(proposed_changes[:3]) if proposed_changes else 'None'}"""

# Sync to PKB
mcp__pkb__create_memory(
    title=f"Session insights: {session_id}",
    body=memory_content,
    tags=["session-insights", f"session-{session_id}", project]
)
```

**Why sync to memory**: Enables semantic search for past session learnings (e.g., "what did we learn about testing?" or "sessions where auth was worked on").

**What gets synced**:

- Summary (what was worked on)
- Accomplishments (concrete deliverables)
- Learning observations (key insights only, truncated)
- Proposed changes (framework improvements)

**What stays in JSON only**:

- Full learning observation details
- Conversation flow
- Verbatim prompts
- Operational metrics

### Step 7: Display Summary

```bash
# Show user-friendly summary
SESSION_ID=$(jq -r '.session_id' "$INSIGHTS_FILE")
SUMMARY=$(jq -r '.summary' "$INSIGHTS_FILE")
OUTCOME=$(jq -r '.outcome' "$INSIGHTS_FILE")
ACCOMPLISHMENTS=$(jq -r '.accomplishments | length' "$INSIGHTS_FILE")
OBSERVATIONS=$(jq -r '.learning_observations | length' "$INSIGHTS_FILE")

echo ""
echo "✓ Session Insights Generated"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Session:         $SESSION_ID"
echo "Summary:         $SUMMARY"
echo "Outcome:         $OUTCOME"
echo "Accomplishments: $ACCOMPLISHMENTS"
echo "Learnings:       $OBSERVATIONS"
echo "Memory synced:   Yes"
echo ""
echo "Full insights: $INSIGHTS_FILE"
```

## Batch Mode Workflow

When invoked with `batch`:

```bash
# 1. Find sessions with transcripts but no insights
PENDING_SESSIONS=$(cd "$AOPS" && PYTHONPATH=aops-core uv run python \
    aops-core/skills/session-insights/scripts/find_pending.py \
    --limit 5)

# 2. Process up to 5 sessions
COUNT=0
MAX=5

while IFS='|' read -r TRANSCRIPT SESSION_ID DATE; do
    if [ $COUNT -ge $MAX ]; then
        break
    fi

    echo "Processing session $SESSION_ID..."
    # Run Steps 3-7 for this session
    # (same as single session workflow)

    COUNT=$((COUNT + 1))
done <<< "$PENDING_SESSIONS"

echo ""
echo "✓ Batch processing complete: $COUNT sessions"
```

## Error Handling

### Transcript Missing

```
❌ No transcript found for session a1b2c3d4

Transcript should be in: $ACA_DATA/../sessions/claude/

Generate transcript now? (yes/no)
> yes

Generating transcript...
✓ Transcript generated
Continuing with insights generation...
```

### Subagent Timeout

```
❌ Subagent timed out

The transcript may be too long. Try one of:
1. Use an abridged transcript (if available)
2. Retry with a shorter context window
3. Process manually with smaller chunks

Transcript: /path/to/transcript.md (125 KB)
```

### Invalid JSON Output

```
❌ Subagent produced invalid JSON

Validation errors:
- Missing required field: summary
- outcome must be one of: success, partial, failure

Retrying with validation feedback...
```

### File Exists

```
⚠️  Insights already exist for session a1b2c3d4
Generated: 2026-01-13
Summary: Created unified session insights architecture

Regenerate? (yes/no)
> no

Aborted. Existing insights preserved.
```

## Tips

**For Large Transcripts**: If the subagent times out, consider:

- Using abridged transcripts (created by transcript_push.py - generates both full and abridged versions)
- Breaking the analysis into chunks
- Using a faster model (but may sacrifice quality)

**For Better Quality**:

- Ensure transcripts include all context (not truncated)
- Review generated insights and provide feedback
- Map corrections to framework heuristics (H2, H3, H4, etc.)

**For Debugging**:

- Check the insights JSON for validation errors
- Verify transcript format matches expected structure
- Ensure ACA_DATA environment variable is set correctly

## Integration with Framework

Generated insights are:

- Used by audit tools to track framework effectiveness
- Analyzed for trend detection (skill compliance, user satisfaction)
- Fed into learning loop for framework improvements
- Stored long-term in ACA_DATA research repository

## See Also

- `/audit` skill - Framework health auditing
- `aops-core/scripts/transcript_push.py` - Transcript generation + reflection extraction
- `specs/session-insights-prompt.md` - Shared prompt template
- `aops-core/lib/insights_generator.py` - Generation library (validation utilities)
