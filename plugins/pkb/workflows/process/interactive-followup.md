---
id: interactive-followup
kind: process
category: session
description: Streamlined flow for bounded follow-up requests within an active session — skips re-hydration and new task binding
requires: [wf-verification]
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-interactive-followup
---

# Process: Interactive Follow-up

## When This Applies

All of: the session has existing work (turns since hydration > 0, or an active
task bound to the session); the prompt is short (<30 words); it contains a
continuation marker (pronoun — "this/that/it"; additive — "also/too/as well";
quick-action verb — "save/add/put/update/log/note"; or "one more"/"quick"/
"before you go").

## What Gets Skipped

- Full hydration (the previous shortlist stands; search the new term only)
- New task binding — inherits the active task from the session

## What Still Applies

- Task binding inheritance
- Escalation checks (compose [[wf-verification]])
- MCP tools (memory, task manager) remain available
- [[wf-handover]] is still required before session end

## Escalation

If a "follow-up" grows beyond bounded scope: automatic escalation after
several tool calls without a compliance check, the user can force full
hydration with a fresh prompt, or the agent should self-recognize scope creep
and say so.

## NOT this template

- New idea/fragment/constraint arriving mid-session → full hydration, then
  route normally (e.g. [[decision-briefing]] or a fresh process template).
