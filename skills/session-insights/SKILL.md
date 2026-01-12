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
3. **Issues**: Extract learnings from bd issues tagged with learning/experiment/bug labels

## Workflow: Current Session

### Step 0: Check existing session file does not exist

DO NOT PROCEED IF A SESSION FILE ALREADY EXISTS.

- Check:`$ACA_DATA/sessions/insights/{date}-{session_id}.json`

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
$ACA_DATA/sessions/insights/{date}-{session_id}.json
```

Format: `YYYY-MM-DD-{session_id}.json` (e.g., `2025-01-12-a1b2c3d4.json`)

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
3. Save JSON to `$ACA_DATA/sessions/insights/{date}-{session_id}.json`

Limit to 3-5 per invocation to avoid timeouts.

## Workflow: Issues

When invoked with `/session-insights issues`:

Extract learnings from bd issues to identify patterns worth formalizing into HEURISTICS.md.

### Step 1: List Learning Issues

```bash
bd list --status=open --limit 0 | grep -E "\[learning\]|\[experiment\]|\[bug\]"
```

### Step 2: For Each Issue

For each issue ID from Step 1:

1. Get full issue details: `bd show {issue_id}`
2. Analyze the issue content to extract:
   - **Pattern**: What behavior/failure pattern does this document?
   - **Root cause**: Why did this happen?
   - **Systemic insight**: What does this teach about agent behavior or framework gaps?
   - **Heuristic candidate**: Should this become a formal heuristic? If so, draft it.
   - **Related**: Which existing heuristics or axioms does this relate to?

### Step 3: Synthesize

Group findings by theme:

- Agent compliance patterns
- Tool usage patterns
- Workflow gaps
- Missing guardrails

### Step 4: Output

Report findings in format:

```
## Issue Learnings Synthesis

### Heuristic Candidates
- H??: [Draft heuristic from issue X]
- H??: [Draft heuristic from issue Y]

### Patterns Observed
- [Pattern]: Seen in issues X, Y, Z

### Recommended Actions
- [ ] Add heuristic H?? to HEURISTICS.md
- [ ] Update skill X to address gap
- [ ] Close issues X, Y, Z after integration
```

### Step 5: Close Processed Issues

After learnings are integrated into HEURISTICS.md or other framework docs:

```bash
bd close {issue_id} --reason="Learning integrated into HEURISTICS.md H##"
```

## Files

| File                         | Purpose                                    |
| ---------------------------- | ------------------------------------------ |
| [insights.md]                | Prompt template for Gemini                 |
| [scripts/mine_transcript.py] | Metadata extraction and prompt preparation |

## Output

`$ACA_DATA/sessions/insights/{date}-{session_id}.json`

Format: `YYYY-MM-DD-{session_id}.json` (e.g., `2025-01-12-a1b2c3d4.json`)

Schema defined in `insights.md`.
