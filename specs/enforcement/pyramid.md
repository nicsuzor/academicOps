---
id: TBD
title: In-Session Enforcement — The Pyramid (Layers 0–1)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Pyramid (Layers 0–1)

## Layer 0 — Intra-task loop (harness-internal)

The span inside a single user-prompt → completion: the harness's own thinking
turns and internal sub-agent delegation as it works out _how_ to satisfy a
high-level prompt.

Agent harnesses change these internal processes frequently. This is not a layer
the framework builds enforcement on — it is fragile and moves too fast. The
default contract is **outcome, not method**: trust the agent to work out how to
do the task it was given. Layer 0 carries no enforcement mechanism by design.

## Layer 1 — Turn loop (the pyramid)

The span from a user-prompt to a Stop event; may recurse through sub-agent
delegation nested within the turn.

**What it enforces:** honest answers, and that the agent has not been lazy. This
is the layer most exposed to model-performance and harness-behaviour change; the
framework adapts to it over time through `/aops-core:learn`.

**Shape — the pyramid.** Enforcement here is responsive, proportionate, and
evidence-driven: a wide, cheap, high-volume base graduating to a rare, heavy tip.
It uses the lightest mechanism that catches a failure and escalates only on
evidence the lighter one is insufficient.

### Mechanisms

All fire on Claude Code hook events within the turn (`UserPromptSubmit → … →
Stop`):

- **`ida`** (Stop) — honesty / criterion-substitution check, once per turn. The
  honesty invariant of this layer.
- **`sentinel`** (PreToolUse) — blocks destructive ops on protected paths.
- **`enforcer`/`rbg`** (PreToolUse) — periodic compliance audit after N tool
  calls.
- **`rbg-review`** (Stop) — final axiom audit before a task-bound session exits.
- **`handover` / `commit`** (Stop) — clean resumable exit: work committed, task
  updated, reflection recorded before the session ends.
- **`qa`** (Stop) — liveness nudge toward release and verification. The
  verification invariant itself is owned by Layer 2.
- **Auto-mode classifier** (PreToolUse) — per-action judgment gate (`soft_deny`
  context-overridable / `hard_deny` absolute).
- **Context injections** (not gates): SessionStart safety floor (`CORE.md`);
  UserPromptSubmit `pkb.nudge` and `hydration` routing hints.

### Two invariant families

Layer 1 carries two distinct invariant families over the same hook surface:
**honesty/verification** (`ida`, `qa`) and **safety/data-boundaries**
(`sentinel`, `policy_enforcer.py`, `settings.json` deny rules, credential
isolation). They share a delivery surface but are not the same concern.
