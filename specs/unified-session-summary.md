---
name: unified-session-summary
title: Unified Session Summary Architecture
category: spec
status: implemented
permalink: unified-session-summary
tags:
  - spec
  - sessions
  - reflection
---

# Unified Session Summary Architecture

**Status**: Implemented

## Architecture

LLM-based extraction from session transcripts. Same prompt template used by both execution paths.

### Single Skill Model

| Mode    | When              | How                                  |
| ------- | ----------------- | ------------------------------------ |
| Default | Session end       | Stop hook → `session-insights` skill |
| Batch   | Manual invocation | `/session-insights batch`            |

Both modes use the same Gemini MCP call with `insights.md` prompt.

All files stored in `$ACA_DATA/dashboard/sessions/{session_id}.json`.

### Session ID Strategy

Use main session UUID (first 8 chars) as key. Avoids collision from multiple terminals in same directory.

### Schema

```json
{
  "session_id": "abc12345",
  "date": "2026-01-08",
  "project": "writing",
  "summary": "One sentence description",
  "accomplishments": ["item1", "item2"],
  "learning_observations": [
    {"category": "user_correction", "evidence": "...", "context": "...", "heuristic": "H2"}
  ],
  "skill_compliance": {"suggested": [...], "invoked": [...], "compliance_rate": 0.0},
  "context_gaps": ["gap1"],
  "user_mood": 0.3,
  "conversation_flow": [["timestamp", "role", "content"]],
  "user_prompts": [["timestamp", "role", "content"]]
}
```

## Data Flow

```
Session ends → Stop hook injects skill instruction
            → Agent invokes session-insights skill
            → Skill generates transcript, calls Gemini MCP
            → JSON saved to dashboard/sessions/

Batch mode:
/session-insights batch → find transcripts lacking JSON
                        → process each via Gemini MCP
                        → JSON saved to dashboard/sessions/
```

## Components

| File                                                 | Purpose                                  |
| ---------------------------------------------------- | ---------------------------------------- |
| `skills/session-insights/insights.md`                | Prompt template                          |
| `skills/session-insights/SKILL.md`                   | Skill instructions                       |
| `skills/session-insights/scripts/mine_transcript.py` | Metadata extraction                      |
| `hooks/session_reflect.py`                           | Injects skill instruction at session end |
| `lib/session_summary.py`                             | Storage utilities                        |

## Relationships

### Used By

- [[dashboard-skill]] (reads session JSON)
- [[skills/daily/]] (aggregates for daily notes)
