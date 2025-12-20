---
name: session-insights
description: Orchestrate transcript generation, daily summaries, and data mining to extract framework learnings from Claude Code sessions.
allowed-tools: Read,Bash,Glob,Grep,Edit,Write,mcp__gemini__ask-gemini,mcp__bmem__search_notes,mcp__bmem__write_note
version: 1.0.0
permalink: skills-session-insights
---

# Session Insights Skill

Orchestrate the full session review workflow: batch transcripts → daily summary → data mining → experiment evaluation.

## When to Use

- End of day session review
- "What happened in my sessions today?"
- "Extract learnings from recent sessions"

## Arguments

- `today` (default) - process today's sessions
- `YYYYMMDD` - process specific date

## Workflow Overview

```
/session-insights [date|today]
    ↓
1. BATCH TRANSCRIPTS (cross-machine safe)
    ↓
2. DAILY SUMMARY (session-analyzer skill)
    ↓
3. DATA MINING (Gemini per-session)
    ↓
4. EXPERIMENT EVALUATION
```

---

## Step 1: Batch Transcripts

Generate/update transcripts for sessions on target date.

**Find sessions**: Use `lib.session_reader.find_sessions()` filtered by date.

**Freshness check** (cross-machine safe):
- Find matching `*-abridged.md` transcript in `$ACA_DATA/sessions/claude/`
- Generate if: transcript missing OR session mtime > transcript mtime
- Skip if transcript is up-to-date

**Generate**: `Skill(skill="transcript")` for each session needing update.

**Output**: `$ACA_DATA/sessions/claude/YYYYMMDD-<project>-<slug>-{full,abridged}.md`

---

## Step 2: Daily Summary

Invoke: `Skill(skill="session-analyzer", args="$DATE")`

This handles accomplishment extraction and daily note updates.

---

## Step 3: Data Mining (Gemini)

For each transcript, extract learnings via Gemini.

**Load context first**:
- Active experiments from `experiments/*.md` (not resolved)
- Learning themes from `learning/*.md`

**Gemini extraction** (see [[mining-prompt.md]]):
- Problems: user corrections, navigation failures, verification skips
- Successes: especially ordinary ones that are experiment evidence
- Experiment evidence: matches to active hypotheses

**Route results**:
- Known patterns → `learning/[theme].md`
- Novel problems → `LOG.md`
- Experiment evidence → `experiments/[file].md`

---

## Step 4: Experiment Evaluation

After mining, report experiment status:
- Which experiments got new evidence?
- Any ready for decision?
- Any hypotheses validated/invalidated?

---

## Output Summary

```
## Session Insights - YYYY-MM-DD

### Transcripts
- Generated: N | Updated: N | Skipped: N

### Daily Summary
- Updated: sessions/YYYYMMDD-daily.md

### Learnings
- Problems: N | Successes: N | Experiment evidence: N
```

---

## Constraints

- **DO NOT** auto-apply learnings. Extract and route only.
- **DO NOT** modify HEURISTICS.md directly. Route to learning files.
