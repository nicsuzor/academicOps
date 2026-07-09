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

Layer 1 enforcement rides Claude Code hook events within the turn
(`UserPromptSubmit → … → Stop`), firing uniformly across main sessions,
subagents, and workers except `enforcer`/`rbg`'s PreToolUse dispatch, which
stays skipped for subagent-classified sessions as a deliberate, permanent
exception — see [`GATES.md` § Subagent & worker session
scope](GATES.md#subagent--worker-session-scope). The full mechanism roster
(which gate, what it catches, trigger and mode per surface) is the
[`ENFORCEMENT-MAP.md` §1 matrix](../../ENFORCEMENT-MAP.md#1-unified-ssot-matrix-rules-mechanisms-and-triggers);
per-gate runtime/forensic detail is [`GATES.md`](GATES.md).

**Retired from this layer:** `sentinel` — deleted (H1, "no shitty NLP";
container isolation instead). `ida` remains live at this layer; disposition
is OPEN, pending the session-type walk ([[aops_3eabb0ae]]) — see
[`GATES.md#ida-gate`](GATES.md#ida-gate) for the corrected record.

### Two invariant families

Layer 1 carries two distinct invariant families over the same hook surface:
**honesty/verification** (now owned by the head-personality surface + `qa`)
and **safety/data-boundaries** (`policy_enforcer.py`, `settings.json` deny
rules, credential isolation, pre-commit mechanical checks). They share a
delivery surface but are not the same concern.
