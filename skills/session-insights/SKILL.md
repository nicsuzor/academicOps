---
name: session-insights
category: instruction
description: Extract accomplishments and learnings from session transcript. Writes JSON summary.
allowed-tools: Bash,Read,Write,mcp__gemini__ask-gemini
version: 2.0.0
permalink: skills-session-insights
---

# Session Insights

Extract accomplishments and learnings from session transcripts via Gemini.

## Modes

1. **Current session** (default): Process the current session at session end
2. **Batch**: Process multiple transcripts that lack JSON summaries

## Workflow: Current Session

### Step 0: Check existing session file does not exist

DO NOT PROCEED IF A SESSION FILE ALREADY EXISTS.

- Check:`$ACA_DATA/dashboard/sessions/{session_id}.json`

### Step 1: Generate Transcript

```bash
cd $AOPS && uv run python scripts/session_transcript.py \
  ~/.claude/projects/$(pwd | tr '/' '-' | sed 's/^-//')/$SESSION_ID.jsonl
```

Transcript written to `$ACA_DATA/sessions/claude/`.

### Step 2: Prepare Prompt

```bash
cd $AOPS && uv run python skills/session-insights/scripts/mine_transcript.py \
  "$ACA_DATA/sessions/claude/[transcript-filename].md"
```

This outputs the prompt with metadata substituted.

### Step 3: Call Gemini

```
mcp__gemini__ask-gemini(
  model="gemini-3-flash-preview",
  prompt="@{transcript_path}\n\n[prepared prompt from Step 2]"
)
```

### Step 4: Save JSON

Extract JSON from Gemini response and save to:

```
$ACA_DATA/dashboard/sessions/{session_id}.json
```

### Step 5: Report

```
Session insights saved: {session_id}
- Accomplishments: {count}
- User mood: {score}
```

## Workflow: Batch Mode

When invoked with `/session-insights batch`:

### Step 1: Find Pending Transcripts

```bash
cd $AOPS && uv run python scripts/session_status.py --mode cron-mining
```

This lists transcript paths that have no corresponding JSON summary.

### Step 2: Process Each

For each transcript path:

1. Run `mine_transcript.py` to prepare prompt
2. Call Gemini MCP with transcript + prompt
3. Save JSON to `$ACA_DATA/dashboard/sessions/{session_id}.json`

Limit to 3-5 per invocation to avoid timeouts.

## Files

| File                         | Purpose                                    |
| ---------------------------- | ------------------------------------------ |
| [insights.md]                | Prompt template for Gemini                 |
| [scripts/mine_transcript.py] | Metadata extraction and prompt preparation |

## Output

`$ACA_DATA/dashboard/sessions/{session_id}.json`

Schema defined in `insights.md`.
