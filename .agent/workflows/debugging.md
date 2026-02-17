---
id: debugging
category: workflow
extends: [base-task-tracking, base-verification]
description: Investigating unknown causes. Session discovery, log artifacts, hypothesis testing.
---

# Debugging Workflow

Understand the problem before fixing it. Compose with [[base-investigation]] for hypothesis testing.

For deep framework-specific debugging (hooks, gates, subagents), see also `.agent/skills/framework/workflows/02-debug-framework-issue.md`.

## Session Discovery

Find recent sessions quickly:

```bash
# Recent Claude sessions (last 3 days)
fd -t f -e jsonl . ~/.claude/projects --changed-within 3d | xargs ls -t 2>/dev/null | head -5

# Recent Gemini sessions (last 3 days)
fd -t f -e json session- ~/.gemini/tmp --changed-within 3d | xargs ls -t 2>/dev/null | head -5

# Recent hooks logs (framework-produced)
fd -t f hooks.jsonl ~/.claude/projects --changed-within 3d | xargs ls -t 2>/dev/null | head -5

# Recent archived transcripts
fd -t f -e md . ~/.aops/sessions --changed-within 7d | xargs ls -t 2>/dev/null | head -5

# Find a specific session by hash fragment (e.g., a6548a0e)
fd a6548a0e ~/.claude/projects ~/.gemini/tmp
```

## Framework Paths

| What | Path |
|------|------|
| Claude raw sessions | `~/.claude/projects/<encoded-cwd>/` (cwd with `/` → `-`) |
| Gemini raw sessions | `~/.gemini/tmp/<project-hash>/chats/` |
| Hooks log (ours) | `~/.claude/projects/<encoded-cwd>/<date>-<hash>-hooks.jsonl` |
| Session state (ours) | `~/.claude/projects/<encoded-cwd>/<date>-HH-<hash>.json` |
| Archived transcripts | `~/.aops/sessions/` (abridged + full markdown) |
| Gemini hydration files | `~/.gemini/tmp/<project-hash>/hydrator/hydrate_*.md` |
| Framework hooks code | `$AOPS/aops-core/hooks/` |
| Gate definitions | `$AOPS/aops-core/lib/gates/definitions.py` |

## Log Artifacts

Three distinct log types exist. Don't confuse them.

### 1. Hooks Log (framework-produced) — `*-hooks.jsonl`

Produced by `$AOPS/aops-core/hooks/router.py`. One line per hook invocation with full payload: hook event, tool name, tool input, `is_subagent`, `subagent_type`, gate verdicts, session state snapshot.

**Best for**: Gate/hook behavior, subagent detection failures, hydration flow, "why was my tool blocked?"

Key fields: `hook_event`, `is_subagent`, `subagent_type`, `tool_name`, `output.verdict`

### 2. Client Session Log (client-produced) — `.jsonl` (Claude) / `.json` (Gemini)

Produced by the CLI client. Full conversation: turns, tool calls, model responses, system messages.

**Best for**: Understanding what the agent did and why, reproducing user-reported issues.

Convert to readable markdown first: `uv run --directory $AOPS python aops-core/scripts/transcript.py <session-file>`

### 3. Session State File (framework-produced) — `<date>-HH-<hash>.json`

Produced by `$AOPS/aops-core/lib/session_state.py`. Current gate statuses (open/closed), active task, ops counters, metadata.

**Best for**: Understanding gate state at a point in time, checking if state persisted correctly across hook invocations.

## Investigation Pattern

1. Define success criteria (what does "fixed" mean?)
2. Locate artifacts (use session discovery commands above)
3. Read hooks log first — it shows exact payloads and verdicts
4. Form hypothesis → test with [[base-investigation]] cheapest-probe pattern
5. Document root cause in task before routing to fix workflow
