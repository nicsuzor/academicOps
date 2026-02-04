---
id: interactive-followup
category: session
triggers: ["follow-up", "also", "quick change", "one more thing"]
---

# Interactive Follow-up Workflow

Streamlined flow for bounded follow-up requests within an active session.

## When This Applies

Follow-ups are detected automatically when ALL conditions are met:

1. **Session has existing work** - Either:
   - `turns_since_hydration > 0` (work done since last hydration), OR
   - Active task is bound to session

2. **Prompt is short** - Less than 30 words

3. **Contains continuation markers** - Words/phrases like:
   - Pronouns: "this", "that", "it", "these"
   - Additive: "also", "too", "as well", "while you're at it"
   - Quick actions: "save", "add", "put", "update", "log", "note"
   - Continuation: "one more", "quick", "before you go"

## What Gets Skipped

- **Hydrator agent** - No prompt-hydrator invocation
- **Critic review** - No mandatory critic before work
- **New task binding** - Inherits active task from session

## What Still Applies

- **Task binding inheritance** - Follow-ups work under the active task
- **Custodiet gate** - Still triggers after threshold tool calls (escalation)
- **MCP tools** - Memory, task manager still available for context
- **Handover** - Still required before session end

## Escalation

If a "follow-up" grows beyond bounded scope:

1. **Automatic**: Custodiet gate triggers after ~7 tool calls without compliance check
2. **Manual**: User can prefix with `.` to bypass, or start fresh prompt for full hydration
3. **Agent-initiated**: If agent recognizes scope creep, they should say so and recommend full hydration

## Examples

**Triggers follow-up flow:**
- "save that to the daily note" (short, has "that", has "save")
- "also add a test for it" (short, has "also", has "add", has "it")
- "put this in memory" (short, has "this", has "put")

**Does NOT trigger (needs full hydration):**
- "implement a new feature that handles user authentication with OAuth2 and JWT tokens" (too long, no continuation markers)
- "refactor the entire module" (no existing work context assumed)

## Implementation

Detection happens in `user_prompt_submit.py`:
- `is_followup_prompt()` - Checks all three conditions
- `should_skip_hydration()` - Returns True for follow-ups

Task reference: [[aops-a63694ce]]

## Related

- [[base-task-tracking]] - Full ceremony workflow
- [[direct-skill]] - Skill invocation flow (also skips hydration)
