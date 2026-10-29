---
id: enforcement_architecture
title: Enforcement Architecture
type: spec
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

The architectural specification detailing design rationale, theoretical mechanisms, proportional intervention, and governance principles behind enforcement in academicOps.

- **Stated Purpose:** Defines the theoretical foundation, mechanism categories, and proportionality model governing how the framework restrains, steers, and verifies agent behavior without programmatic micro-management.
- **Primary Audience:** Framework architects, system developers, and compliance auditors designing, modifying, or reviewing enforcement mechanisms and policies.
- **Current Truth / SSoT:** The empirical register of active rules, mechanisms, severity levels, and pinpoints is [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md). Nothing here restates that live table.

## Governing principle -- agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**, with an authorized exception for procedural friction that never rules on substance: the hearsay gate (`hearsay_gate.py`, with `premise_check_gate.py` compatibility), triggered on `UserPromptSubmit` (for canonical incoming agent envelopes: cross-session messages, teammate messages, task notifications, subagent handbacks) and on `PostToolUse` (for foreground subagent dispatch returns: `Agent`, `invoke_subagent`, `Task`), which refuses dispatch, messaging and channel reply tools and blocks `Stop` while an arrived report or relayed direction awaits a recorded verdict, paired with separated JIT reminders for report writing (`honesty.md` on `SubagentStart`) and report receiving (`hearsay.md` on `UserPromptSubmit` and once per resolved batch on `PostToolBatch`), and its verdict recorder (`premise_check_verdict.py`), which refuses a PASS whose reason lacks the checker's seven keyed lines or contradicts the judged block, and refuses REVISE or FAIL when Valid entries all hold with no unanswered ask ([evidence-contract-enforcement.md](evidence-contract-enforcement.md)). The recorder checks the reason's shape and its consistency with the block mechanically; whether a rule yields its claim, whether the named rival is the nearest, whether an assumption line is complete, sufficiency against stakes, and relay entailment stay with the checking agent and are never mechanised. Hooks, server contracts, and config are **delivery channels** -- they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

Apart from the exception above, the only **mechanical** enforcement is **structural prevention**: credential and workspace isolation, delivery guards (such as stray PR auto-retargeting from distribution branches via `.github/workflows/auto-retarget-pr.yml`), model pins. Prevention by construction -- never reactive detection, never content-sniffing, never a deterministic pass/fail on the substance of an agent's work.

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

### Protection of user attention as a binding constraint

User attention is the scarce, non-renewable resource of the system and the primary constraint under Knightian uncertainty and bounded cognitive bandwidth. Agents must strictly budget cognitive load across all interaction surfaces:

- **Autonomous resolution over interruptive escalation**: Resolve within delegated scope, defer via empirical probes, or batch non-blocking questions into scheduled digests; never interrupt interactive conversational channels for routine calibrations or valuation queries.
- **Strict serialization**: Present at most one decision or question per message; never dump lists, aggregated decision cards, or multi-question batches.
- **Progressive disclosure**: Deliver bottom-line actionable takeaways first (concise, self-contained, mechanism-mapped), reserving deep evidence, technical logs, and traces for on-demand inspection rather than upfront narration.

## The table schema (4 columns)

The enforcement register is structured in 4 columns:

1. **Rule / nudge** -- The short-form linked reference to the rule (e.g. `[Axiom: Data Boundaries](../../plugins/rbg/skills/axioms/data-boundaries.md)` or `[Persona: Ida](../../plugins/ida/agents/ida.md)`) paired with the operative obligation or steering intent.
2. **Mechanism** -- The carrier category from the controlled vocabulary.
3. **Severity** -- The force of intervention within the mechanism.
4. **Detail** -- The pinpoint verification reference (`path:line` + operative snippet or handler function) and operational state flags (`[DISABLED]`, `[MAP DRIFT]`).

## Mechanism categories and force gradations

The framework organizes all enforcement into a strict controlled vocabulary:

- **`doctrine only`** -- declared principle or policy with no explicit path to agents.
- **`instructions`** -- guiding text provided to an agent, by force: `suggestion`, `advisory`, `imperative`, `absolute`.
- **`JIT injection`** -- advisory information provided at a targeted point of a workflow.
- **`structural`** -- by scope and force: `scoped` (tool visibility), `permissions` (explicit grant/deny rules), `warning` (advisory notification), `friction` (soft restriction), `block` (hard stop), `protection` (mount permissions, fail-closed configs, native loaders), `isolation` (container/sandbox).
- **`process`** -- by review or gate requirement: `advisory check`, `routing`, `required gate`.
- **`post-hoc`** -- by auditability: `reversability` (version history), `observability` (traces, reasons), `proactive detection`.

### Prompt hydration delivery channel (JIT injection)

Prompt hydration (`search_the_pkb`, detailed in [`specs/agents/prompt-hydration.md`](../agents/prompt-hydration.md)) serves as a JIT injection delivery channel on incoming channel messages and `UserPromptSubmit` (and `PreInvocation` on agy) that grounds the agent turn in existing knowledge base context:

- **Whole-prompt hydration**: Sends the full human prompt text, incoming channel message, or agent report up to 8 KB (`8192` characters) without arbitrary 200-character truncation, unwrapping `<channel>` and message envelopes when present.
- **Peer reports, subagent handbacks, and task notifications included**: Incoming peer reports, subagent handbacks, and task notifications are searched against the PKB to provide relevant grounding context.
- **Slash command gating**: Suppresses PKB calls on argument-less slash commands (`/cmd`); slash commands with arguments (`/cmd <arg>`) send `<arg>` whole up to 8 KB.
- **Session attribution metadata**: Every hydration query passes a `_session` payload containing `session_id`, `prompt_id`, `agent_id`, `caller: "hook"`, and `surface` (`"agy"`, `"github-actions"`, or `"claude-code"`), matching `prompt_id` across the MCP request and hook span.
- **Quiet failure & empty handling**: Injects nothing on empty or whitespace search results; on server/network failure, injects a single concise line naming the failure cause without dumping stack traces or polluting agent context.

## Proportionality and force of intervention

Enforcement is chosen by **proportionality, frequency, scope, and force of intervention**, assessed in context rather than as a mechanical ladder.

Pick the least invasive intervention that fits the context and risk (`likelihood × severity`), weighing token and attention cost at each firing frequency against the consequence of a miss. Recurring failures provide evidence to adjust the force or mechanism in context.

### Proportional intervention options pass

Any change that shapes agent behaviour (hooks, review lenses, branch protection, instructions, project rules, agent personas) must run through the enforcement options against this specification first before proposing or implementing a mechanism.

- **Trigger:** Any proposed addition, modification, or escalation of a measure intended to shape agent behaviour.
- **Referent:** This specification (`specs/enforcement/enforcement.md`).
- **Options:** The options to run through are the categories in the controlled vocabulary (§ "Mechanism categories and force gradations") and their force gradations, evaluated from least-invasive to most-invasive:
  1. `doctrine only`
  2. `instructions` (`suggestion` → `advisory` → `imperative` → `absolute`)
  3. `JIT injection`
  4. `structural` (`scoped` → `permissions` → `warning` → `friction` → `block` → `protection` → `isolation`)
  5. `process` (`advisory check` → `routing` → `required gate`)
  6. `post-hoc` (`reversability` → `observability` → `proactive detection`)
- **Default and burden of proof:** Default to instructions. Instructions work in the large majority of cases; the burden of proof is on adding or escalating to a heavier mechanism.
- **Changes to Ida are made, then tested by use:** a change at the `instructions` level to Ida (her persona, her instruction files, the skills she checks and relays with) is made on the user's direction without an empirical test first; if it does not work, the next experiment follows. We learn by doing and talking and cannot afford to wait (user ruling, 2026-10-29). Keep the concise record of each experiment required by the escalation threshold above; measurement gates mechanisms, not instructions. The PKB workflow template `aops-wf-framework-change` step 5 carries the same ruling.
- **Escalation threshold:** A pattern of failures provides evidence to increment force or mechanism; increments must be exhausted before escalating. Concise records must be kept of assessment of suitability of each regulatory experiment.

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition: who the agent is and what standard it holds. An **agent skill** defines a procedure: how a job gets done.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill depends on that personality's judgment register) or **permission control** (grants restricted to force a workflow split, keeping reviewer ≠ executor).
- The three review registers above name **lenses a review must apply**, not exclusive executors. Which agent carries a lens is a dispatch decision.
- **Supervisor upfront proportionality and altitude calibration (`james`)**: Before dispatching reviewers (`wf-dialectical-design`, `wf-review`, `strategic-review`), the Supervisor (`james`) sets target altitude and calibrates review proportionality to the artifact's stakes -- investing multi-round dialectical refinement and higher-capability models (`pro`) on high-stakes architecture, specifications, or core rules, while running a single-round sanity pass on lighter models (`flash` / `flash_lite`) for routine changes.
- **Review lenses bind artifacts by consequence**: The compliance lens (`rbg`) evaluates target artifacts by what they build, configure, or instruct once running: an artifact breaks an axiom when its runtime consequence would violate what axioms forbid an agent to do. Mechanisms that substitute deterministic techniques (path globs, author allowlists, AST shape heuristics) for qualitative judgment fail `judgment-non-delegable`.
- **Three non-overlapping review roles (all returning `PASS`, `REVISE`, or `FAIL`)**:
  - **Compliance lens (`rbg`, template `wf-rbg`)**: Evaluates compliance with universal axioms, project rules, scope of delegated authority (_ultra vires_), data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`). Confined strictly to static semantic evaluation of artifact text/diff and governing rule/spec sources (including companion specs); enforces upfront stopping on _ultra vires_ or disproportionate changes and per-claim fail-fast without searching the repo to author fixes; does not run tests/probes or scan codebase callers (Quality & Requirement Satisfaction) or evaluate the core premise and PKB graph congruence (Strategic Direction & Congruence).
  - **Strategic direction & congruence lens (`pauli`, template `wf-strategic-fit`)**: Evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing PKB material -- testing objective alignment, necessity, parsimony, precedent, flawed reasoning, untested assumptions, negative space, and cross-task lifecycle coherence (`PASS`/`REVISE`/`FAIL`) strictly on the PKB graph from an inline briefing without inspecting repository code or filesystem templates. Does not inspect source code for axiom violations (Compliance) or run tests/probes (Quality & Requirement Satisfaction).
  - **Quality & requirement-satisfaction lens (`marsha`, template `wf-qa`)**: Evaluates whether the work actually delivers on its requirements to an ambitious quality standard ("amazingly good", not merely working) across actual rendered multimodal outputs (never code alone or simulated renders), runtime execution, and primary sources against whatever specifications, requirements, or acceptance criteria are available. Treats the absence of any specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL`). Enforces upfront stopping on missing criteria and per-claim fail-fast. Does not evaluate the strategic core premise or rule on axioms.
- **Shared review briefing (`wf-review`, `wf-dialectical-design`)**: Every review dispatch across all three roles draws its brief from the shared review briefing in `wf-review`. The brief quotes the originating request verbatim with its source identifier in a section read before the pull request, branch name, or diff, and provides whatever specifications, requirements, or acceptance criteria exist, ensuring reviewers evaluate intent, proportion, and verifiable criteria before inspecting implementation details. Composite review coordinates the three distinct role components (`pauli`, `rbg`, `marsha`) under `james` and reconciles their findings into a single unified verdict (`PASS`, `REVISE`, or `FAIL`). Any expert reviewer's `FAIL` makes the combined verdict `FAIL`; the consolidating agent never downgrades or softens it (addressing an over-harsh reviewer is the user's job to review the underlying reviewer agent).

### Published surface and repo visibility review

The rule-compliance review lens (`rbg`, coordinated via `strategic-review` or `wf-rbg`) evaluates everything candidate changes publish across the trust boundary (diffs, commit messages and trailers, PR title and body, review replies) against destination repository visibility under `data-boundaries`. On public destinations, this enforces strict exclusion of personal identifiers, private host/project names, deployment-only agent names, PKB note/task/session / conversation IDs, commit trailers, and live telemetry before merge, comment, or push.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail.
3. **Measure before changing a mechanism.** The evidence loop below is the authority for adding or strengthening a mechanism. Authorial intuition is not evidence. Instruction-level changes to Ida are made on direction and tested by use (see the options pass above).
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it.
5. **Never guess.** With no evidence either way, current placement holds.

## Evidence loop -- how the framework learns

Two flows, deliberately separated as witness and judge, so the volume and direction of framework change is governed by cross-incident pattern rather than by the salience of the most recent failure.

1. **Diagnose and route (`/learn`)** -- an agent that hits friction traces it to the structural cause and routes the lesson to the one destination its scope claims. It proposes no fix to anything governing future sessions; writing a standing rule needs the user to have asked.
2. **Improve the framework** (used to be the `triage` skill's sweep mode; currently N/A) -- a detached pass over the accumulated issue queue on a cadence the user sets, proposing a mechanism only where recurrence or explicit direction justifies it.

A single incident that is a **bug** is fixed immediately from one report. A single incident that may qualify for a **mechanism proposal** is logged and waits for the pattern.

## PR Risk Taxonomy Enforcement

Pull request review and merge authority is governed by a three-tier risk taxonomy. Because evaluating the operational hazard, semantic intent, and blast radius of a change inherently requires qualitative judgment, risk tier classification is executed natively by agentic verification workflows ([`wf-finish.md`](../../plugins/ida/skills/workflow-library/workflows/wf-finish.md), [`wf-code-task-base.md`](../../plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md), [`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md), [`plugins/ida/skills/reify/SKILL.md`](../../plugins/ida/skills/reify/SKILL.md)) rather than deterministic CI scripts or path heuristics ([`judgment-non-delegable`](../../plugins/rbg/skills/axioms/judgment-non-delegable.md)):

| Tier | Category | Scope / Characteristics | Merge Authority | Carrier Mechanism |
| :- | :- | :- | :- | :- |
| **Tier 1** | Autonomous QA-Merge | Low-risk standalone changes: pure documentation, standalone retrospective specifications with no following build, formatting, typing stubs (`.pyi`). (A spec or design stage preceding a feature build never merges autonomously on its own; it opens a draft PR, the feature follows on the same branch and PR, and both merge together after full review.) | Independent QA worker merges autonomously on verified pass (`gh pr merge --squash`) and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `plugins/ida/skills/reify/SKILL.md` |
| **Tier 2** | Operational & Behavioral Gate | Code, workflows, tools, skills, rules, agent definitions, or tests. | Reviewer sign-off required; QA worker verifies, posts structured receipts to the PR, leaves PR open for sign-off, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `plugins/ida/skills/reify/SKILL.md` |
| **Tier 3** | Critical Hazard & Public Gate | Host infrastructure, credentials, manuscripts, public releases, or high external blast radius. | Exclusive principal review and merge; agents strictly forbidden from merging. QA worker verifies, posts receipts, leaves open, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md`, `plugins/ida/skills/reify/SKILL.md` |

Enforcement operates through workflow merge gates (`instructions`, `imperative`):
Finish and QA templates direct QA workers to semantically evaluate PR risk against the taxonomy in a clean context. Under the one-branch, one-PR lifecycle for spec-then-build workflows, the spec goes out as a draft PR into the base branch carrying the spec or design, and its review verdict is recorded on that PR; the spec task never merges on its own. After approval, the feature is built on the same branch and PR, with the spec still editable as more is learned; the PR flips to ready once the feature is written and ready for full review, without waiting for approval; spec and feature merge together after full review. For verified standalone Tier 1 PRs with no following build, QA workers merge autonomously via `gh pr merge --squash` and release the QA task as `done`. For Tier 2 and Tier 3 PRs, QA workers verify claims, post structured receipts to the PR, and leave the PR open for reviewer or principal sign-off. Under headless worker and review lifecycle rules, QA tasks complete as `done` with the PR URL recorded on the task record so that `/reconcile` tracks merge without human wait states; no task rests or releases into `review` for human merge gates.
