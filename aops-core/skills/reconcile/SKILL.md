---
skill: reconcile
description: On-demand GH ↔ PKB reconciliation — full sweep of closure-loop gaps, triage of needs_user_call items.
trigger: user_invoked
entrypoint: scripts/reconcile.py --full
---

# Reconcile Skill

Runs the GH ↔ PKB closure-loop reconciliation library in `--full` mode. This surfaces ambiguous matches for user triage and writes `needs_user_call` events to `gh-pkb-deltas.json`.

**Cron-driven modes** (`--forward`, `--reverse`) are NOT invoked via this skill — they are wired directly into `repo-sync-cron.sh` and the `pkb__complete_task` hook respectively. See `DESIGN.md` for the full callsite map.

## Usage

```
/reconcile
```

Invokes `scripts/reconcile.py --full`. The script:

1. Reads `pr-state.json` and `issue-state.json` for all tracked repos.
2. Calls `aops-core/lib/reconcile/match.py` — mechanical matching first, semantic agent dispatch for unresolved cases.
3. Applies actions (task completion, GH comment/close) via PKB MCP and `gh` CLI.
4. Writes all events (including `needs_user_call`) to `gh-pkb-deltas.json`.
5. Prints a summary: N completed, N commented, N flagged for user call.

## Triage surface

After running, `needs_user_call` items appear in the next `/daily` briefing under "What Needs Attention → Needs your call". They do not require immediate response.

## Implementation status

**Not yet implemented.** Skeleton only. See `DESIGN.md` for the full design.
Implementation tracked via PR1/PR2/PR3 tasks (queued 2026-05-13).
