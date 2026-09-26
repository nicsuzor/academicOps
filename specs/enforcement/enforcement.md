---
id: enforcement_architecture
title: Enforcement Architecture
type: spec
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

The architectural specification detailing design rationale, theoretical mechanisms, regulatory pyramid escalation, and governance principles behind enforcement in academicOps.

- **Stated Purpose:** Defines the theoretical foundation, mechanism categories, and escalation model governing how the framework restrains, steers, and verifies agent behavior without programmatic micro-management.
- **Primary Audience:** Framework architects, system developers, and compliance auditors designing, modifying, or reviewing enforcement mechanisms and policies.
- **Current Truth / SSoT:** The empirical register of active rules, mechanisms, severity levels, and pinpoints is owed but not yet shipped on this branch. Nothing here restates a live table that does not exist.

## Governing principle -- agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**. Hooks, server contracts, and config are **delivery channels** -- they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

The only **mechanical** enforcement is **structural prevention**: credential and workspace isolation, delivery guards, model pins. Prevention by construction -- never reactive detection, never content-sniffing, never a deterministic pass/fail on the substance of an agent's work.

### Regulatory tools

Enforcement is risk-reduction; compliance is probabalistic, not guaranteed.

- **Instructions** -- the agent's internalised alignment with intent: prompt directives, agent and skill instructions, rules. Timeliness, clarity, and prominence are all relevant here.
- **Friction** -- internal requirements that slow agents down and step them through important instructions.
- **Tooling** -- making the compliant path mechanically easy.
- **Process** -- post-hoc checks and balances for compliance.

### Costs

In probabalistic enforcement, we have to match the impact of regulation to the risk:

- **Cost is measured in tokens and user attention** -- every additional mechanism introduces overhead and additional work.
- **Risk is likelihood x severity** -- the probability a violation is detected, times its consequence. Severity moves this lever and no other.

## The table schema (4 columns)

The enforcement register is structured in 4 columns:

1. **Rule / nudge** -- The short-form linked reference to the rule (e.g. `[Axiom: Data Boundaries](../../lib/axioms/data-boundaries.md)` or `[Persona: Ida](../../plugins/ida/agents/ida.md)`) paired with the operative obligation or steering intent.
2. **Mechanism** -- The carrier category from the controlled vocabulary.
3. **Severity** -- The escalation index within the mechanism.
4. **Detail** -- The pinpoint verification reference (`path:line` + operative snippet, handler function, or CI workflow) and operational state flags (`[DISABLED]`, `[MAP DRIFT]`).

## The mechanism categories and strength gradations within categories

The framework organizes all enforcement into a strict controlled vocabulary:

- **`doctrine only`** -- declared principle or policy with no explicit path to agents.
- **`instructions`** -- guiding (non-binding) text provided to an agent in escalating force: `suggestion` → `advisory` → `imperative` → `absolute`
- **`JIT injection`** -- advisory information provided at a targeted point of a workflow.
- **`structural`** -- `scoped` (tool visibility) → `permissions` (explicit grant/deny rules) → `warning` (advisory notification) → `friction` (soft restriction) → `block` (hard stop) → `protection` (mount permissions, fail-closed configs, native loaders) → `isolation` (container/sandbox)
- **`process`** `advisory check` → `routing` → `required gate`
- **`post-hoc`** `reversability` (version history) → `observability` (traces, reasons) → `proactive detection`

## Escalation: the enforcement pyramid

The canonical doctrine of enforcement is the **enforcement pyramid**: pick the least invasive level to intervene and only **reluctantly** escalate through enforcement strength and levels.

A pattern of failures at one level provides evidence to increment **strength**; increments must be exhausted before moving to another enforcement mechanism.

Concise records must be kept of assessment of suitability of each regulatory experiment.

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition: who the agent is and what standard it holds. An **agent skill** defines a procedure: how a job gets done.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill depends on that personality's judgment register) or **permission control** (grants restricted to force a workflow split, keeping reviewer ≠ executor).
- The three review registers above name **lenses a review must apply**, not exclusive executors. Which agent carries a lens is a dispatch decision.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail.
3. **Measure before changing.** The evidence loop below is the authority for adding or escalating a mechanism. Authorial intuition is not evidence.
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it.
5. **Never guess.** With no evidence either way, current placement holds.

## Evidence loop -- how the framework learns

Two flows, deliberately separated as witness and judge, so the volume and direction of framework change is governed by cross-incident pattern rather than by the salience of the most recent failure.

1. **Diagnose and route (`/learn`)** -- an agent that hits friction traces it to the structural cause and routes the lesson to the one destination its scope claims. It proposes no fix to anything governing future sessions; writing a standing rule needs the user to have asked.
2. **Improve the framework** (used to be the `triage` skill's sweep mode; currently N/A) -- a detached pass over the accumulated issue queue on a cadence the user sets, proposing a mechanism only where recurrence or explicit direction justifies it.

A single incident that is a **bug** is fixed immediately from one report. A single incident that may qualify for an **escalation proposal** is logged and waits for the pattern.
