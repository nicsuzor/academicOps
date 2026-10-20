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

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**, with an authorized exception for procedural friction that never rules on substance: the premise-check gate (`premise_check_gate.py`), triggered on `UserPromptSubmit` (for canonical incoming agent envelopes: cross-session messages, teammate messages, task notifications, subagent handbacks) and on `PostToolUse` (for foreground subagent dispatch returns: `Agent`, `invoke_subagent`, `Task`), which refuses dispatch, messaging and channel reply tools and blocks `Stop` while an arrived report or relayed direction awaits a recorded verdict, and its verdict recorder (`premise_check_verdict.py`), which refuses a PASS whose reason lacks the checker's seven keyed lines or contradicts the judged block ([evidence-contract-enforcement.md](evidence-contract-enforcement.md)). The recorder checks the reason's shape and its consistency with the block mechanically; whether a rule yields its claim, whether the named rival is the nearest, whether an assumption line is complete, sufficiency against stakes, and relay entailment stay with the checking agent and are never mechanised. Hooks, server contracts, and config are **delivery channels** -- they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

Apart from the exception above, the only **mechanical** enforcement is **structural prevention**: credential and workspace isolation, delivery guards, model pins. Prevention by construction -- never reactive detection, never content-sniffing, never a deterministic pass/fail on the substance of an agent's work.

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

1. **Rule / nudge** -- The short-form linked reference to the rule (e.g. `[Axiom: Data Boundaries](../../plugins/rbg/skills/axioms/data-boundaries.md)` or `[Persona: Ida](../../plugins/ida/agents/ida.md)`) paired with the operative obligation or steering intent.
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
- **Review lenses bind artifacts by consequence**: The rule-compliance lens (`rbg`) evaluates target artifacts by what they build, configure, or instruct once running: an artifact breaks an axiom when its runtime consequence would violate what axioms forbid an agent to do. Mechanisms that substitute deterministic techniques (path globs, author allowlists, AST shape heuristics) for qualitative judgment fail `judgment-non-delegable`.

### Published surface and repo visibility review

The rule-compliance review lens (`rbg`, coordinated via `strategic-review` or `wf-rbg`) evaluates everything candidate changes publish across the trust boundary (diffs, commit messages and trailers, PR title and body, review replies) against destination repository visibility under `data-boundaries`. On public destinations, this enforces strict exclusion of personal identifiers, private host/project names, deployment-only agent names, PKB note/task/session IDs, commit trailers, and live telemetry before merge, comment, or push.

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

## PR Risk Taxonomy Enforcement

Pull request review and merge authority is governed by a three-tier risk taxonomy (canonical: [[kb_48809ad0]], amended in [[aops_a7366995]]). Because evaluating the operational hazard, semantic intent, and blast radius of a change inherently requires qualitative judgment, risk tier classification is executed natively by agentic verification workflows (`wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `reify/SKILL.md`) rather than deterministic CI scripts or path heuristics (`judgment-non-delegable`, `RULES.md#No Shitty NLP and Agentic-First Design`):

| Tier | Category | Scope / Characteristics | Merge Authority | Carrier Mechanism |
| :- | :- | :- | :- | :- |
| **Tier 1** | Autonomous QA-Merge | Low-risk changes: pure documentation, specifications, formatting, typing stubs (`.pyi`). | Independent QA worker merges autonomously on verified pass (`gh pr merge --squash`) and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `reify/SKILL.md` |
| **Tier 2** | Operational & Behavioral Gate | Code, workflows, tools, skills, rules, agent definitions, or tests. | Reviewer sign-off required; QA worker verifies, posts structured receipts to the PR, leaves PR open for sign-off, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `reify/SKILL.md` |
| **Tier 3** | Critical Hazard & Public Gate | Host infrastructure, credentials, manuscripts, public releases, or high external blast radius. | Exclusive principal review and merge; agents strictly forbidden from merging. QA worker verifies, posts receipts, leaves open, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `reify/SKILL.md` |

Enforcement operates through workflow merge gates (`instructions` → `imperative`):
Finish and QA templates direct QA workers to semantically evaluate PR risk against the taxonomy in a clean context. For verified Tier 1 PRs, QA workers merge autonomously via `gh pr merge --squash` and release the QA task as `done`. For Tier 2 and Tier 3 PRs, QA workers verify claims, post structured receipts to the PR, and leave the PR open for reviewer or principal sign-off. In accordance with headless worker and review lifecycle rules (`.agents/rules/headless-workers.md`, [[aops_204898b2]]), QA tasks complete as `done` with the PR URL recorded on the task record so that `/reconcile` tracks merge without human wait states; no task rests or releases into `review` for human merge gates.
