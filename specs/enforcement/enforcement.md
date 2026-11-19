---
id: enforcement_architecture
title: Enforcement Architecture
type: spec
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

The architectural specification detailing the theoretical foundation, mechanism categories, proportional intervention, and operational governance behind enforcement in academicOps.

- **Stated Purpose:** Defines the theoretical foundation, mechanism categories, and proportionality model governing how the framework restrains, steers, and verifies agent behavior without programmatic micro-management.
- **Primary Audience:** Framework architects, system developers, and compliance auditors designing, modifying, or reviewing enforcement mechanisms and policies.
- **Current Truth / SSoT:** The empirical register of active rules, mechanisms, severity levels, and pinpoints is [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md), governed by [`specs/enforcement/enforcement-map.md`](enforcement-map.md). When editing `specs/ENFORCEMENT-MAP.md`, every row must **only** reference a specific rule derived from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) and applicable to agents working in any third-party project; workflows are not rules and do not enforce rules, and creating or modifying workflows must never produce token enforcement map rows (as the only applicable rule is "agents must follow workflows given to them" and nothing more than that). Nothing here restates that live table.

## Governing principle -- agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process substance**, reserving mechanical code strictly for procedural friction and structural prevention:

- **Procedural friction exception (The Evidence Contract gate):**
  - **Hearsay gate (`hearsay_gate.py`, with `premise_check_gate.py` compatibility):** Triggers on `UserPromptSubmit` (canonical incoming agent envelopes: cross-session messages, teammate messages, task notifications, subagent handbacks), `SubagentStop` (subagent return events), and `PostToolUse` (foreground subagent dispatch returns: `Agent`, `invoke_subagent`, `Task`). Holds dispatch, messaging, and channel reply tools and blocks `Stop` while an arrived report or relayed direction awaits a recorded verdict.
  - **Separated JIT reminders:** Report-writing reminder (`honesty.md` on `SubagentStart` in Claude Code and first `PreInvocation` in agy), one-time `PreToolUse` pre-handback check on subagent `send_message` in agy, and report-receiving reminder (`hearsay.md` on `UserPromptSubmit` and once per resolved batch on `PostToolBatch`).
  - **Verdict shape recorder (`premise_check_verdict.py`):** Verifies the checker's seven-key reason shape and structural consistency against the judged Argdown block (`evidence-contract-enforcement.md`), refusing invalid `PASS`, `REVISE`, or `FAIL` records. Whether a rule yields its claim, whether a named rival is nearest, assumption completeness, sufficiency against stakes, and relay entailment stay wholly with the checking agent.
  - **Qualitative basis evaluation:** Premise basis checking operates at Level 2 (Review Lens and Checker Evaluation) and Level 1 (Instructions); authors state natural-language claims with inline sources and checkers judge evidence sufficiency qualitatively under `Supported:` rather than via Level 3 mechanical basis regex or rank arithmetic (`handback-format-design.md`).
- **Structural prevention:** Outside the procedural-friction gate above, the only mechanical enforcement is prevention by construction -- credential and workspace isolation, delivery guards (such as `.github/workflows/auto-retarget-pr.yml` retargeting stray PRs from distribution branches to `dev` and repository rulesets blocking direct pushes and non-release PR merges to `main`), and deployment model pins. Never reactive content-sniffing or deterministic pass/fail on work substance.
- **Delivery channels only:** Hooks, server contracts, and configurations remind, route, and surface state; every substantive judgment is an agent's judgment held to world-leading standards.

## The framework-workflow enforcement line

Enforcement in academicOps is strictly defined as **framework-level process rules** (compliance with universal operating processes), never **workflow-substance rules** (which govern domain substance or client repository work).

- **Framework-level process rules:** Universal behavioral and process invariants derived from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) governing how agents operate across any third-party project, regardless of repository or domain (universal axioms, task lifecycle contracts, authority boundaries, data boundaries, headless worker invariants, and independent review gates).
- **Workflow-substance rules:** Domain-specific instructions, procedures, business logic, heuristics, or formats governing client repository work or specific routines (e.g., correspondence watermarks, Telegram layouts, dbt transformations, literature search strategies).
- **Core doctrine:** Workflows are not rules and do not enforce rules. Workflow substance lives strictly inside workflows (`wf-*.md` or `SKILL.md`), never as framework-level enforcement rules, never in `specs/enforcement/`, and never on [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).
- **The only framework rule for workflows:** Agents must follow workflows given to them, and nothing more than that. When an agent misses a workflow step, the root cause is workflow non-compliance or unclear workflow wording -- never a missing framework rule, spec, gate, or enforcement-map row.

### The operational test for rule classification

When authoring, evaluating, or reviewing any proposed or existing rule, specification, hook, or enforcement-map row, apply this three-step test:

1. **Axiom-Derivation and Third-Party Project Applicability Test:** Does the requirement derive from our axioms ([`plugins/rbg/skills/axioms/`](../../plugins/rbg/skills/axioms/)) and apply universally to agents working in _any_ third-party project across all client repositories, domains, and tasks?
   - _If YES:_ It is a candidate **framework-process rule** eligible for `specs/ENFORCEMENT-MAP.md`.
   - _If NO_ (specific only to `academicOps` project-local rules or to domain workflows such as email sweeps, Telegram UI, dbt, or daily notes): It must NOT appear on `specs/ENFORCEMENT-MAP.md`.
2. **Substance vs. Process Test:** Does the requirement prescribe domain content or workflow steps, OR how axiom-derived operating processes (authority, evidence, truth maintenance, lifecycle) are upheld across any third-party project? Domain substance lives solely inside its workflow (`wf-*.md`) or skill (`SKILL.md`).
3. **General Compliance Test:** Does an observed failure stem from an absent general axiom-derived framework rule, or from failing to follow the applicable workflow? Improve workflow clarity or enforce existing axiom-derived rules (`do-one-thing`, `cite-sources`) rather than inventing per-workflow rules or map rows.

### Regulatory tools and costs

Enforcement is risk-reduction; compliance is probabilistic, not guaranteed:

- **Tools:** **Instructions** (internalized intent via prompts, agent definitions, skills, and rules), **Friction** (gates slowing agents down at key checkpoints), **Tooling** (making the compliant path mechanically easy), and **Process** (independent review and audit).
- **Costs:** Every added mechanism spends tokens and user attention. Match impact to **risk (`likelihood x severity`)** -- severity moves this lever and no other.

### Protection of user attention as a binding constraint

User attention is the scarce, non-renewable resource under Knightian uncertainty and bounded working memory:

- **Autonomous resolution over interruptive escalation:** Resolve within delegated scope, defer via empirical probes, or batch non-blocking items into scheduled digests; never interrupt interactive channels for routine calibrations or valuation queries.
- **Strict serialization:** Present at most one decision or question per message; never dump lists, aggregated decision cards, or multi-question batches.
- **Progressive disclosure:** Deliver bottom-line actionable takeaways first, reserving deep evidence, logs, and traces for on-demand inspection.

## The enforcement register (schema & inclusion)

The enforcement register ([`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md)) is the canonical state document mapping universal axiom-derived rules applicable in any third-party project to their live enforcement carriers. Schema, inclusion criteria, and two-line `Detail` concision invariants are governed by [`specs/enforcement/enforcement-map.md`](enforcement-map.md).

## Mechanism categories and force gradations

The framework organizes all enforcement into a strict controlled vocabulary:

- **`doctrine only`** -- declared principle or policy with no explicit path to agents.
- **`instructions`** -- guiding text provided to an agent, by force: `suggestion`, `advisory`, `imperative`, `absolute`.
- **`JIT injection`** -- advisory information provided at a targeted point of a workflow.
- **`structural`** -- by scope and force: `scoped` (tool visibility), `permissions` (explicit grant/deny rules), `warning` (advisory notification), `friction` (soft restriction), `block` (hard stop), `protection` (mount permissions, fail-closed configs, native loaders), `isolation` (container/sandbox).
- **`process`** -- by review or gate requirement: `advisory check`, `routing`, `required gate`.
- **`post-hoc`** -- by auditability: `reversability` (version history), `observability` (traces, reasons), `proactive detection`.

### Prompt hydration delivery channel (JIT injection)

Prompt hydration (`search_the_pkb`, [`specs/agents/prompt-hydration.md`](../agents/prompt-hydration.md)) serves as a JIT injection delivery channel for top-level `ida` sessions on real user prompts or incoming `<channel>` messages on `UserPromptSubmit` (`PreInvocation` on agy):

- **Top-level `ida` and real prompt scoping:** Runs exclusively on top-level `ida` sessions for interactive console prompts and `<channel>` envelopes; non-`ida` agents, subagents, automated wakeups (`loop_wakeup`, `schedule_wakeup`, `poll_event`), non-`<channel>` system/peer/task/command/reminder wrappers, and `agy` `SYSTEM_MESSAGE` turns make zero PKB calls.
- **Whole-prompt hydration:** Sends full unwrapped prompt text up to 8 KB (`8192` chars) without truncation.
- **Slash command gating:** Suppresses PKB calls on argument-less slash commands (`/cmd`) and `/pull` / `/ida:pull`; other slash commands with arguments send `<arg>` whole up to 8 KB.
- **Stateless MCP attribution metadata:** Sends top-level `session_id` in `arguments` and `x-session-id` header, plus `prompt_id` synced to the turn hook span.
- **Quiet failure & empty handling:** Emits nothing on empty search results; on server/network failure, emits one concise diagnostic line naming the failure cause without stack dumps.

### Plugin startup delivery channel (JIT injection)

Every plugin runs a `SessionStart` hook injecting a plugin-scoped `CORE.md` (at most 20 lines) into ambient session context without agent-specific or extraneous prose ([`specs/agents/startup-core-routing.md`](../agents/startup-core-routing.md)). In `ida`, `SessionStart` (and initial `PreInvocation` on `agy`) also delivers session metadata alongside concise pointers for `premise-check` and explicit caller `session_id` attribution on instrumented MCP calls without rewriting tool inputs in `PreToolUse`.

## Proportionality and force of intervention

Enforcement is chosen by **proportionality, frequency, scope, and force of intervention**, weighing token and attention cost at each firing frequency against the consequence of a miss.

### Proportional intervention options pass

Any change that shapes agent behavior (hooks, review lenses, branch protection, instructions, project rules, agent personas) must evaluate options against this specification before implementation. Editing workflows (`wf-*.md`, `SKILL.md`, process templates) is not a rule change and owes no rows in `specs/ENFORCEMENT-MAP.md`.

1. **Controlled options order (least to most invasive):**
   - `doctrine only` -> `instructions` (`suggestion` -> `advisory` -> `imperative` -> `absolute`) -> `JIT injection` -> `structural` (`scoped` -> `permissions` -> `warning` -> `friction` -> `block` -> `protection` -> `isolation`) -> `process` (`advisory check` -> `routing` -> `required gate`) -> `post-hoc` (`reversability` -> `observability` -> `proactive detection`).
2. **Default and burden of proof:** Default to instructions. No new hooks without a full spec; no new mechanical enforcement without a full spec and an enforcement escalation history. Confirm existing loaded instructions on the same surface were tried and shown insufficient before adding mechanisms.
3. **Instruction updates tested by use:** Instruction-level edits to `ida` (persona, instruction files, checked/relayed skills) proceed on direction and are evaluated by live use; measurement gates mechanisms, not instructions.
4. **Escalation threshold:** A recurring failure pattern justifies incrementing force or mechanism only after less invasive increments are exhausted, with concise records maintained here rather than bloated in `ENFORCEMENT-MAP.md`.

### Active regulatory records

- **Supervised epic dispatch architecture (`instructions` / `imperative` + `process` / `routing`):** Dispatches repo-scoped epic tasks directly from `/q` to containers running `/supervise` under `james`, moving `/reify` into container supervision onto a single combined task body by default and restricting follow-up task creation strictly to out-of-session boundaries (different repo, different time, or external agent/session).
- **Custodian related-work search and conceptual query distillation (`instructions` / `imperative` + `process` / `routing`):** Routes overlap/related-work lookups to `pauli` across agent definitions, planning skills, and sweep templates using 5-15 word distilled conceptual queries rather than raw prompts, preventing identifier pinning and embedding dilution.
- **Explicit MCP caller-session attribution (`instructions` / `imperative` + `JIT injection`):** Retires `PreToolUse` MCP input rewriting in favor of `SessionStart` instructions and `PKB_SESSION_POINTER` requiring agents to pass explicit top-level `session_id` on instrumented MCP and proxy calls, avoiding cloud connector mutation refusals.
- **Default dialectical review (`process` / `required gate`):** Establishes multi-perspective dialectical review (`wf-dialectical-review` with `default: true`) under `james` as the standard independent review workflow for specifications, plans, documents, and PRs.
- **Plugin-scoped startup `CORE.md` injection (`JIT injection` / `advisory`):** Injects bounded (<= 20 line) per-plugin `CORE.md` orientation at `SessionStart` (`specs/agents/startup-core-routing.md`) so cross-directory sessions retain plugin invariants without bloated prompt prefixes.
- **The Evidence Contract gate (`instructions` / `JIT injection` / `structural` / `process` / `post-hoc`):** Holds inter-agent handbacks until verified by an agent against `premise-check`, enforced via `hearsay_gate.py`, `premise_check_verdict.py`, and Phoenix verdict telemetry (`specs/enforcement/evidence-contract-enforcement.md`).
- **Disabled / staged hooks:** `plugins/rbg/hooks/` evaluation and stop handlers (`evaluate`, `inject_ruleset`, `rule_check`) are temporarily `[DISABLED]` in `plugins/rbg/hooks/handlers.py` while `SessionStart` stays active; `post_tool_degraded_check` in `plugins/ida/hooks/handlers.py` remains `[DISABLED]` pending evidence that instructions fail.

### Bounded helpers and recurring jobs

- **Bounded helpers (`instructions`, `advisory` / `imperative`):** Helpers batch multi-item reads/writes, yield or complete before the 5-minute prompt cache TTL expires, and are assessed for culling at agent-idle hooks and task boundaries (dispatching fresh helpers for unrelated work).
- **Recurring jobs (`instructions` / `imperative` + `structural` / `block`):** Recurring jobs inspect their `since: <cursor>` timestamp at Step 0 (exiting cleanly with zero writes or subagent dispatches on no delta) and enforce single-flight concurrency via an active lock marker with `< 15 min` heartbeat.

## Personalities are not skills

An **agent personality** defines conduct, judgment register, and disposition (who the agent is and what standard it holds). An **agent skill** defines a reusable procedure (how a job gets done).

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; binding a skill to a personality is a documented exception strictly for **earmarking** (judgment register dependency) or **permission control** (keeping reviewer distinct from executor).
- **Single source of truth for tool boundaries:** Agent-specific tool prohibitions live in agent definitions (`pauli.md`, `rbg.md`, `marsha.md`) and build tool permissions (`build/tool_map.toml`), never duplicated across skill procedures.
- **Calibration and review division of duties:**
  - **Review Supervisor (`james`, `wf-dialectical-review.md`, `strategic-review/SKILL.md`):** Calibrates proportionality upfront (`flagship` multi-round for high-stakes architecture/specs/rules vs `mid-tier` single-pass sanity check for routine changes), sets target altitude and genre standard, neutrally briefs all lenses with the verbatim originating ask before diffs, verifies reviewer warrants, preserves per-finding risk-vs-cost proportionality without ever softening any specialist `FAIL`, and verifies committed/pushed `fix(review): ...` self-fixes prior to `PASS`.
  - **Compliance lens (`rbg`, `wf-rbg.md`):** Evaluates static semantic compliance against universal axioms, local/user rules, Gate 0 ask-bounded authority and non-mechanical baseline, least-invasive enforcement, data boundaries/public egress, and conditional document-placement/`/craft`/spec standards (`Needs judgment: no` never bypasses Gate 0 or fail-fast). Confined strictly to static diff/artifact evaluation (never runtime QA, qualitative taste, relay truth/fidelity, or graph strategy).
  - **Strategic direction & congruence lens (`pauli`, `wf-strategic-fit.md`):** Evaluates core premise, strategic direction, parsimony, and PKB graph congruence from an inline graph-only brief without reading repository source code, judging aesthetics, or running tests.
  - **Qualitative quality lens (`marsha`, `verify/SKILL.md`):** Evaluates live rendered outputs against external audience purpose, cognitive clarity, and governing genre standards, including anti-circular spec scrutiny (never accepting degraded outputs merely because internal PR-relaxed criteria pass). Never runs test suites/runtime QA, primary-source truth audits, compliance rulings, or PKB strategy.
  - **Functional QA (`wf-qa.md`):** Verifies runtime correctness, live test execution, red-to-green regressions, and edge-case probes against stated specs/ACs only (never qualitative taste, compliance rulings, or strategic fit).
- **Uncontroversial reviewer self-fixes:** Deterministic repairs (`data-boundaries` scrubbing, dead relative links, typos, formatting) are applied directly, committed (`fix(review): ...`), and pushed so `HEAD` matches inspected state prior to `PASS` (never issuing `REVISE` solely for self-fixed items); non-deterministic trade-offs stay under required changes.
- **Consequence & non-mechanical baseline:** Reviewers judge mechanisms by runtime consequences and test against the non-mechanical baseline first: where an agent workflow or skill meets the request across its class, mechanical scripts/CLIs/engines/deterministic judgment proxies fail `no-over-engineering`, `proportionate`, and `judgment-non-delegable`.

### Published surface and repo visibility review

Compliance review evaluates all published surfaces (diffs, commits, trailers, PR titles/bodies, review replies) against destination visibility under `data-boundaries`. Public repositories exclude personal names, private project/host names, deployment-only agent names, PKB note/task/session IDs, internal trailers, and live telemetry.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail.
3. **Measure before changing a mechanism.** The evidence loop below governs adding or strengthening mechanisms; instruction edits to `ida` proceed on direction and are tested by use.
4. **Show, don't tell.** Require primary evidence wherever compliance is claimed.
5. **Never guess.** With no evidence either way, current placement holds.
6. **Agentic-first over mechanical code.** Smarts belong to agents; executable machinery is reserved for deterministic protocol/isolation boundaries.
7. **Proportion covers both code and prose.** Multi-file bloat, rigid calibration schemes, or unneeded enforcement rows where a concise instruction or workflow edit suffices is a defect.

## Evidence loop -- how the framework learns

Class D feedback separates witness from judge so framework evolution tracks recurring root causes rather than single-incident noise:

1. **Detect & Hand Over (Class D Triggers):** PR sweeps (`wf-pr-sweep`, `wf-pr-attention-sweep`) inspect open PRs AND PRs updated or merged `since: <cursor>` with full `reviews` and comments, while `wf-pr-move-along` flags resolved maintainer `CHANGES_REQUESTED` reviews on agent-reviewed PRs `(repo, pr, review_id)` in handbacks for custodian or coordinator `/q` intake (so fast-merged fixes never escape learning). Duplicates against existing PKB `/learn` tasks and open `/learn` GitHub issues are filtered out.
2. **Diagnose & Classify (`/learn`):** The custodian (`pauli`) diagnoses systemic root causes using Phoenix traces (or `gh` PR diffs/comments solely on non-traced CI surfaces) and classifies every finding into one of two typed remedies:
   - **`bug fix at source`:** A single-incident concrete defect in a tool, workflow, local rule, or instruction -- queued immediately from one report via `/q` at the lowest effective tier (Tiers 1-3) for direct repair.
   - **`recurring local-rule or one-step mechanism proposal`:** Logged and consolidated by shared root cause in `/learn` GitHub issues; proposes a local project rule or single-step escalation up the enforcement pyramid only where repeated instances or structural gaps prove single-incident fixes insufficient.
3. **Surface & Route (`wf-reconcile`):** Truth maintenance (`wf-reconcile`) surfaces completed Class D `/learn` remedy proposals on the graph without re-analyzing raw runs or unilaterally restructuring tasks, linking queued `bug fix at source` tasks or surfacing `recurring local-rule or mechanism proposal` items in `## With you` for explicit user approval.

## PR Risk Taxonomy Enforcement

Pull request risk tier classification and merge authority are evaluated semantically by agentic workflows ([`wf-finish.md`](../../plugins/ida/skills/workflow-library/workflows/wf-finish.md), [`wf-code-task-base.md`](../../plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md), [`wf-qa.md`](../../plugins/ida/skills/workflow-library/workflows/wf-qa.md)) rather than path heuristics ([`judgment-non-delegable`](../../plugins/rbg/skills/axioms/judgment-non-delegable.md)):

| Tier | Category | Scope / Characteristics | Merge Authority | Carrier Mechanism |
| :- | :- | :- | :- | :- |
| **Tier 1** | Verified QA-Merge | Pure documentation, formatting, typing stubs (`.pyi`). | Independent verification passes; merges autonomously only under a standing user ruling naming the repository inside the user's boundary; otherwise awaits explicit user approval under `data-boundaries`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |
| **Tier 2** | Operational & Behavioral Gate | Code, workflows, tools, skills, rules, agent definitions, or tests. | Reviewer sign-off required; worker/reviewer posts receipts inside boundary (or holds for approval externally), marks ready inside boundary, leaves PR open for sign-off, and releases task `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |
| **Tier 3** | Critical Hazard & Public Gate | Host infrastructure, credentials, manuscripts, public releases, or high blast radius. | Exclusive principal review and merge; agents forbidden from merging. Verifies, posts receipts inside boundary, marks ready inside boundary, leaves open, releases `done`. | `wf-finish.md`, `wf-code-task-base.md`, `wf-qa.md` |

### Partitioned PR Readiness and Merge Lifecycle

- **Single-session supervision default (`/supervise`):** Runs design, subagent dialectical review, build, incremental `git push` checkpoints, and PR verification inside one combined repo-scoped task, opening a single `--draft` PR carrying build and any spec changes together (or pushing to the shared epic/`bundle/<slug>` branch when project consolidation rules apply).
- **Constituent and standalone PR readiness gate (`--draft` -> `gh pr ready`):**
  1. Open as `--draft` (`gh pr create --draft`).
  2. Mark ready (`gh pr ready`) only when **all** hold against current remote `HEAD`:
     - Green `HEAD` CI checks (rejecting errored, bypassed, cancelled, or `startup_failure` runs).
     - `0` open `CHANGES_REQUESTED` reviews (inspecting raw reviews, never relying solely on summary `reviewDecision`).
     - `0` uncommitted reviewer edits (`fix(review): ...` committed and pushed so `HEAD` matches inspected diff prior to posting verdicts).
     - `0` deferred DRY, single-source-of-truth, or rule-compliance findings.
     - Label-vs-confirmed-route consistency (coordinator routing cannot hold or override a user-designated route without a verified superseding user reversal).
     - Head-SHA-matched **posted** `## RBG Review: PASS` (or CI `## Enforcer Review`) plus proportionate dialectical review verdicts with distinct lens headers (rejecting stale-SHA passes/approvals and committed verdict files).
- **Consolidated feature-branch (`bundle/<slug>`) PR gate:** Where configured by project rules (e.g. `.agents/rules/bundled-prs.md`), constituent PRs undergo full multi-lens diff review before merging into the shared `bundle/<slug>` branch, and donor PRs close immediately upon consolidation linking to the bundle PR. Pre-approval readiness (`gh pr ready`) requires constituent diff receipts, green `HEAD` CI, and a head-SHA-matched **posted** description-only `## RBG Review: PASS`; post-approval rebase onto base triggers full combined-diff multi-lens review matching the rebased `HEAD` SHA prior to merge.
- **External audience boundary (`data-boundaries`):** Outside the user's own organisations and designated repositories, opening any PR (including `--draft`), posting receipts, or posting review comments requires explicit item-by-item user approval first.
- **No waiting in `review`:** Headless workers release finished work tasks as `done` (never `review`) once the PR/deliverable is recorded; downstream review or `/reconcile` handles progression without human wait states on agent tasks.

### Pre-Approval Readiness and Post-Approval Rebase

Before approval, a pull request requires green `HEAD` checks and head-SHA-matched independent proportionate review with feedback resolved; mergeability against the base branch is not required before approval. Rebase and conflict resolution execute strictly after approval, just before merge (re-verifying `HEAD` CI and post-approval combined-diff review where consolidated).

### Non-PR Task Verification and Lifecycle

For tasks producing non-PR deliverables (empirical analyses, documentation, research, maintenance), selected workflow contracts govern whether an independent verification step runs; no low-risk bypass or hard-coded class branching overrides template selection. Workers release completed non-PR tasks directly as `done` with primary evidence in `## Report`.

### Worker State-Only Invariant & Parent Rollup Lifecycle

Per ADR-0002 ([`specs/decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md`](../decisions/0002-distinguish-pkb-graph-edge-purposes-and-enforce-parsimony.md)):

- **Plain leaf workers (`/pull`):** Mutate strictly their claimed task's own state (ticking met criteria with primary evidence, recording `## Report`, transitioning status). Never reify workflows, create child tasks, inspect/modify other tasks' edges, or mint follow-up tasks.
- **Container coordinators (`/supervise`):** Enrich their claimed repo-scoped epic task via `/reify` onto a single combined task body by default, coordinate subagent fan-out with incremental `git push` checkpoints, and wire follow-up tasks via `/q` strictly at out-of-session boundaries (different repo, different time, or separate external agent/session).
- **Parent rollup (`wf-reconcile`):** When all open children of a composite parent reach `done`, a composite task carrying substantive criteria transitions to `ready` for explicit synthesis and sign-off rather than auto-closing.

### Operational Event Ingestion and Session Waking

Worker container completion emits exit listener events, OpenTelemetry `polecat.container.exit` spans, and `polecat_events` MCP queue entries. The dashboard daemon (`specs/telegram/mini-app-dashboard-integration.md`) consumes `polecat_events` and repository webhooks, waking listening sessions over authenticated HTTP/SSE without UNIX socket pushes or client polling loops.

### Observability and Telemetry Failure Gating

Zero-silent-telemetry enforcement spans client hooks, tracer runtimes, and verdict gates ([`specs/observability/telemetry-failure-surfacing.md`](../observability/telemetry-failure-surfacing.md)):

- **JIT Injection & Structural Warnings (`warning`):** Unconfigured trace endpoints and export errors emit scrubbed stderr diagnostics and inject notices into session context via `handlers.session_start` and `handlers.telemetry_diagnostic_handler`.
- **Configurable Structural Gating (`block` vs `warn`):** `AOPS_TELEMETRY_FAILURE_MODE=block|warn` defaults to `block` inside autonomous worker containers (`POLECAT_TASK`, `POLECAT_TARGET_TASK`, `AOPS_CONTAINER`) and `warn` on interactive sessions and CI runners.
- **Report Verification Gate (`required gate`):** `premise_check_verdict.py` requires remote span export to Phoenix; export failures keep the gate armed.
