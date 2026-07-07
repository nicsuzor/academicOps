---
id: enforcement-pyramid
title: In-Session Enforcement — The Pyramid (Layers 0–1)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Pyramid (Layers 0–1)

> **Numbering note.** `Layer 0`/`Layer 1` here belong to the **module-boundary layer model** (`Layer 0`–`Layer 4`, spanning this file plus [task-contract.md](task-contract.md), [workflow.md](workflow.md), [sign-off.md](sign-off.md)) — an axis orthogonal to [`enforcement.md`](enforcement.md)'s pipeline (`L0`–`L11`) and pyramid-position (`L0`–`L7`) numbers. They reuse the same digits for a different purpose; see [enforcement.md § Two views of the same mechanisms](enforcement.md#two-views-of-the-same-mechanisms) for the distinction.

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
Stop`), uniformly across main sessions, subagents, and workers — no
`is_subagent` skip (H8, reorganised within the existing session-state design
per H12):

- **`enforcer`/`rbg`** (PreToolUse) — periodic compliance audit after ~17
  tool calls (default lowered from 50, H2).
- **`rbg-review`** (Stop) — final axiom audit before a task-bound session
  exits; armed by default, posture expressed only via env vars/`polecat.yaml`
  (H3).
- **`handover` / `commit`** (Stop) — clean resumable exit: work committed, task
  updated, reflection recorded before the session ends. Unchanged (H10/H12).
- **`qa`** (Stop) — liveness nudge toward release and verification. The
  verification invariant itself is owned by Layer 2. Unchanged (H10/H12).
- **Task-binding** (PreToolUse, write) — reactivated: no mutation without a
  task bound via `claim_task` (H4; target, lands with aops-5b9e95c4).
- **Auto-mode classifier** (PreToolUse) — per-action judgment gate (`soft_deny`
  context-overridable / `hard_deny` absolute).
- **Pre-commit mechanical checks** (git-commit hook) — dprint/ruff/
  markdownlint/actionlint/no-fallbacks and others; deterministic, local.
- **Context injections** (not gates): SessionStart safety floor (`CORE.md`);
  UserPromptSubmit `pkb.nudge` (stays lowest-layer, aops-core, H5/H14) and the
  skills-routing hint (moves up to aops-pkb/aops-adhd, H11).

**Retired from this layer:** `sentinel` — deleted (H1, "no shitty NLP";
container isolation instead). `ida` — retired as a hook (H6); the honesty /
criterion-substitution check this layer used to enforce mechanically now
belongs to the head-personality surface interacting with the human
(`ida`, `aops-core`), not a router-level gate that fires uniformly regardless
of whether a human is present.

### Two invariant families

Layer 1 carries two distinct invariant families over the same hook surface:
**honesty/verification** (now owned by the head-personality surface + `qa`)
and **safety/data-boundaries** (`policy_enforcer.py`, `settings.json` deny
rules, credential isolation, pre-commit mechanical checks). They share a
delivery surface but are not the same concern.
