---
id: enforcement-318d578e
title: Enforcement Architecture
type: spec
status: ready
tier: core
depends_on: []
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

The architectural specification detailing design rationale, theoretical mechanisms, regulatory pyramid escalation, and governance principles behind enforcement in academicOps.

- **Stated Purpose:** Defines the theoretical foundation, mechanism categories, and escalation model governing how the framework restrains, steers, and verifies agent behavior without programmatic micro-management.
- **Primary Audience:** Framework architects, system developers, and compliance auditors designing, modifying, or reviewing enforcement mechanisms and policies.
- **Current Truth / SSoT:** For the empirical register of active rules, mechanisms, severity levels, and pinpoints, see [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md). Nothing here restates the live table.

## Governing principle — agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**. Hooks, server contracts, and config are **delivery channels** — they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

The only **mechanical** enforcement is **structural prevention**: credential and workspace isolation, delivery guards, model pins. Prevention by construction — never reactive detection, never content-sniffing, never a deterministic pass/fail on the substance of an agent's work.

## The four levers

Enforcement is risk-reduction; compliance is not guaranteed, and a hard block is often not the best available move.

1. **Norms** — the agent's internalised alignment with intent: prompt directives, agent and skill instructions, rules.
2. **Cost** — the token, time, and friction cost of complying against the incentive to bypass.
3. **Defaults** — whether the compliant path is mechanically the path of least resistance rather than something the agent must remember to invoke.
4. **Likelihood** — the probability a violation is detected, times its consequence. Severity moves this lever and no other.

Before escalating severity, establish that the failure is not a cost or defaults problem. Repeated stale-state assertions are not a norms failure — agents know the rule — so the fix is cheaper search and injected results, not a heavier gate.

## The mechanism categories (10 terms)

The framework organizes all enforcement into a strict 10-term controlled vocabulary:

1. **`agent persona instructions`** — guiding text in an agent's persona file (`plugins/*/agents/*.md`).
2. **`skill instructions`** — operational text in a skill's `SKILL.md`.
3. **`hook`** — registered handler on a lifecycle event (`PreToolUse`, `PostToolBatch`, `Stop`, `SessionStart`, etc.).
4. **`tool grant`** — frontmatter or config explicitly granting, scoping, or denying tools/models.
5. **`structural check`** — code-level guarantee holding regardless of agent cooperation (mount permissions, fail-closed configs, native loaders).
6. **`workflow gate`** — cross-cutting checkpoint governing when work may proceed (branch protection, task contracts).
7. **`CI job`** — named GitHub Actions workflow posting a status check.
8. **`observability`** — hook or pipeline that records or traces without gating.
9. **`doctrine`** — declared principle or policy carried in prose without direct code enforcement.
10. **`not enforced`** — declared rule or constraint with no active code, hook, tool-grant, or prompt mechanism enforcing it.

## The severity index (escalation within mechanisms)

Within each mechanism category, enforcement strength escalates along an explicit **Severity** index:

- **Instructions:** `suggestion` → `advisory` → `imperative` → `absolute`
- **Hooks:** `warning` (advisory notification) → `block` (hard stop / withholding)
- **Tool Grants:** `scoped` (allowlist restriction) → `denial` (explicit prohibition)
- **Structural Checks:** `hard guarantee` (isolation boundary) → `fail-closed` (unrecoverable termination)
- **Workflow Gates:** `checkpoint` (review obligation) → `blocking gate` (hard merge barrier)
- **CI Jobs:** `advisory check` → `required gate`
- **Observability:** `trace` → `log`
- **Doctrine:** `declared principle` → `unbacked policy`
- **Not Enforced:** `none`

## The escalation ladder (the enforcement pyramid)

The canonical doctrine of enforcement is the **enforcement pyramid**: escalate the strength of prose instructions first, and only **reluctantly** move to non-instruction enforcement, within which tooling affordances are preferred to code prohibitions.

The escalation sequence runs in strict order. A cheaper rung must be demonstrably exhausted with evidence before advancing to the next:

1. **Instruction, at escalating severity** (`suggestion` → `advisory` → `imperative` → `absolute`). The default and starting rung. Reach here first.
2. **Tooling and affordances** (tool grants/allowlists, parameter schemas, injected hydrator context, cheaper compliant defaults). Prefer shaping the agent's action space and lowering compliance friction before forbidding actions.
3. **Deterministic gates and post-hoc enforcement** (pre-commit/CI linting, schema validation, non-blocking hook checks, observational review like RBG/Marsha). Detect and flag without imposing hard programmatic blockers during execution.
4. **Code prohibitions and hard structural blocks** (sandboxing, hard policy blocks, capability funnels/chokepoints). Last resort only, entered reluctantly when all cheaper rungs demonstrably fail.

```
instruction (escalating severity) → tooling / affordances → deterministic gates / post-hoc enforcers → code prohibitions / structural blocks
```

A failure on one rung is evidence to escalate **one** step (or to try a stronger formulation on the same rung), never evidence that instruction is an invalid lever.

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition: who the agent is and what standard it holds. An **agent skill** defines a procedure: how a job gets done.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill depends on that personality's judgment register) or **permission control** (grants restricted to force a workflow split, keeping reviewer ≠ executor).
- The three review registers above name **lenses a review must apply**, not exclusive executors. Which agent carries a lens is a dispatch decision.

## Hook channel constraints

Every plugin hook shares one runtime, `lib/hooks/dispatch.py`, injected at build time. The mechanics — which events honour a block, the once-per-stop-chain guard, how a plugin's handlers merge — belong to that runtime and are stated in [`ARCHITECTURE.md`](../ARCHITECTURE.md), Hooks. What binds here:

- **No hook produces a verdict.** A hook may oblige a check; it never reads the transcript, and it never grades what the agent did with the turn it was given.
- **A block withholds a stop, never a tool call.** It is legal only where the question is a fact about the session — did the check happen — rather than a model's reading of a rule. Honoured only on Claude Code on `BLOCKABLE_EVENTS` (`Stop`, `SubagentStop`); no handler is permitted to emit a blocking disposition on `agy`.
- **Injection budget scales inversely with firing frequency.** Per-tool-call and per-turn events get a line or two; stop events, guarded to once per chain, can afford a full instruction.
- **Every agent-visible string comes from a markdown file beside the handler** (`hooks/messages/`), editable without touching code.
- **Degradation is distinguished from legitimate absence** by the handlers themselves: no evaluator configured, `$ACA_DATA` unset, and no project rules directory are all valid states and clean no-ops. A fault is never a gate.
- **A degraded check is legible to the log and not to the person who could fix it.** Handler self-reports go to stderr and no further. Known gap in the channel, not a property of it.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail.
3. **Measure before changing.** The evidence loop below is the authority for adding or escalating a mechanism. Authorial intuition is not evidence.
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it.
5. **Never guess.** With no evidence either way, current placement holds.

## Evidence loop — how the framework learns

Two flows, deliberately separated as witness and judge, so the volume and direction of framework change is governed by cross-incident pattern rather than by the salience of the most recent failure.

1. **Diagnose and route** ([`learn`](../../plugins/aops/skills/learn/SKILL.md)) — an agent that hits friction traces it to the structural cause and routes the lesson to the one destination its scope claims. It proposes no fix to anything governing future sessions; writing a standing rule needs the user to have asked.
2. **Improve the framework** (the [`triage`](../../.agents/skills/triage/SKILL.md) skill's sweep mode) — a detached pass over the accumulated issue queue on a cadence the user sets, proposing a mechanism only where recurrence or explicit direction justifies it.

A single incident that is a **bug** is fixed immediately from one report. A single incident that is an **escalation proposal** is logged and waits for the pattern.

## Sibling documents

- [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) — the current-state authoritative register.
- [task-contract.md](task-contract.md) — the work-unit contract.
- [workflow.md](workflow.md) — the workflow shape and the review-depth call.
- [sign-off.md](sign-off.md) — workflow-level review, instantiated as the PR pipeline.
- [evidence-contract.md](evidence-contract.md) — the universal claim-evidence shape.
- [auto-mode-classifier.md](auto-mode-classifier.md) — the harness's own per-action classifier.
- [agent-authority.md](../agents/agent-authority.md) — the frontmatter permission schema the grants above are expressed in.
