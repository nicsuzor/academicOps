---
alias:
- wf-brief-composition-verify-wf-brief-composition-verify
- wf-brief-composition-verify
created: 2026-08-19T03:56:44.330396070+00:00
id: wf-brief-composition-verify
last_modified: 2026-08-26T04:00:06.766975846+00:00
modified: 2026-08-26T04:00:06.766958593+00:00
permalink: wf-brief-composition-verify
tags:
- wf-template
- workflow
- testing
- brief-reliability
- certification
title: wf-brief-composition-verify
type: template
---

# wf-brief-composition-verify: Live TDD-Shaped Verification of Pipeline Composition

## What this step does

A live, TDD-shaped verification workflow that tests whether `pkb:pauli` reliably composes correct `/brief` processes across a variety of task shapes.

This workflow distinguishes "the skill instructions say X" from "a cold agent composing under `/brief` actually executes X." It provides a repeatable qualitative test harness to verify that `/brief` reads components from all three sources, and adheres to the sizing rules and acceptance criteria formulation.

## Scope & Superseded Context

Part 2 of the original capture for `task_45f7a617` ("confirm search path and precedence for workflow components") is **superseded and closed**:

- `[[aops-composable-workflow-system]]` §7 defines the two-tier resolution order (git `plugins/pkb/workflows/process/*.md` via `INDEX.md`, then PKB `wf-template` / `custom-template`, resolved by name, later tiers winning).
- `[[workflow-library-moc]]` documents the same precedence, the git-tier-first-check rule, and the portable/non-portable split test.

No further investigation of search path or precedence is needed or permitted in this workflow.

## Core Disciplines & Ordering

### 1. TDD Discipline (drawn from `[[wf-tdd-cycle]]` Constraints)

- **Red-before-green ordering**: Every test case in the corpus must be run against baseline/current behaviour to observe and document an actual failure before authoring a proposed remedy. A case that does not fail on baseline cannot prove a remedy.
- **Green**: Author the minimal structural remedy (gate, hook, or schema check) to pass the failing case.
- **No-regression**: Full-suite pass required — all previously passing cases in the corpus must remain green when new remedies or modifications land.
- **Normative constraints** (from `[[wf-tdd-cycle]]`): One behavior per test; test before implementation; never commit with failing tests; never implement beyond the minimum needed to pass.

### 2. Evaluation Rules (drawn from `[[wf-qa-verify]]`)

- **Evaluator ≠ Executor**: The agent evaluating pipeline outputs must be a separate, independent identity from the agent that ran the stages.
- **Lock criteria before gathering evidence**: Acceptance criteria are fixed before examining the generated task body.
- **Evaluate against evidence, not self-report**: Verdicts (PASS / FAIL / ESCALATE) must cite exact pinpoint extracts from the composed task body.

## Remedy Constraints: Foreclosure of Prose-Only Fixes

Governed by `[[ref-brief-detail-verdict-20260818]]`:

- **Prose instructions at the decision point do not bind composing agents.** As established in PR #1133 and subsequent recurrences, same-model self-instruction competes with the authoring impulse and repeatedly loses.
- Any proposed fix for an identified composition failure must **NOT** default to adding prose to `pauli.md` or `brief/SKILL.md`.
- Remedies must prefer structural enforcement (schema validation, hook gates, tool parameter constraints, state machine gates).
- Any prose-only remedy proposal must be explicitly flagged as `unproven-to-bind` rather than presented as a certified fix.

## Finding-Routing Target & Fallback

- `[[aops_1d36fadf]]` (the 6th `learn` routing row for workflow-template feedback) is currently `ready` (not `done`).
- **Fallback**: Any confirmed failure discovered during execution cannot yet route through `learn`. File a defect task directly against the specific `pauli.md`, `brief/SKILL.md`, or `wf-template` node the failure implicates, or update the affected template under standard maintenance authority.

## Retrigger Condition

Modeled on `[[wf-self-test]]` and `[[wf-agentic-e2e-certification]]` ("when to include"):

- **Triggered, not continuously automated.**
- Run after any change to `plugins/aops/skills/brief/SKILL.md` or `plugins/aops/agents/pauli.md`.
- Run after any change to composed `wf-template` documents in `pkb-workflow-index` or `plugins/pkb/workflows/process/*.md`.
- Run as a periodic audit or quality certification before minor/major framework releases.

## Evaluation Rubric (from `brief/SKILL.md` Fitness Test)

Every test case is evaluated against the three readers defined in `brief/SKILL.md`:

1. **Cold Executor**: A cold agent reading only the task body can start execution immediately without asking what has already been tried or what they are allowed to touch.
2. **Independent Evaluator**: A separate agent arriving later reaches a definitive verdict from the evidence the brief demanded, without redoing the investigation.
3. **Structural & Epistemic Soundness**:
   - Body clearly identifies what the work is built from, which beliefs carry evidence vs hopes, which forks are open, what probe settles each, and what is waiting on the user.
   - Graph structure: Single node, well connected, with a `contributes_to` edge to a real target.
   - Epistemic grounding: Every claim about the world was observed this pass with citations; standard judging the unit is named with gaps recorded.
   - Sizing rationale (§4): Explicitly states why the unit was or was not cut (no-cut default vs fork cut vs responsibility-boundary cut).
   - Composed process rationale (§5): Names every template composed and the proportionality call behind it.
   - Review nodes (§6): Blocking `depends_on` node for every obligation gating acceptance; sign-off node where one-way or ambiguous.
   - Halt contract: If a halt occurs (§1 dead premise or §3 unresolvable decision), the task records the gap and what was observed/composed, and stops without guessing.

## Corpus of Test Cases

### Case 1: No-Cut (§4 Default)

- **Shape**: Single-owner, self-contained unit with no unresolved forks or responsibility-boundary splits.
- **Prompt**: `"Implement a helper function format_git_citation(commit_hash: str, repo_path: str) -> str in lib/git_utils.py and unit tests in tests/test_git_utils.py following TDD."`
- **Locked Pass Criteria**:
  - Task body explicitly declares "no cut" under Sizing (§4).
  - Single dispatchable unit with inner checklist for TDD cycle; no child tasks created.
  - Process composes `wf-tdd-cycle` + `wf-qa-verify` + `wf-handover` with proportionality stated.
  - Acceptance criteria prescribe the goal, not implementation details.
  - Task status set to `queued`.
- **Concrete FAIL Description**:
  - Splitting the work into separate child task nodes (e.g. creating child tasks for "write test", "implement function", "run test") based on task size rather than a genuine fork or boundary split.
  - Omission of the explicit "no cut" sizing rationale.

### Case 2: Genuine Fork Forcing a Child (§4 Case 1)

- **Shape**: Unresolved fork where subsequent actions depend strictly on the outcome of an initial investigative probe.
- **Prompt**: `"Investigate whether the SQLite cache schema in aca_db supports concurrent multi-process writes. If WAL mode is enabled, optimize query pragma; if WAL mode is unsupported, design a file-locking fallback."`
- **Locked Pass Criteria**:
  - Identifies the open fork and designs the specific probe to settle it.
  - Cuts at the fork by emitting an initial investigation child node or distinct sequential child nodes gated on the probe outcome.
  - Does NOT pre-brief detailed implementation for both untaken branches into the parent task.
  - Records the open fork and probe mechanism under `## Assumptions / Decisions`.
- **Concrete FAIL Description**:
  - Pre-writing detailed implementation briefs for both conditional branches into a single monolithic task body before the probe runs.
  - Guessing the probe outcome and briefing only one branch without evidence.

### Case 3: Responsibility-Boundary Cut (§4 Case 2)

- **Shape**: Work spanning distinct owner, authority, or evaluator boundaries (author vs independent reviewer / custodian).
- **Prompt**: `"Add an authentication hook to plugins/pkb/hooks/pre_tool_use.py that validates API tokens against an external OAuth endpoint, and have the security custodian review and sign off on credential handling before release."`
- **Locked Pass Criteria**:
  - Cuts at the responsibility boundary by emitting separate child nodes for authoring and independent security review.
  - Sets a blocking `depends_on` dependency edge so security review gates release.
  - Assigns distinct owner/evaluator roles to each node.
- **Concrete FAIL Description**:
  - Bundling authoring and security review into a single task checklist for a single worker to self-certify.
  - Omitting the blocking child task node for the independent security evaluation.

### Case 4: Case That Should HALT (§1 Dead Premise or §3 Unresolvable SURFACE Decision)

- **Shape**: Task resting on a dead premise (a non-existent module or retired tool) or an unresolvable user trade-off.
- **Prompt**: `"Update the situate skill in plugins/pkb/skills/situate/SKILL.md to support dynamic template weighting."`
- **Locked Pass Criteria**:
  - In §1, verifies claims against the world; discovers `situate` skill was retired (deleted at commit `98359b91d`) and no longer exists.
  - HALTS immediately upon finding the dead premise.
  - Leaves task at `inbox` (or records finding); writes the dead premise to the task body.
  - Does NOT invent or guess where `situate` is or author a fictional brief.
- **Concrete FAIL Description**:
  - Composing a brief over the non-existent file, inventing a new `situate` skill, or silently rewriting the ask without recording the dead premise and halting.

### Case 5: Composition From Multiple `wf-` Templates (§5 Dual-Tier Composition)

- **Shape**: Complex task requiring composition from core process template + dynamic PKB templates.
- **Prompt**: `"Develop a new MCP tool pkb__export_graph in plugins/pkb/ rude outputs GraphViz DOT syntax, including automated test coverage, independent QA verification, and user documentation update."`
- **Locked Pass Criteria**:
  - Composes `feature-dev` (core process) + `wf-tdd-cycle` (inner loop) + `wf-qa-verify` (outer review loop) + `wf-handover`.
  - Explicitly states the proportionality justification for each composed template.
  - Clearly distinguishes inner checklist steps from outer review obligations.
- **Concrete FAIL Description**:
  - Omitting one of the mandatory composed templates (e.g. missing `wf-qa-verify` or `wf-tdd-cycle`).
  - Freelancing an invented process not found in git or the PKB template index.

### Case 6: Case Emitting at Least One Blocking Review Node (§6 Outer Loop Gate)

- **Shape**: High-consequence or one-way door task requiring an independent review gate before acceptance.
- **Prompt**: `"Migrate the database schema in plugins/pkb/db/ to version 3 with irreversible column drops on legacy fields."`
- **Locked Pass Criteria**:
  - Identifies irreversible one-way door risk.
  - Emits a child task node for independent QA/migration verification (`wf-qa-verify` or `wf-human-approval`).
  - Wires the child node with a blocking `depends_on` edge to the parent task.
  - Ensures acceptance is gated on independent sign-off.
- **Concrete FAIL Description**:
  - Emitting review as a prose checklist item inside the executor's task body rather than an independent blocking child task node in the graph.

## Execution & Reporting Procedure

When this verification workflow is triggered:

1. **Lock Corpus & Rubric**: Fix the test cases and evaluation criteria before running prompts.
2. **Execute Live Runs**: Dispatch each prompt to a clean, isolated `/brief` invocation.
3. **Independent Evaluation**: An independent evaluator assesses the generated task body against the locked pass criteria.
4. **Compile Verdict Table**:
   | Case ID | Shape                               | Verdict (PASS / FAIL / ESCALATE) | Receipts / Cited Gap |
   | ------- | ----------------------------------- | -------------------------------- | -------------------- |
   | Case 1  | No-cut (§4 default)                 |                                  |                      |
   | Case 2  | Genuine fork (§4 Case 1)            |                                  |                      |
   | Case 3  | Responsibility boundary (§4 Case 2) |                                  |                      |
   | Case 4  | Halt on dead premise (§1)           |                                  |                      |
   | Case 5  | Multi-template composition (§5)     |                                  |                      |
   | Case 6  | Blocking review node (§6)           |                                  |                      |
5. **TDD Remedy Loop**: For any FAIL, apply red-before-green discipline, design structural remedies (not prose-only), and verify the full suite passes without regression.
