---
title: Intent Router Session Context
type: spec
status: approved
permalink: intent-router-context
tags:
- framework
- hooks
- intent-router
---

# Intent Router Session Context

**Status**: Approved (ready for implementation)

## Problem

The intent router only sees the current user prompt. Without session context, it can't understand:
- Multi-turn conversations ("do the same for X")
- Active workflows (user is mid-skill invocation)
- Task state (TodoWrite items in progress)

## Solution

Extract compact session context and inject into router prompt alongside the user's current prompt.

## What to Extract

| Data | Purpose | Token Budget |
|------|---------|--------------|
| Last 3-5 user prompts | Multi-turn understanding | ~100-150 |
| Most recent Skill invocation | Active workflow detection | ~20 |
| TodoWrite state (from last call) | Task tracking | ~30-50 |
| **Total** | | **~150-250** |

## What NOT to Extract

- Full assistant responses (verbose, not useful for routing)
- Tool results (too detailed)
- Agent transcripts (separate concern)
- File paths touched (defer to v2)

## Context Format

```markdown
## Session Context

Recent prompts:
1. "help me debug the hook error"
2. "now fix the tests"
3. "that didn't work, try again"

Active: Skill("framework") invoked recently
Tasks: 2 pending, 1 in_progress ("Fix hook error")
```

### Formatting Rules

1. **User prompts**: Truncate to ~100 chars, newest first
2. **Skill line**: Only show if Skill invoked in last 10 turns
3. **Tasks line**: Only show if TodoWrite used in session
4. **Total**: Keep under 300 tokens

## Implementation

### New Function

Add to [[lib/session_reader.py]]:

```python
def extract_router_context(transcript_path: Path, max_turns: int = 5) -> str:
    """Extract compact context for intent router.

    Returns formatted markdown or empty string on error.
    """
```

### Hook Update

Update [[hooks/prompt_router.py]] `build_router_context()`:

```python
def build_router_context(user_prompt: str, transcript_path: str | None) -> str:
    session_context = ""
    if transcript_path:
        session_context = extract_router_context(Path(transcript_path))

    # Inject into template with {session_context} placeholder
```

### Prompt Template Update

Update [[hooks/prompts/intent-router.md]] to include:

```markdown
{session_context}

## User Prompt

{prompt}
```

## Fallback Behavior

| Condition | Behavior |
|-----------|----------|
| No transcript path | Empty session context |
| Empty session | Empty session context |
| Malformed JSONL | Log warning, empty context |
| No TodoWrite calls | Omit "Tasks:" line |
| No Skill calls | Omit "Active:" line |

Router continues to work without context (degrades gracefully).

## TodoWrite State Logic

TodoWrite tool calls contain explicit `status` field:
- `pending` - not started
- `in_progress` - currently working
- `completed` - done

Extract from most recent TodoWrite call in transcript. Count items by status.

## Test Cases

1. **Normal session**: 5 turns, skill invoked, todos present
2. **Empty session**: 0 turns → empty context
3. **Slash-only session**: Only `/commit`, `/help` → skip those, extract real prompts
4. **Malformed JSONL**: Graceful skip of bad entries
5. **Long prompts**: Truncation works correctly

## Configuration

```python
# Defaults (can be tuned based on testing)
MAX_TURNS = 5  # How many recent prompts to include
SKILL_LOOKBACK = 10  # How far back to look for Skill invocations
PROMPT_TRUNCATE = 100  # Max chars per prompt
```

## Acceptance Criteria

1. Router receives session context when transcript available
2. Context stays under 300 tokens
3. Graceful fallback on errors (no crashes)
4. Test coverage for edge cases
5. Latency impact < 100ms (extraction is fast)

## Future Enhancements (v2)

- Recently touched file paths (helps with "that file" references)
- Conversation topic summary (if session is very long)
- Caching of parsed transcript (if performance becomes issue)
