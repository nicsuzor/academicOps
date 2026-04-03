---
title: "Handoff: Dogfood session-insights extraction (Claude-native)"
created: 2026-04-03
branch: crew/pamela
status: ready-to-execute
requires:
  - PKB MCP server (mcp__pkb__*)
  - $AOPS_SESSIONS mounted and accessible
---

# Handoff: Session-Insights Dogfood

## What this is

Resurrect the session-insights skill as a **Claude-native** extraction pipeline. The archived
skill (`archived/skills/session-insights/SKILL.md`) called `~~ai-assistant` (Gemini Flash 2.0)
— a dead tool reference. The sleep cycle's Phase 1 calls `/session-insights batch` but has no
live target. Fix it by replacing Gemini with a Claude subagent reading transcripts directly.

**Important**: Use only live data from `$AOPS_SESSIONS`. No fixtures, no synthetic sessions.

## Follow the dogfood loop

Per `/dogfood`: **execute one step → reflect before proceeding → codify if warranted**.
File every friction point as a PKB task. Fix instructions inline. Defer structural rethinking.

## Step 0: PKB setup (do this first)

```
mcp__pkb__create_task(
  title="Dogfood: session-insights extraction — Claude-native resurrection",
  tags=["dogfood", "session-insights"]
)
```

Save the returned task ID as the parent. File all findings as children of it.

## Step 1: Locate available transcripts

```bash
ls "$AOPS_SESSIONS/transcripts/" | head -20
# Then find pending (transcripts without corresponding insights):
cd /workspace && PYTHONPATH=aops-core uv run python \
  archived/skills/session-insights/scripts/find_pending.py --limit 5
```

Pick one completed session. Reflect: did `find_pending.py` work? Any errors?

## Step 2: Load and validate the prompt template

Read `/workspace/specs/session-insights-prompt.md`. Check for:

- References to `~~ai-assistant` or Gemini (outdated)
- Schema version mismatches vs `aops-core/lib/insights_generator.py`
- Fix inline if clear and localised

## Step 3: Extract insights (core step)

Read the selected transcript. Use `extract_recent_context()` from
`aops-core/lib/session_reader.py` for structured parsing — don't reinvent.

Then: launch a **general-purpose agent** with:

- The prompt template (substituted with session_id, date, project)
- The session transcript content
- Instruction to return pure JSON, no markdown fences

Validate the output:

```python
cd /workspace && PYTHONPATH=aops-core uv run python -c "
from lib.insights_generator import validate_insights_schema
import json, sys
data = json.load(open(sys.argv[1]))
validate_insights_schema(data)
print('valid')
" /path/to/output.json
```

Reflect: did validation pass? What fields were missing or wrong?

## Step 4: Save output + sync PKB

```python
from lib.insights_generator import write_insights_file, get_insights_file_path
# write to $AOPS_SESSIONS/summaries/
```

Then:

```
mcp__pkb__create_memory(
  title="Session insights: {session_id}",
  body="Session {session_id} ({date}): {summary}\n\nAccomplishments: ...\nKey learnings: ...",
  tags=["session-insights", "session-{session_id}", "{project}"]
)
```

Reflect: is the PKB sync step in `archived/skills/session-insights/SKILL.md` clear
enough for an agent to follow without this handoff?

## Step 5: Fix the skill

Edit `archived/skills/session-insights/SKILL.md`:

- Remove `~~ai-assistant` references throughout
- Replace Step 4 ("Call Gemini") with: launch a general-purpose Claude agent with the
  prepared prompt + transcript content; collect JSON response
- Update `allowed-tools`: remove `~~ai-assistant`, add `Agent` if available
- Decide: move to `aops-core/skills/session-insights/` if working end-to-end

Check `aops-core/skills/sleep/SKILL.md` Phase 1 — does invocation still match?

## Step 6: Codify learnings

For each friction point:

```
mcp__pkb__create_task(
  title="Finding: [specific description]",
  parent="<session-task-id>",
  tags=["learning", "session-insights"]
)
```

File a verification task:

```
mcp__pkb__create_task(
  title="Verify: session-insights works in sleep Phase 1 batch mode",
  tags=["verification", "session-insights"],
  body="Check that /sleep Phase 1 successfully calls /session-insights batch and produces valid JSON."
)
```

## Key files

| File                                                           | Role                                                                              |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `archived/skills/session-insights/SKILL.md`                    | The skill to fix                                                                  |
| `archived/skills/session-insights/scripts/find_pending.py`     | Session discovery                                                                 |
| `archived/skills/session-insights/scripts/prepare_prompt.py`   | Prompt prep                                                                       |
| `archived/skills/session-insights/scripts/process_response.py` | JSON extraction/validation                                                        |
| `specs/session-insights-prompt.md`                             | Extraction prompt template                                                        |
| `aops-core/lib/insights_generator.py`                          | `validate_insights_schema()`, `write_insights_file()`, `get_insights_file_path()` |
| `aops-core/lib/session_reader.py`                              | `extract_recent_context()`, `find_sessions()`                                     |
| `aops-core/skills/sleep/SKILL.md`                              | Phase 1 — check after skill move                                                  |

## Where we stopped

Blocked in Docker: `$AOPS_SESSIONS` not mounted, PKB MCP not available.
Steps 0–1 are the first things to do in the new session once both are accessible.
