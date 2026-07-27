---
id: dogfooding
kind: process
category: meta
description: Framework self-improvement through deliberate execute-reflect-codify cycles while doing real work
requires: [memory-capture]
pairs-with: [session-effectiveness]
conflicts: []
version: 2.0.0
permalink: workflows-process-dogfooding
---

# Process: Dogfooding

**Supersedes**: the prior duplicate `reflect.md` (id `meta-improvement`) — same
loop, same intent, migrated once here.

## When to Apply

Working under uncertainty (new/unclear process); testing framework
capabilities on real work; any task where the process itself is worth
examining; conversational planning sessions.

## The Loop — `EXECUTE → REFLECT → CODIFY`, per step, not per session

1. **Execute** one discrete step. Notice friction: awkward steps, missing
   context, tools that didn't work.
2. **Reflect** before the next step. One-time friction → note it, continue.
   Recurring pattern (3+) → check whether it's already documented; if not,
   flag for codification. Blocking → fix minimally, note for later. Better
   pattern found → document what worked.
3. **Codify** — the step most often skipped. Ask: what did I learn that should
   become part of the framework? Better workflow → update the template. Missing
   guardrail → add to a gate. New heuristic → record it. Tool/schema gap → file
   a task, never a silent workaround.

## Core Principles

PKB is always live — write facts/decisions immediately, don't wait to be
asked. Anchor findings to a task, with specific titles (not "finding #1").
Update existing items, don't duplicate. Don't be selfish — propagate fixes to
the instructions governing future work, not just current work. No
workarounds — a broken tool is a filed task, not an invented manual step.

## Post-Run Assessment (mandatory)

File structured follow-ups as the output of a dogfood run: a "pre-next-run
fixes" epic; a blocked "repeat and reassess" task depending on it with
baseline metrics; issues for systemic problems (compose [[session-effectiveness]]
for the transcript-level version of this).

## Scope

Dogfooding grants dual scope: the task AND the tooling being tested. Fix
obvious bugs inline; defer design changes and new features to follow-up tasks.
