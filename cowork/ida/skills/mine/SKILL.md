---
name: mine
description: With an ask, file it as an ida-tracked task that must not be dropped even across days and sessions; with no ask, pass through the agents' own tracked tasks and move each on. Use when the user invokes /mine. Not for routine task capture (use /q) or for starting workers on ready tasks (use /dispatch).
argument-hint: "[ask to track]"
---

# /mine -- tracked asks

Ask: $ARGUMENTS

## With an ask: track it

The user is signalling that this ask must not be dropped, even if it takes days and many sessions.

1. Have the PKB session hydrate the ask. If an open task already covers it, attach the user's words to that task verbatim, add the `ida-tracked` tag, and soft-link it from the themed parent it belongs to; never reparent project work. If nothing covers it, create a task assigned to ida, status `queued`, tagged `ida-tracked`, with the user's words verbatim as the goal, under the themed parent in the agents' own PKB project that it belongs to. Create a theme parent only when none fits.
2. Have the PKB session make sure the tracked ask's parent reaches one of the user's existing targets at a strong weight, with a one-line justification.
3. If work can start now, start it in the same turn: brief the session that does the work.
4. Tell the user the task's id and plain-English title, through the user-facing session.

A tracked ask is done only when the user has the result.

## With no ask: pass through the tracked tasks

1. Have the PKB session return every task assigned to ida, under the agents' own project, or tagged `ida-tracked`, grouped by theme parent, with its id, title, status and trigger.
2. For each task, do the next step it needs now: send the user what is due through the user-facing session, start anything not yet dispatched, and close what is finished. Every close carries its evidence.
3. Send the user one message: what you sent them, and anything that needs their decision. Say nothing about the rest. Only the user-facing session sends it.
