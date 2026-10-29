---
id: decision_request_axiom_clarification
title: Decision-Request Axiom Clarification
status: draft
type: spec
tags: [enforcement, axioms, decisions, rules]
---

# Decision-Request Axiom Clarification

This specification governs the clarification of the academicOps universal axiom governing decision requests to the user. It establishes the mandatory standard that every request for the user's decision, of any kind (approving a review, merging a PR, and every other decision included), must provide:

1. Enough information for the user to make the decision;
2. Evidence proportionate to the decision;
3. A reasoned recommendation.

## Originating Ask & Evidence

User direction relayed on 2026-10-30:

> "and that's another axiom clarificatoin: any decision request comes with enough information for the user to make the decision, supported by evidence at the appropriate (proportionate) level, with a reasoned recommendation. ANY decision, including reviews etc."

### Occasion and Observed Defect

On 2026-10-30, the user was asked to approve and merge pull requests with neither a posted review nor evidence of their verification state.

The existing universal axiom `exercise-authority` (`plugins/rbg/skills/axioms/exercise-authority.md`) prohibited agents from asking permission for in-scope work (abdication), but completely omitted the affirmative standards required when an agent _does_ escalate a decision outside delegated authority to the user. Consequently, agents escalated decisions bare--without sufficient decision context, without verifiable state receipts, and without a reasoned recommendation.

Additionally, downstream instructions contained fragmented, partial, and competing rules across plugin files (e.g. `plugins/ida/CORE.md:66-75`, `plugins/ida/agents/ida.md:78`, `plugins/ida/skills/decide/SKILL.md`), which lacked universal binding authority across harnesses and failed to prevent bare decision requests.

## User Stories

### US-1: Universal Standard for User Decision Requests

As the user, I want every decision request from any agent or workflow to arrive with complete decision context, proportionate evidence, and a reasoned recommendation, so that I can make informed decisions efficiently without having to hunt for missing reviews, test results, or rationale.

- **AC-1.1**: Given an agent requesting a decision from the user (including PR approvals, merges, review sign-offs, and design choices), when the request is presented on any channel (console, Telegram, daily note, or PR comment), then the request provides enough self-contained information for the user to make the decision without manual log digging.
- **AC-1.2**: Given an agent requesting a decision from the user, when formulating the request, then the request includes primary evidence proportionate to the risk and consequence of the decision (such as posted review links, CI test status receipts, or diff summaries).
- **AC-1.3**: Given an agent requesting a decision from the user, when formulating the request, then the request provides an explicit, reasoned recommendation stating functional rationale ("Recommend X because Y").

### US-2: Complete Scope Across All Decision Types

As a framework contributor and auditor, I want the rule to bind every category of user decision without exception, so that no workflow or interaction mode can bypass decision presentation requirements.

- **AC-2.1**: Given any decision type--including PR reviews, PR merges, architectural choices, and escalation halts--when an agent interacts with the user, then the same threefold requirement applies unconditionally.
- **AC-2.2**: Given the wording of the clarified axiom, when reviewed against the originating ask, then the wording covers all three requirements across all decision requests and adds no unrequested constraints.

## Design & Placement Analysis

### 1. Axiom Identification & Canonical Home (AC1)

A systematic survey of universal axioms in `plugins/rbg/skills/axioms/` was conducted to determine the canonical home:

- **`exercise-authority` (`plugins/rbg/skills/axioms/exercise-authority.md`):**
  - **Identified as Canonical Home.**
  - `plugins/rbg/skills/axioms/README.md` defines its core principle as: _"Act within delegated scope; escalate outside; do not ask for routine execution."_
  - This axiom specifically governs the division between autonomous in-scope execution and escalating outside to the user for decisions.
  - The existing text addressed only the negative prohibition (*"Do not ask for permission to do your job"*), omitting the operative rules for the other half of its defined scope (*"escalate outside"*). Clarifying this axiom restores completeness to the authority boundary.
- **Evaluation of Other Axiom Candidates:**
  - `closure` (`closure.md`): Governs epistemic closure (*"derive decisions strictly from axioms... halt and seek authorization when no authoritative source covers an action"*). It governs derivation of authority, not the evidentiary structure of decision requests.
  - `costly-ops-approval` (`costly-ops-approval.md`): Restricts operations with unbounded blast radius (bulk writes, recursive deletes). It does not govern routine decisions, PR approvals, or reviews.
  - `delay-decisions` (`delay-decisions.md`): Governs timing (deferring decisions to gather information), not the contents of decision requests.
  - `reasons` (`reasons.md`): Governs chained Toulmin Argdown backing for factual and analytic claims, not interactive decision requests to the user.
  - `proportionate` (`proportionate.md`): Governs mechanism overhead and risk weighting.
- **Conclusion:** `exercise-authority` (`plugins/rbg/skills/axioms/exercise-authority.md`) is the existing universal axiom governing delegated authority versus user decision escalation.

### 2. Proposed Axiom Clarification Wording (AC2)

The proposed amendment to `plugins/rbg/skills/axioms/exercise-authority.md` covers all three requirements, explicitly includes reviews and PR approvals, applies to every decision request, and adds nothing beyond the ask:

```markdown
---
description: Act within delegated scope; escalate outside; do not ask for routine execution.
trigger: always_on
---

## Do not ask for permission to do your job

Exercise judgment decisively within your delegated authority.

- Our processes articulate the complete set of checks and balances.
- You are not authorized to increase friction by creating new safeguards or approval processes that are not explicitly required by your instructions.
- You must complete your task to the best of your ability (_abdication_).
- Every request for the user's decision, of any kind (approving a review, merging a PR, and every other decision included), comes with:
  1. Enough information for the user to make the decision;
  2. Evidence proportionate to the decision;
  3. A reasoned recommendation.
```

### 3. Enforcement-Map Status & One-Step Placement (AC3)

#### Enforcement-Map Extract

Inspection of `specs/ENFORCEMENT-MAP.md` shows the current state:

- **Row 21 (`specs/ENFORCEMENT-MAP.md:21`):**
  ```markdown
  | [Axiom: Exercise Authority](../plugins/rbg/skills/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; do not create un-delegated friction or ask permission. | instructions, process | imperative, routing | plugins/rbg/skills/axioms/exercise-authority.md:9-15: Exercise judgment decisively within delegated authority; do not invent un-delegated safeguards or ask permission to do your job (abdication). plugins/ida/agents/james.md:10-35, plugins/ida/agents/sara.md:14-45, & plugins/ida/skills/pull/SKILL.md:14-39: Workers execute headless within the task contract without pausing for human prompts (specs/enforcement/task-contract.md:17-26). plugins/ida/skills/workflow-library/workflows/wf-finish.md:35-60 & wf-qa.md:25-45: Authorise QA workers to merge verified Tier 1 PRs autonomously without human wait states (specs/enforcement/enforcement.md#pr-risk-taxonomy-enforcement). |
  ```
- **Row 54 (`specs/ENFORCEMENT-MAP.md:54`):**
  ```markdown
  | [Shared Core: Decide or Escalate](../plugins/ida/CORE.md) -- State once when an agent decides itself, defers, or escalates, covering returned work, Sara, and workers; never bring questions settled by axioms/specs. | instructions | imperative | plugins/ida/CORE.md:48-66: State once when an agent decides itself, defers, or escalates across conversations, dispatch, workers, and returned work; require at least a "do nothing" option and no false dichotomies; never bring a question axioms/specs settle, picking the fix covering the most general case. Observation: Decisions within scope are made without asking; escalated decisions include a "do nothing" option. |
  ```

#### Planned Enforcement-Map Update for Stage 2 (Build)

Update Row 21 to record the clarified standard and the regulatory observation:

```markdown
| [Axiom: Exercise Authority](../plugins/rbg/skills/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; every decision request to the user (reviews and PR approvals included) comes with enough information, proportionate evidence, and a reasoned recommendation. | instructions, process | imperative, routing | `plugins/rbg/skills/axioms/exercise-authority.md:9-20`: Exercise judgment decisively within delegated authority; do not invent un-delegated safeguards or ask permission to do your job (`abdication`); every request for the user's decision of any kind comes with enough information, proportionate evidence, and a reasoned recommendation. `plugins/ida/CORE.md:66-75`, `plugins/ida/agents/ida.md:78`, `plugins/ida/skills/decide/SKILL.md:20-33`, `plugins/ida/skills/workflow-library/workflows/wf-daily.md:47`. Observation: Decision requests to the user carry self-contained decision context, proportionate verification receipts, and reasoned recommendations. |
```

#### Enforcement Pyramid & One-Step Placement

Following `specs/enforcement/enforcement.md`:

1. **`doctrine only`**: Evaluated and rejected. High-level principles without explicit binding directives failed to prevent bare decision requests.
2. **`instructions` (`imperative`)**: **Selected mechanism.** Establishing the clarified axiom at Level 2 in `plugins/rbg/skills/axioms/exercise-authority.md` injects the rule into every agent session across all platforms (Claude Code, Antigravity, OpenClaw). Default to instructions: instructions work in the large majority of cases, and the burden of proof is on adding heavier machinery.
3. **`JIT injection`**: Evaluated and deferred. Axioms already inject globally via harness configuration. Dynamic JIT hooks on every prompt would introduce unnecessary prompt overhead.
4. **`structural`**: Evaluated and rejected. Evaluating whether an arbitrary decision request provides "enough information", "proportionate evidence", or a "reasoned recommendation" requires semantic interpretation of complex natural language and artifacts. Deterministic AST/regex linting is prohibited by `judgment-non-delegable`.
5. **`process` (`required gate`)**: Retained as verification backstop through multi-lens PR review (`wf-review`, `strategic-review` with `rbg` and `marsha`).
6. **`post-hoc` (`observability`)**: Retained. Traces and commit history provide full auditability.

The move represents strictly one increment within Level 2 instructions, moving from an incomplete universal formulation and fragmented plugin rules to a unified universal axiom.

### 4. Repository Search: Duplicating & Contradicting Instructions (AC4)

A comprehensive codebase search across `plugins/` identified the following instructions that duplicate, contradict, or partially state the clarified rule, along with their planned amendments for Stage 2 (Build):

#### 1. `plugins/ida/CORE.md:66-75` (`### Presenting Decisions to the User`)

- **Current Text:** Defines presentation rules including "The choice and verifiable facts: State what is being decided with exact citations and pointers..." and "Recommendation from the checked report: The recommendation must come from the checked report argument...".
- **Defect/Duplication:** Duplicates the recommendation and facts requirement, but couples the recommendation narrowly to the checked report and omits the universal scope across all decision types (including PR approvals and merges).
- **Amendment for Stage 2:** Reconcile presentation rules with the clarified axiom so that every decision presented to the user satisfies the threefold standard ((a) enough information, (b) proportionate evidence, (c) reasoned recommendation) while preserving presentation-specific constraints (one decision per message, structured reply options, including "do nothing").

#### 2. `plugins/ida/agents/ida.md:78` (`## Reporting on returned work`)

- **Current Text:** _"A decision message's recommendation comes from the checked report; when the report has none, the recommendation is an offer to have one assessed."_
- **Defect/Duplication:** Restricts the recommendation requirement to "A decision message" on returned work, omitting the universal scope over every decision request (e.g. PR approvals/merges).
- **Amendment for Stage 2:** Amend to state that all decision requests directed to the user must carry enough information, proportionate evidence, and a reasoned recommendation per the clarified axiom.

#### 3. `plugins/ida/skills/decide/SKILL.md:20-33` (`## 1. Read Decisions from Today's Daily Note`)

- **Current Text:** Mandates decision cards with "1. The Choice", "2. The Facts with Pointers", "3. Recommendation and Why", "4. Answer Options".
- **Defect/Duplication:** Uses localized phrasing ("Facts with Pointers") rather than referencing proportionate evidence and enough information to decide.
- **Amendment for Stage 2:** Align card preparation requirements to explicitly map to the clarified axiom: (1) enough information to decide, (2) evidence proportionate to the decision (with pointers), and (3) a reasoned recommendation.

#### 4. `plugins/ida-telegram/skills/telegram/SKILL.md:27-30` (`## Questions`)

- **Current Text:** _"Asynchronous by default: Post questions with structured options, placing the recommended choice first... Fuller background behind Details: Provide deep context, evidence, logs, or detailed tradeoffs in the detail parameter..."_
- **Defect/Duplication:** Divides evidence and recommendations across separate bullet points without explicitly enforcing that questions requiring decisions must provide enough information and proportionate evidence.
- **Amendment for Stage 2:** Reconcile question guidance to reaffirm that decision requests via Telegram must provide enough information, proportionate evidence (on the card or in Details), and a reasoned recommendation.

#### 5. `plugins/ida-telegram/skills/refresh-questions/SKILL.md:33,43` (`## Workflow`)

- **Current Text:** Requires active questions to provide an explicit recommendation and concise context; forbids leaving open decisions without recommendation and context.
- **Defect/Duplication:** Duplicates the axiom's requirement in an isolated Telegram sweep skill.
- **Amendment for Stage 2:** Preserve the operational verification check while aligning terminology with the clarified axiom.

#### 6. `plugins/ida/skills/workflow-library/workflows/wf-daily.md:47` (`## Structure`)

- **Current Text:** `7. ## Open PRs: Clean table of open PRs requiring user action (PR | What it does | Recommendation).`
- **Defect/Duplication:** Contradicts the clarified axiom by failing to require evidence of PR state (such as posted review verdict and CI checks status) in the Open PRs table--the exact failure mode that provoked the user's correction.
- **Amendment for Stage 2:** Amend the `## Open PRs` table schema to `PR | What it does | Evidence / Review State | Recommendation`, ensuring proportionate evidence accompanies every PR decision request.

#### 7. `plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md:26` & `wf-doc-base.md:19`

- **Current Text:** Instructs agents when PRs are mergeable to post a merge recommendation and leave open for reviewer sign-off if Tier 2/3.
- **Defect/Duplication:** Under-specifies the affirmative handoff obligation when requesting user merge/approval, failing to mandate inclusion of the posted review link and CI receipts.
- **Amendment for Stage 2:** Explicitly mandate that when leaving a PR open for user decision, the escalated handback and notification must carry enough information, proportionate evidence (posted review and verification receipts), and a reasoned recommendation.

#### 8. `plugins/ida/skills/workflow-library/workflows/wf-escalated-approval.md:18` (`## Procedure`, Step 2)

- **Current Text:** _"state plainly what decision is being asked for, the evidence supporting it, and what happens on approval."_
- **Defect/Duplication:** Mentions evidence supporting the decision, but omits the explicit requirement for a reasoned recommendation.
- **Amendment for Stage 2:** Update step 2 to mandate that the escalation record states the decision with enough information, proportionate evidence, and a reasoned recommendation per the clarified axiom.

## Outcome-Level Build Criteria for Stage 2 (Build)

Stage 2 (Build) must satisfy the following outcome-level criteria across the repository:

1. **Axiom Amendment:**
   `plugins/rbg/skills/axioms/exercise-authority.md` states the clarified threefold requirement covering every request for the user's decision (reviews and PR approvals included) without adding unrequested constraints.
2. **Instruction Alignment:**
   `plugins/ida/CORE.md`, `plugins/ida/agents/ida.md`, `plugins/ida/skills/decide/SKILL.md`, `plugins/ida/skills/workflow-library/workflows/wf-daily.md`, `wf-code-task-base.md`, `wf-doc-base.md`, and `wf-escalated-approval.md` are amended to align with the clarified axiom and eliminate conflicting or incomplete definitions.
3. **Enforcement-Map Record:**
   `specs/ENFORCEMENT-MAP.md` is updated at the `[Axiom: Exercise Authority]` row with the clarified scope, referencing amended surfaces and recording the regulatory experiment observation.
4. **Validation:**
   Automated test suites and linters pass cleanly with zero regressions.

## Open Questions

None. The axiom identification, wording, placement, and downstream amendments are fully resolved.
