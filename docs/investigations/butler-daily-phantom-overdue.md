# Post-Mortem: Butler Failed to Diagnose Daily Skill Phantom Overdue Bug

**Date:** 2026-03-31
**PR:** #429
**Related fix:** #427 (`ac2bdac`)

## What Happened

User ran `/daily` on dev3. The daily agent reported the OSB renewal agreement as **overdue** — but the user had already marked it `done` via the dashboard on Mar 29. The PKB task (`task-e6289bdb`) had `status: done`. The daily agent ignored this and carried forward "overdue" from yesterday's note.

The fix was straightforward (landed in #427 / `ac2bdac`): pre-flight MCP check, PKB tools in allowed-tools, mandatory carryover verification. But diagnosing it took 30+ minutes of flailing — the butler, which is supposed to have perfect framework knowledge, couldn't find basic things.

## Root Cause Chain (Daily Skill Bug)

1. Daily skill didn't list PKB MCP tools in `allowed-tools`
2. Agent spawned an Explore subagent to scan the filesystem as a workaround
3. Subagent's scan only found `active/inbox` tasks — correctly excluded the `done` task
4. But the main agent also read yesterday's daily note, which listed the task as "DUE TODAY"
5. Main agent trusted yesterday's note over the subagent's findings
6. Result: phantom overdue item for a completed task

## Root Cause Analysis (Butler Investigation Failure)

This is the real issue. The butler is the framework's institutional memory. It should have diagnosed this in 5 minutes. Instead:

**RC1: BUTLER.md has no operational knowledge.**
It describes architecture, components, decisions, priorities — but not the basic facts needed to DO things. Where are transcripts? What env vars exist? What does the directory layout look like? This is a chief-of-staff who knows the org chart but can't find the filing cabinet. Butler didn't know `$AOPS_SESSIONS`, didn't know where transcripts live, didn't know the transcript naming convention.

**RC2: No investigation methodology.**
The butler skill is ~200 lines of governance philosophy and zero lines on "how to trace a problem through the system." No systematic diagnostic approach. Should have been: (1) what's the claim? (2) what generated the claim? (3) trace the source. Instead: scattered searches across daily notes, JSONL files, brain, Mac guesses — all before finding the transcript that generated the claim.

**RC3: Filename pattern matching instead of content search.**
Butler searched for filenames containing "brain", "daily", or "abridged" — and missed the actual transcript (`academicOps-aadb37ee-remove-pkb-mcp`) because the slug is unpredictable. A simple `rg "daily note"` on transcript content would have found it in one step. This happened THREE times in the session.

**RC4: Assumption-driven investigation.**
Butler assumed the daily ran on the Mac (it ran on dev3). Assumed transcripts would be in brain (they're in `$AOPS_SESSIONS`). Assumed `$ACA_SESSIONS` was the right variable (it's `$AOPS_SESSIONS`). Each assumption sent it down a dead-end path. Correct approach: search broadly first, narrow from evidence.

**RC5: No env var registry.**
`$AOPS_SESSIONS`, `$ACA_DATA`, `$POLECAT_HOME`, `$PKB_MCP_URL` — scattered across hooks, scripts, and `lib/paths.py`. No single reference. Easy to confuse similar names (`$ACA_SESSIONS` vs `$AOPS_SESSIONS`).

**RC6: Silent degradation is the worst failure mode.**
Before the fix, the daily skill would happily produce a daily note with stale data rather than failing. The user trusted the output. This is worse than crashing — at least a crash tells you something is wrong.

## What Was Already Fixed

PR #427 (`ac2bdac`, merged to main):
- Pre-flight MCP check (halt if PKB or Outlook unavailable)
- PKB tools added to `allowed-tools`
- Mandatory live status check for carryover tasks
- `$ACA_SESSIONS` → `$AOPS_SESSIONS` env var fix

BUTLER.md updated with session transcript operational knowledge.

## Proposed Fixes (For Discussion)

These changes would target the **butler skill** and **framework operational docs**, not the daily skill:

1. **Add investigation methodology to butler skill** — a "how to trace a problem" section: identify the claim → find the source transcript → read the agent's tool calls → identify where it went wrong. Content search first, filename patterns never.

2. **Add env var registry to BUTLER.md** — single table of all framework env vars, what they resolve to on each machine, and what reads them.

3. **Add "debugging the framework" reference to butler skill** — common failure patterns and where to look: "daily note wrong" → find transcript → check MCP calls; "task status stale" → check PKB directly; "agent didn't follow skill" → check if skill was loaded.

4. **Behavioural rule: content search before filename search** — when looking for a session or transcript, ALWAYS search content first (`rg` on the content), NEVER rely on filename slugs. This should be in the butler skill as a concrete investigation rule.

## Open Questions

- Is BUTLER.md the right place for operational knowledge, or should there be a separate operational reference? BUTLER.md is already long.
- Should the env var registry live in BUTLER.md, in `lib/paths.py` docstring, or in a separate `ENV_VARS.md`?
- How much investigation methodology belongs in the butler skill vs being a general agent capability?
