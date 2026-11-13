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
- **Current Truth / SSoT:** The empirical register of active rules, mechanisms, severity levels, and pinpoints is [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md), governed by [`specs/enforcement/enforcement-map.md`](enforcement-map.md). When editing `specs/ENFORCEMENT-MAP.md`, every row must **only** reference a specific rule derived from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) and applicable to agents working in any third-party project; workflows are not rules and do not enforce rules, and creating or modifying workflows must never produce token enforcement map rows (as the only applicable rule is "agents must follow workflows given to them" and nothing more than that). Nothing here restates that live table.

## Governing principle -- agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**, with an authorized exception for procedural friction that never rules on substance: the hearsay gate (`hearsay_gate.py`, with `premise_check_gate.py` compatibility), triggered on `UserPromptSubmit` (for canonical incoming agent envelopes: cross-session messages, teammate messages, task notifications, subagent handbacks), `SubagentStop` (for subagent return events), and on `PostToolUse` (for foreground subagent dispatch returns: `Agent`, `invoke_subagent`, `Task`), which refuses dispatch, messaging and channel reply tools and blocks `Stop` while an arrived report or relayed direction awaits a recorded verdict, paired with separated JIT reminders for report writing (`honesty.md` on `SubagentStart` in Claude Code and first `PreInvocation` in agy), a one-time `PreToolUse` pre-handback check on subagent `send_message` in agy, and report receiving (`hearsay.md` on `UserPromptSubmit` and once per resolved batch on `PostToolBatch`), and its verdict recorder (`premise_check_verdict.py`), which refuses a PASS whose reason lacks the checker's seven keyed lines or contradicts the judged block, and refuses REVISE or FAIL when Valid entries all hold with no unanswered ask ([evidence-contract-enforcement.md](evidence-contract-enforcement.md)). The recorder checks the reason's shape and its consistency with the block mechanically; whether a rule yields its claim, whether the named rival is the nearest, whether an assumption line is complete, sufficiency against stakes, and relay entailment stay with the checking agent and are never mechanised. In accordance with the enforcement pyramid, premise basis checking operates at Level 2 (Review Lens & Checker Evaluation) and Level 1 (Instructions): report authors provide natural language assertions with inline citations, and checking agents evaluate evidence sufficiency qualitatively under `Supported:` rather than via Level 3 mechanical basis regex matching or rank arithmetic (`specs/enforcement/handback-format-design.md`). Hooks, server contracts, and config are **delivery channels** -- they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

Apart from the exception above, the only **mechanical** enforcement is **structural prevention**: credential and workspace isolation, delivery guards (such as stray PR auto-retargeting from distribution branches to `dev` via `.github/workflows/auto-retarget-pr.yml` and repository ruleset push protection locking `main` against direct pushes and non-release PR merges with release pipeline bypass), model pins. Prevention by construction -- never reactive detection, never content-sniffing, never a deterministic pass/fail on the substance of an agent's work.

## The framework-workflow enforcement line

Enforcement in academicOps is strictly defined as **framework-level process rules** (compliance with our processes), never **workflow-substance rules** (which govern the substance of what is done in client repos or domain-specific workflows).

- **Framework-level process rules**: Universal behavioral and process invariants derived from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) governing how agents operate within the framework across any third-party project, regardless of repository or task domain. These include the universal axioms, task lifecycle contracts (`claim_task` -> `release_task` with verified evidence), authority boundaries, data boundaries, headless worker invariants, and independent review gates.
- **Workflow-substance rules**: Domain-specific instructions, procedures, business logic, heuristics, or formats governing the substance of client repository work or specific operational routines (e.g. correspondence watermarks, Telegram reply button layouts or reaction legends, dbt model transformations, streamlit layout schemas, literature search strategies).
- **Core doctrine**: Workflows are not rules and do not enforce rules. Workflow substance lives strictly as **instructions inside their workflows** (`wf-*.md` or `SKILL.md`), NEVER as framework-level enforcement rules, NEVER in `specs/enforcement/`, and NEVER on the universal enforcement register ([`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md)).
- **The only framework rule for workflows**: The only applicable rule is simply that **agents must follow workflows given to them** and nothing more than that. Creating or modifying workflows must not produce token enforcement map rows. When an agent fails to follow an existing workflow, the root cause is poor compliance with workflows (or that the workflow instructions were unclear or missing), NOT a missing framework enforcement rule. Adding a bespoke framework rule, spec, gate, or enforcement map row for a specific workflow is an over-engineering defect.

### The operational test for rule classification

When authoring, evaluating, or reviewing any proposed or existing rule, specification, hook, or enforcement-map row, apply this three-step test:

1. **Axiom-Derivation and Third-Party Project Applicability Test**: Does the requirement derive from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) and apply universally to agents working in _any_ third-party project across all client repositories, domains, and tasks (e.g. how tasks are claimed, cited, verified, proven with evidence, bounded for safety/PII, or reported)?
   - _If YES:_ It is a candidate **framework-process rule** eligible for `specs/ENFORCEMENT-MAP.md`.
   - _If NO_ (it is a repository-local project rule specific only to `academicOps`, or specific to email sweeps, Telegram messaging, dbt transformations, paper peer-reviews, daily note formatting, or other domain workflows): It must NOT appear on `specs/ENFORCEMENT-MAP.md`.
2. **Substance vs. Process Test**: Does the requirement prescribe _what_ domain content, heuristics, or workflow steps to execute, OR _how_ axiom-derived operating processes (authority, evidence, truth maintenance, lifecycle) are complied with across any third-party project?
   - If it prescribes domain substance or workflow execution details, it MUST live solely as an instruction inside that workflow template (`wf-*.md`) or skill (`SKILL.md`). Workflows are not rules and do not enforce rules; it MUST NOT be given a spec in `specs/enforcement/` and MUST NOT produce a token row on `specs/ENFORCEMENT-MAP.md`.
3. **General Compliance Test**: If an agent failed to follow the instruction, does the failure stem from an absence of a general axiom-derived framework rule, or from failing to follow the applicable workflow?
   - The only applicable rule is: _agents must follow workflows given to them_ and nothing more than that. The remedy is to improve the clarity of the workflow instructions or enforce existing axiom-derived rules (e.g. `do-one-thing`, `cite-sources`), NEVER to invent a new bespoke enforcement rule, spec, gate, or enforcement-map row for that workflow.

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

## The enforcement register (schema & inclusion)

The enforcement register ([`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md)) is the canonical empirical state document mapping active behavioral controls. Every row in `specs/ENFORCEMENT-MAP.md` must **only** reference a specific rule derived from our axioms (`plugins/rbg/skills/axioms/`) and applicable to agents working in any third-party project -- never repository-local project rules, subsystem specifications, or workflows (workflows are not rules and do not enforce rules; creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that). Its table schema, row-by-row inclusion boundaries, and concision invariants are governed by [`specs/enforcement/enforcement-map.md`](enforcement-map.md).

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

### Plugin startup delivery channel (JIT injection)

Every plugin runs a `SessionStart` hook that injects a plugin-scoped `CORE.md` (at most 20 lines) into ambient session context, providing concise guidance for that plugin's features without extraneous or agent-specific text ([`specs/agents/startup-core-routing.md`](../agents/startup-core-routing.md)).

## Proportionality and force of intervention

Enforcement is chosen by **proportionality, frequency, scope, and force of intervention**, assessed in context rather than as a mechanical ladder.

Pick the least invasive intervention that fits the context and risk (`likelihood × severity`), weighing token and attention cost at each firing frequency against the consequence of a miss. Recurring failures provide evidence to adjust the force or mechanism in context.

### Proportional intervention options pass

Any change that shapes agent behaviour (hooks, review lenses, branch protection, instructions, project rules, agent personas) must run through the enforcement options against this specification first before proposing or implementing a mechanism. Creating or modifying workflows (`wf-*.md`, `SKILL.md`, or process templates) is not a rule change and does not enforce rules -- the only applicable rule is "agents must follow workflows given to them" and nothing more than that -- so workflow edits must never produce token rows in `specs/ENFORCEMENT-MAP.md`.

- **Trigger:** Any proposed addition, modification, or escalation of a measure intended to shape agent behaviour.
- **Referent:** This specification (`specs/enforcement/enforcement.md`).
- **Options:** The options to run through are the categories in the controlled vocabulary (§ "Mechanism categories and force gradations") and their force gradations, evaluated from least-invasive to most-invasive:
  1. `doctrine only`
  2. `instructions` (`suggestion` → `advisory` → `imperative` → `absolute`)
  3. `JIT injection`
  4. `structural` (`scoped` → `permissions` → `warning` → `friction` → `block` → `protection` → `isolation`)
  5. `process` (`advisory check` → `routing` → `required gate`)
  6. `post-hoc` (`reversability` → `observability` → `proactive detection`)
- **Default and burden of proof:** Default to instructions. Instructions work in the large majority of cases; the burden of proof is on adding or escalating to a heavier mechanism. No new hooks without a full spec. No new mechanical enforcement of any kind without a full spec and a decision history filed to show enforcement map escalation step by step.
- **Changes to Ida are made, then tested by use:** a change at the `instructions` level to Ida (her persona, her instruction files, the skills she checks and relays with) is made on the user's direction without an empirical test first; if it does not work, the next experiment follows. We learn by doing and talking and cannot afford to wait (user ruling, 2026-10-29). Keep the concise record of each experiment required by the escalation threshold above; measurement gates mechanisms, not instructions. The framework-change workflow template carries the same ruling.
- **Supervised epic dispatch architecture (`instructions` / `imperative` + `process` / `routing`)**: Dispatches repo-scoped epic tasks directly from `/q` to polecat containers running `/supervise` under `james` on a calibrated coordinator model, moving `/reify` inside container supervision to assemble workflows onto a single combined task body by default (handling design, dialectical review, build, and PR verification in-session with incremental `git push` checkpoints), eliminating multi-task coordination overhead while restricting follow-up task creation strictly to out-of-session boundaries (different repository, different time, or external agent delivery).
- **Escalation threshold:** A pattern of failures provides evidence to increment force or mechanism; increments must be exhausted before escalating. Concise records must be kept of assessment of suitability of each regulatory experiment.

### Bounded Helpers and Subagent Lifecycle

To prevent unsustainable context growth and token burn across background operations, subagent helpers are kept bounded:

- **Level 1 (Instructions / Advisory & Imperative)**: On an agent-idle hook and at task boundaries, agents are encouraged (not required) to consider whether a subagent helper has run too long and decide whether to cull it, and to dispatch fresh subagents for unrelated tasks rather than reusing long-running helpers. Batched operations and the 5-minute prompt cache TTL are imperative instructions.

### Recurring Jobs: Change-Only and Single-Flight

Recurring background jobs and sweeps enforce:

- **Level 1 (Instructions / Imperative)**: Inspect execution cursor at Step 0 and exit immediately with zero writes and zero subagent dispatches when no delta is detected (`since: <cursor>`).
- **Level 4 (Structural / Block)**: Concurrency lock (in-progress marker with heartbeat < 15 min) prevents overlapping or concurrent runs of the same recurring job.

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition: who the agent is and what standard it holds. An **agent skill** defines a procedure: how a job gets done.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill depends on that personality's judgment register) or **permission control** (grants restricted to force a workflow split, keeping reviewer ≠ executor).
- **Agent definitions are the single source of truth for persona tool boundaries**: Agent-specific tool and action prohibitions reside in the agent definitions (`pauli.md`, `rbg.md`, `marsha.md`) and build tool permissions (`build/tool_map.toml`), never duplicated across individual skill procedures (`SKILL.md`).
- The three review registers above name **lenses a review must apply**, not exclusive executors. Which agent carries a lens is a dispatch decision.
- **Supervisor upfront proportionality and altitude calibration (`james`)**: Before dispatching reviewers (`wf-dialectical-review`, `strategic-review`), the Supervisor (`james`) sets target altitude and calibrates review proportionality to the artifact's stakes -- investing multi-round dialectical refinement and higher-capability models (`pro`) on high-stakes architecture, specifications, or core rules, while running a single-round sanity pass on lighter models (`flash` / `flash_lite`) for routine changes.
- **Reviewer self-fixes for uncontroversial issues**: When a reviewer (`james`, `rbg`, `marsha`, `pauli`) identifies defects that can be readily resolved without controversy--specifically updating language, scrubbing private identifiers or session trailers (`data-boundaries`), fixing dead links, or correcting formatting--it applies the fix immediately, commits with an explanatory commit message (`fix(review): ...`), and itemizes the fix in its handback report. Reviewers do not return `REVISE` solely for uncontroversial issues they have repaired. Issues lacking a reasonably deterministic solution (architectural trade-offs, missing specifications, scope drift) must never be guessed; they are recorded as findings requiring worker revision (`REVISE` or `FAIL`).
- **Review lenses bind artifacts by consequence**: The compliance lens (`rbg`) evaluates target artifacts by what they build, configure, or instruct once running: an artifact breaks an axiom when its runtime consequence would violate what axioms forbid an agent to do. Mechanisms that substitute deterministic techniques (path globs, author allowlists, AST shape heuristics) for qualitative judgment fail `judgment-non-delegable`. Furthermore, reviewers evaluate against the **non-mechanical baseline** first: when an agent workflow template (`wf-*`) or skill instruction (`SKILL.md`) meets the request across its class, building an executable software engine, script, CLI utility, or programmatic wrapper is prohibited as an over-engineered defect under `no-over-engineering` and `proportionate`.
- **Three non-overlapping review roles (all returning `PASS`, `REVISE`, or `FAIL`)**:
  - **Compliance lens (`rbg`, template `wf-rbg`)**: Evaluates compliance with universal axioms, project rules, scope of delegated authority (_ultra vires_), data boundaries, and the enforcement pyramid (`specs/enforcement/enforcement.md`). Confined strictly to static semantic evaluation of artifact text/diff and governing rule/spec sources (including companion specs); verifies that task-creating skills uphold Single Source of Truth and runtime workflow composition without embedding hardcoded workflow branching or QA restrictions; verifies entry validity on enforcement map modifications (confirming that every row only references a specific rule derived from our axioms and applicable to agents working in any third-party project, never a repository-local project rule, subsystem feature spec, or workflow); enforces upfront stopping on _ultra vires_, disproportionate changes, or over-engineered mechanical machinery (the Gate 0 Non-Mechanical Baseline Check) and per-claim fail-fast with an uncontroversial self-fix carve-out (scrubbing private data, language updates, pinpoint corrections) without searching the repo to author complex fixes; does not run tests/probes or scan codebase callers (correctness testing belongs to authors/QA), does not judge qualitative taste or UX (Quality lens `marsha`), or evaluate graph strategy (Strategic Fit `pauli`).
  - **Strategic direction & congruence lens (`pauli`, template `wf-strategic-fit`)**: Evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing PKB material -- testing objective alignment, necessity, parsimony, precedent, flawed reasoning, untested assumptions, negative space, and cross-task lifecycle coherence (`PASS`/`REVISE`/`FAIL`) strictly on the PKB graph from an inline briefing without inspecting repository code or filesystem templates. Does not inspect source code for axiom violations (Compliance), does not judge visual/prose aesthetics (Quality lens `marsha`), or run tests/probes (QA).
  - **Qualitative quality lens (`marsha`, procedure `verify`)**: Evaluates the live output artifact as its audience meets it against intended purpose, aesthetic grace, and excellence standards across live rendered multimodal outputs. Calibrates depth proportionately (cursory/low bar for routine objects; rigorous for high-stakes deliverables). Does not check truth or fidelity (hearsay checker and `premise-check`), does not execute test suites or runtime correctness checks (authoring worker and independent QA `wf-qa`), does not rule on axioms (Rule Compliance `rbg`), and does not evaluate graph strategy (Strategic Fit `pauli`).
- **Shared review briefing (`wf-dialectical-review`)**: Every review dispatch across all three roles draws its brief from the shared review briefing in `wf-dialectical-review`. The brief quotes the originating request verbatim with its source identifier in a section read before the pull request, branch name, or diff, and provides whatever specifications, requirements, or acceptance criteria exist, ensuring reviewers evaluate intent, proportion, and verifiable criteria before inspecting implementation details. Composite review coordinates the three distinct role components (`pauli`, `rbg`, `marsha`) under `james` and reconciles their findings into a single unified verdict (`PASS`, `REVISE`, or `FAIL`). Any expert reviewer's `FAIL` makes the combined verdict `FAIL`; the consolidating agent never downgrades or softens it (addressing an over-harsh reviewer is the user's job to review the underlying reviewer agent).

### Published surface and repo visibility review

The rule-compliance review lens (`rbg`, coordinated via `strategic-review` or `wf-rbg`) evaluates everything candidate changes publish across the trust boundary (diffs, commit messages and trailers, PR title and body, review replies) against destination repository visibility under `data-boundaries`. On public destinations, this enforces strict exclusion of personal identifiers, private host/project names, deployment-only agent names, PKB note/task/session / conversation IDs, commit trailers, and live telemetry before merge, comment, or push.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail.
3. **Measure before changing a mechanism.** The evidence loop below is the authority for adding or strengthening a mechanism. Authorial intuition is not evidence. Instruction-level changes to Ida are made on direction and tested by use (see the options pass above).
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it.
5. **Never guess.** With no evidence either way, current placement holds.
6. **Agentic-first over mechanical code.** Smarts belong to agents; code is a permanent maintenance liability. Never build scripts, CLI tools, or programmatic wrappers where an agent workflow instructing agents to exercise qualitative judgment meets the request.
7. **Proportion measures mechanism necessity and change size across both code and prose.** A change that touches multiple files, adds specifications, introduces calibration schemes, or registers enforcement-map rows where a simple instruction or workflow edit suffices is disproportional and an over-engineering defect. Meeting a request with the least mechanism means the smallest change that works, never expanding small wording edits into cross-tier architectural projects.

## Evidence loop -- how the framework learns

Two flows, deliberately separated as witness and judge, so the volume and direction of framework change is governed by cross-incident pattern rather than by the salience of the most recent failure.

1. **Diagnose and route (`/learn`)** -- an agent that hits friction traces it to the structural cause and routes the lesson to the one destination its scope claims. It proposes no fix to anything governing future sessions; writing a standing rule needs the user to have asked.
2. **Improve the framework** (used to be the `triage` skill's sweep mode; currently N/A) -- a detached pass over the accumulated issue queue on a cadence the user sets, proposing a mechanism only where recurrence or explicit direction justifies it.

A single incident that is a **bug** is fixed immediately from one report. A single incident that may qualify for a **mechanism proposal** is logged and waits for the pattern.

## PR Risk Taxonomy Enforcement

Pull request review and merge authority is governed by a three-tier risk taxonomy. Because evaluating the operational hazard, semantic intent, and blast radius of a change inherently requires qualitative judgment, risk tier classification is executed natively by agentic verification workflows ([`wf-finish.md`](../../plugins/ida/skills/workflow-library/workflows/wf-finish.md), [`wf-code-task-base.md`](../../plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md), [`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md)) rather than deterministic CI scripts or path heuristics ([`judgment-non-delegable`](../../plugins/rbg/skills/axioms/judgment-non-delegable.md)):

| Tier | Category | Scope / Characteristics | Merge Authority | Carrier Mechanism |
| :- | :- | :- | :- | :- |
| **Tier 1** | Autonomous QA-Merge | Low-risk changes: pure documentation, formatting, typing stubs (`.pyi`). | Independent QA worker merges autonomously on verified pass (`gh pr merge --squash`) and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |
| **Tier 2** | Operational & Behavioral Gate | Code, workflows, tools, skills, rules, agent definitions, or tests. | Reviewer sign-off required; QA worker verifies, posts structured receipts to the PR, leaves PR open for sign-off, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |
| **Tier 3** | Critical Hazard & Public Gate | Host infrastructure, credentials, manuscripts, public releases, or high external blast radius. | Exclusive principal review and merge; agents strictly forbidden from merging. QA worker verifies, posts receipts, leaves open, and releases task as `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |

Enforcement operates through workflow merge gates (`instructions`, `imperative`):
Finish and QA templates direct reviewing agents to semantically evaluate PR risk against the taxonomy in a clean context. Worker pull requests open as a draft (`gh pr create --draft`) and are marked ready for review (`gh pr ready`) only after the independent check passes and proportionate review by independent agents is posted to the PR thread, without waiting for approval. Under single-session supervised execution (`/supervise`), execution runs Stages 1-4 (design, subagent dialectical review, build, and QA/PR verification) in one combined repo-scoped task by default, keeping subagent dialectical review, incremental `git push` checkpoints, and PR verification inside the single container session rather than requiring separate Stage 1 / Stage 2 / QA child tasks unless out-of-session splitting is explicitly warranted. The container opens the single draft PR (`gh pr create --draft`) into `dev` carrying the build and any spec change, with the spec still editable as more is learned; the PR flips to ready (`gh pr ready`) once the independent check passes and proportionate review by independent agents is posted to the PR thread, without waiting for approval; spec and feature merge together after full review. For verified standalone Tier 1 PRs, autonomous QA marks the PR ready (`gh pr ready`), merges via `gh pr merge --squash`, and releases the task as `done`. For Tier 2 and Tier 3 PRs, reviewers verify claims, post structured receipts to the PR, mark the draft PR ready for review (`gh pr ready`), and leave the PR open for reviewer or principal sign-off. Under headless worker and review lifecycle rules, workers complete as `done` with the PR URL recorded on the task record so that `/reconcile` tracks merge without human wait states; no task rests or releases into `review` for human merge gates.

### Pre-Approval Readiness and Post-Approval Rebase

Before approval (by the principal or designated reviewer), a pull request requires green checks and an independent proportionate review, with review comments and requested changes addressed; mergeability against the base branch is not required before approval. Rebase and conflict-resolution passes must not be executed while a PR is awaiting approval. Bringing a pull request up to date with its base branch and resolving merge conflicts happens after approval, just before merge.

### Non-PR Task Verification and Lifecycle

For tasks that do not produce pull requests (such as empirical analyses, documentation updates, research tasks, and operational maintenance), workflow templates define whether a task warrants an independent verification check (such as empirical analyses requiring numerical replication, high-impact specification changes, or formal qualitative audits). Workflows that do not warrant an additional verification pass compose no QA follow-up.

Worker self-release to `done` applies across all tasks (PR and non-PR): when a worker satisfies all frozen acceptance criteria with concrete verifiable evidence recorded in its handback report, it releases the task directly to `done`. Workers are never forced into `review` awaiting external verification. If a separate QA task was minted, that QA task executes independently against the completed artifact; if the QA check fails, the QA worker releases its own task as `failed` with diagnostic evidence.

### Worker State-Only Invariant & Parent Rollup Lifecycle

Per ADR-0002 ([`specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md`](../decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md)), execution environments distinguish two worker modes:

- **Plain leaf workers (`/pull`)**: A plain leaf worker executing an already-reified task operates strictly state-only: it may only mutate that task's own state (checking off acceptance criteria, recording verifiable evidence under `## Report`, transitioning status). Leaf workers never reify workflows, create child tasks, inspect or modify edges across other tasks, compute reverse graph dependencies, or mint follow-up verification tasks; unblocking, sequencing, and parent rollup belong exclusively to the graph engine, dispatcher, and background truth maintenance (`wf-reconcile`).
- **Container coordinators (`/supervise`)**: A container coordinator claimed on a repository-scoped epic task enriches its claimed task by assembling workflows via `/reify` in-session onto a single combined task body by default, coordinates subagent fan-out and reviews with incremental `git push` checkpoints, and creates/wires repository-scoped follow-up tasks on the graph via `/q` solely when work explicitly cannot be completed in-session (different repository, different time, or workflow-mandated separate external agent/session).

When all open children under a composite task (`parent`) reach `done`, the composite task does not automatically close if it contains substantive acceptance criteria. Instead, it becomes `ready` for an explicit synthesis and sign-off pass. Background truth maintenance (`wf-reconcile`) is the authoritative process that detects completed child sets, verifies composite criteria, and transitions parent tasks.

### Operational Event Ingestion and Session Waking

Worker container completion is recorded via the exit listener, OpenTelemetry `polecat.container.exit` spans, and the `polecat_events` MCP queue. The operational dashboard daemon (`specs/telegram/mini-app-dashboard-integration.md`) acts as the single consumer of `polecat_events` and repository webhooks, waking listening agent sessions over its authenticated HTTP/SSE channel bridge. Direct UNIX domain socket pushes (`[polecat-exit]`) and in-session client polling loops are retired.

### Observability and Telemetry Failure Gating

Enforcement of zero silent telemetry failures operates across client hooks, tracer runtimes, and verdict gates ([`specs/observability/telemetry-failure-surfacing.md`](../observability/telemetry-failure-surfacing.md)):

- **JIT Injection & Structural Warnings (`warning`)**: On interactive surfaces and CI runners, unconfigured trace endpoints and export errors (HTTP 401/403 refusals, HTTP 5xx errors, connection timeouts) emit conspicuous standard error diagnostics with scrubbed credentials and inject actionable notices into the active session context via `handlers.session_start` and `handlers.telemetry_diagnostic_handler`.
- **Configurable Structural Gating (`block` vs `warn`)**: Governed by `AOPS_TELEMETRY_FAILURE_MODE=block|warn`. Autonomous container dispatch workers (`POLECAT_TASK`, `POLECAT_TARGET_TASK`, or `AOPS_CONTAINER`) default to `block` (structural refusal on unconfigured tracing or tracer crash), guaranteeing full trace auditability for headless workers. Interactive local sessions and CI runners default to `warn` to prevent developer lockout.
- **Report Verification Gate (`required gate`)**: Premise-check verdict recording strictly requires remote span export to Phoenix; any failure to export a span leaves the gate armed to prevent untraced handbacks.
