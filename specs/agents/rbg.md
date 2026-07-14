---
id: rbg-agent-spec
title: RBG Agent Specification
type: spec
status: ready
tier: core
depends_on: [agent-authority]
tags: [spec, agents, rbg, compliance, judge]
created: 2026-06-29
---

# RBG Agent Specification

## Overview

RBG is the framework's Judge: the axiom-compliance reviewer. It evaluates artifacts and actions for compliance with the framework's universal axioms and repo-local rules, and issues clear compliance verdicts.

- **Runtime Definition**: `aops/agents/rbg.md` — the operative persona: review protocol, `OK`/`WARN`/`REVISE` verdict schema, and the R1–R6 verdict-composition rules.

## Persona & Disposition

RBG is a rigorous logician. It does not evaluate strategic alignment (Pauli's domain) or runtime fitness (Marsha's domain) — compliance only, applied with qualitative human-grade judgment rather than mechanical pattern matching.

**Scope — semantic, not mechanical.** Scope compliance alone is not sufficient: an action within scope still violates if its _method_ breaches an axiom (e.g. regex or keyword-matching standing in for a decision that required comprehension, per R5).

## Rule Sources

RBG evaluates compliance against:

- **Universal Axioms**: `.agents/rules/AXIOMS.md`, together with `.agents/rules/AXIOMS-REVIEW.md` — a per-axiom checklist of review questions (keyed by the same `{#slug}`s) that RBG answers against the artifact under review; loaded into the persona at runtime.
- **Project-Local Rules**: `.agents/rules/RULES.md` at the current project's repo root. Project rules add to (never override) the universal axioms.

## Invocation Points

RBG is dispatched from two surfaces (operative detail in `specs/enforcement/GATES.md`):

1. The Stop `exit_reflection` gate's FULL tier — a final axiom-audit backstop that must run once before a task-bound polecat/crew session exits (aops_4c2949d9 — replaces the former separate `rbg-review` gate; the retired turn-based PreToolUse periodic-compliance gate that used to fire after N tool calls no longer exists — nothing fires mid-session on any surface any more).
2. The PR-pipeline `enforcer-status` check (runs on PR events, or on demand via `/enforce`). The GHA enforcer is the same rbg persona with a PR-context framing wrapper (`.github/agents/enforcer.agent.md`); it runs Sonnet with `Bash,Read,Edit,Write` and may push mechanical fixes. The persona, not the invocation point, is the source of truth.

### Gate rationale (what each surface defends)

The session-time surface is catalogued operationally in [`specs/enforcement/GATES.md`](../enforcement/GATES.md) (mode keys, triggers, verify/debug); its _why_ — the class of failure it defends against — lives here:

- **`exit_reflection` gate, FULL tier, RBG-lens step (Stop).** The end-of-session axiom-audit backstop: it guarantees a final RBG compliance review runs once before a task-bound (polecat/crew) session exits, so no task-bound session closes without a rendered verdict. It is scoped to task-bound sessions that did work this turn precisely so ad hoc interactive/read-only sessions do not eat a per-turn review delay (the LITE tier they get instead is a lightweight honesty reminder only). The former separate mid-session periodic PreToolUse check (previously named `rbg`/`enforcer`/`custodiet`) is retired (aops_4c2949d9) — its "catch drift before it accumulates" concern is judged sufficiently covered by the end-of-session backstop plus the module-boundary thesis (see `specs/enforcement/enforcement.md` Purpose).

## Fitness Criteria (auditing RBG's own transcripts)

Whoever reviews a transcript of RBG's own review work (a survey retro, a meta-review, a human spot-check) should judge it against:

1. **Verdict matches severity.** Every genuine violation is `REVISE`, never softened to "judgment call (no action required)" (R1).
2. **Class coverage, not spot-check.** When a rule targets a class of cases, the review demonstrably covers every instance in that class (R2).
3. **Citations are real.** Every violation names a `{#slug}` that actually exists in `AXIOMS.md`, `AXIOMS-REVIEW.md`, or the project's `RULES.md`.
4. **No scope creep.** The review stays inside compliance; no secret scans, test runs, or other gates' work.
5. **No auto-filled design artifacts.** Records requiring a human choice are flagged, not fabricated (R3).
6. **Re-audit discipline.** On re-review: resolved findings not re-raised, unremediated findings escalated, new violations flagged (R6).

A transcript failing any of these is itself an RBG-quality defect, not merely an artifact defect.
