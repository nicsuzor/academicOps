---
name: session-insights
category: analysis
description: Generate comprehensive session insights from transcripts using Gemini
allowed-tools: Bash,Read,Write,~~ai-assistant,mcp__pkb__create_memory
version: 3.1.0
tags:
  - analysis
  - gemini
  - insights
  - sessions
  - memory
---

# Session Insights (Gemini Post-hoc Analysis)

Generate comprehensive session insights from transcripts using Gemini Flash 2.0.

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

### Step 3: Extract Metadata and Prepare Prompt

```bash
# Use prepare_prompt.py to extract metadata and prepare prompt
PROMPT=$(cd "$AOPS" && PYTHONPATH=aops-core uv run python \
    aops-core/skills/session-insights/scripts/prepare_prompt.py \
    "$TRANSCRIPT")

if [ $? -ne 0 ]; then
    echo "❌ Failed to prepare prompt"
    exit 1
fi

echo "✓ Prompt prepared with metadata substituted"
```

The prepare_prompt.py script:

- Extracts `session_id`, `date`, `project` from transcript filename
- Loads shared template from `aops-core/specs/session-insights-prompt.md`
- Substitutes `{session_id}`, `{date}`, `{project}` placeholders
- Returns prepared prompt

### Step 4: Call Gemini

Use Gemini Flash 2.0 for fast, cost-effective analysis:

```bash
# Prepare full prompt with transcript reference
FULL_PROMPT="${PROMPT}

## Session Transcript

@${TRANSCRIPT}

Generate insights JSON now:"

# Call Gemini via MCP
# Note: The transcript will be loaded via the @{path} syntax
```

Now call ~~ai-assistant with the full prompt:

```python
# Tool call (conceptual - use whatever ~~ai-assistant connector is available)
result = ~~ai-assistant.ask(
    prompt=FULL_PROMPT,
    timeout=120  # 2 minutes
)
```

**Error Handling**:

- If timeout (> 120s): Suggest using abridged transcript
- If API error: Show error message, suggest retry
- If rate limit: Show message, suggest waiting

### Step 5: Parse and Validate JSON

```bash
# Extract JSON from Gemini response (may be in markdown fence)
# Validate and normalize using process_response.py

INSIGHTS_JSON=$(echo "$GEMINI_RESPONSE" | (cd "$AOPS" && PYTHONPATH=aops-core uv run python \
    aops-core/skills/session-insights/scripts/process_response.py \
    "$DATE" "$SESSION_ID"))

if [ $? -ne 0 ]; then
    # Error details are printed to stderr and debug file by the script
    echo "❌ Failed to process insights response"
    exit 1
fi
```

If JSON is invalid:

- Save raw response to `$ACA_DATA/../sessions/summaries/YYYYMMDD-{session_id}.debug.txt`
- Show error message with path to debug file
- Exit with error

### Step 6: Update Insights File

```bash
# Merge and write insights using merge_insights.py
echo "$INSIGHTS_JSON" | (cd "$AOPS" && PYTHONPATH=aops-core uv run python \
    aops-core/skills/session-insights/scripts/merge_insights.py \
    "$INSIGHTS_FILE")

if [ $? -ne 0 ]; then
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

### Gemini Timeout

```
❌ Gemini call timed out after 120 seconds

The transcript may be too long. Try one of:
1. Use an abridged transcript (if available)
2. Retry with a shorter context window
3. Process manually with smaller chunks

Transcript: /path/to/transcript.md (125 KB)
```

### Invalid JSON Response

```
❌ Gemini returned invalid JSON

Error: Expecting ',' delimiter: line 15 column 5 (char 432)

Raw response saved to:
$ACA_DATA/../sessions/summaries/20260113-a1b2c3d4.debug.txt

Please review and report if this is a bug.
```

### File Exists

```
⚠️  Insights already exist for session a1b2c3d4
Generated: 2026-01-13
Summary: Created unified session insights architecture

Regenerate with Gemini? (yes/no)
> no

Aborted. Existing insights preserved.
```

## Tips

**For Large Transcripts**: If Gemini times out, consider:

- Using abridged transcripts (created by transcript_push.py - generates both full and abridged versions)
- Breaking the analysis into chunks
- Using a faster model (but may sacrifice quality)

**For Better Quality**:

- Ensure transcripts include all context (not truncated)
- Review generated insights and provide feedback
- Map corrections to framework heuristics (H2, H3, H4, etc.)

**For Debugging**:

- Check `$ACA_DATA/../sessions/summaries/*.debug.txt` for raw Gemini responses
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
- `aops-core/specs/session-insights-prompt.md` - Shared prompt template
- `aops-core/lib/insights_generator.py` - Generation library
