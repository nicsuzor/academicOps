---
name: unified-session-summary
title: Unified Session Summary Architecture
category: spec
status: implementing
permalink: unified-session-summary
tags:
  - spec
  - sessions
  - reflection
  - daily-notes
---

# Unified Session Summary Architecture

**Status**: Implementing (TDD in progress)

## Problem Statement

Session summary generation has duplicated logic across:

- Framework reflection (AGENTS.md Step 3)
- Stop hook session synthesis
- Session-insights skill (daily batch processing)

This creates DRY violations and inconsistent output formats.

## Solution

Unified tiered architecture with a single schema for session summaries, captured at different times by different methods.

## Architecture

### Tiered Capture Model

| Layer                  | File                      | Key             | Written When               | Written By                |
| ---------------------- | ------------------------- | --------------- | -------------------------- | ------------------------- |
| 1: Task contributions  | `{session_id}-tasks.json` | Main session ID | After each task reflection | Main agent (AGENTS.md)    |
| 2: Session synthesis   | `{session_id}.json`       | Main session ID | Session end                | Stop hook                 |
| 3: Recovery (fallback) | `{session_id}.json`       | Main session ID | Daily batch                | session-insights (Gemini) |

All files stored in `$ACA_DATA/dashboard/sessions/`.

### Session ID Strategy

**Problem**: Multiple terminals in same directory get same `cwd` hash → collision.

**Solution**: Use main session UUID as key (NOT project hash).

Subagents link to main agent via `sessionId` field in agent JSONL files (see `lib/session_reader.py:816`).

### Schema: Task Contribution

Written after each task reflection (AGENTS.md Step 3):

```json
{
  "session_id": "abc12345-...",
  "updated_at": "2026-01-08T10:30:00Z",
  "tasks": [
    {
      "request": "Create stub spec for debug-headless skill",
      "guidance": "Hydrator suggested /framework skill",
      "followed": "no",
      "outcome": "success",
      "accomplishment": "Created debug-headless skill stub",
      "project": "academicOps"
    }
  ]
}
```

### Schema: Session Summary

Full session synthesis (written at session end or by Gemini fallback):

```json
{
  "session_id": "abc12345",
  "date": "2026-01-08",
  "project": "writing",
  "summary": "One sentence description of session work",
  "accomplishments": ["item1", "item2"],
  "learning_observations": [
    {
      "category": "user_correction",
      "evidence": "quoted text",
      "context": "description",
      "heuristic": "H2"
    }
  ],
  "skill_compliance": {
    "suggested": ["framework"],
    "invoked": [],
    "compliance_rate": 0.0
  },
  "context_gaps": ["gap1"],
  "user_mood": 0.3,
  "tasks": [/* merged from task contributions */]
}
```

## Data Flow

```
Task 1 completes → append to {session_id}-tasks.json
Task 2 completes → append to {session_id}-tasks.json
...
Session ends → Stop hook reads -tasks.json, synthesizes to {session_id}.json
               (or session-insights mines transcript if no -tasks.json exists)
Daily batch → session-insights reads all {session_id}.json, produces daily.md
```

## Acceptance Criteria

### 1. Task Contribution Capture

- [ ] `lib/session_summary.py` provides `append_task_contribution(session_id, task_data)`
- [ ] Function is atomic (append to file, not read-modify-write)
- [ ] Schema validation on write
- [ ] Works from any cwd (uses session_id, not project hash)

### 2. Session Synthesis

- [ ] `lib/session_summary.py` provides `synthesize_session(session_id)`
- [ ] Reads `-tasks.json`, merges into `{session_id}.json`
- [ ] Falls back gracefully if no task contributions exist
- [ ] Idempotent (can run multiple times safely)

### 3. Daily Note Integration

- [ ] `session-insights` reads `{session_id}.json` files (not transcripts when possible)
- [ ] Produces same daily.md format as current implementation
- [ ] Accomplishments flow: task contributions → session summary → daily.md

### 4. Backward Compatibility

- [ ] Existing Gemini mining still works as fallback
- [ ] Sessions without task contributions still get mined
- [ ] No breaking changes to synthesis.json format

## Implementation Plan

1. **Create `lib/session_summary.py`** with:
   - `get_session_summary_dir()` → Path
   - `get_task_contributions_path(session_id)` → Path
   - `get_session_summary_path(session_id)` → Path
   - `append_task_contribution(session_id, task_data)` → None
   - `load_task_contributions(session_id)` → list
   - `synthesize_session(session_id, additional_data)` → SessionSummary
   - `save_session_summary(session_id, summary)` → None

2. **Update AGENTS.md Step 3** to call `append_task_contribution()` after reflection

3. **Update Stop hook** to call `synthesize_session()` on session end

4. **Update session-insights** to prefer `{session_id}.json` over transcript mining

## File Locations

| File                               | Purpose                                     |
| ---------------------------------- | ------------------------------------------- |
| `lib/session_summary.py`           | Core capture/synthesis logic                |
| `tests/test_session_summary.py`    | Unit tests                                  |
| `hooks/session_reflect.py`         | Stop hook (update to synthesize)            |
| `skills/session-insights/SKILL.md` | Batch processing (update to use summaries)  |
| `AGENTS.md`                        | Reflection instructions (update to capture) |

## Relationships

### Replaces/Consolidates

- Duplicated summary logic in AGENTS.md, session_reflect.py, session-insights

### Depends On

- `lib/session_reader.py` for session ID resolution
- `$ACA_DATA` environment variable

### Used By

- [[dashboard-skill]] (reads synthesis.json)
- [[session-insights-skill]] (produces daily.md)
- Framework reflection (writes task contributions)
