---
id: brief-satisfiability
title: Brief Satisfiability and Report Demand Boundaries
status: draft
type: spec
tags: [enforcement, brief-authoring, premise-check, direction-intake, verification]
---

# Brief Satisfiability and Report Demand Boundaries

This specification establishes the architectural contracts governing brief authoring, direction intake, and premise-check evaluation across academicOps. It eliminates the systemic failure mode where coordinators demand end-of-pipeline deliverables from early-stage workers (#3262), and where premise-check grades reports against impossible demands and forces unresolvable revision loops (#3263).

## Problem Statement & Observed Pathology

When coordinating work across asynchronous pipelines, briefing agents frequently demand end-state deliverables that the recipient cannot hold when it terminates.

Empirical session traces (documented in GitHub issues #3262 and #3263) demonstrated two interlocking defects:

1. **Unbounded Brief Demands (#3262)**: The front agent rule governing report routes ("Say what its report must contain") lacked reachability constraints. The briefing agent filled this slot with the ultimate outcome desired by the user (demanding a PR link and code landing location) when briefing a fire-and-forget dispatcher whose route terminates upon dispatch. The recipient cannot fulfill this demand by design.
2. **Verification Miss in Premise-Check (#3263)**: When the recipient reported what it executed and noted that downstream artifacts cannot exist yet, `premise-check` lacked a satisfiability evaluation. The checker's `Answered` rule treated the absent downstream deliverable as `unanswered` and forced a `REVISE` verdict, even while the checker's own `Valid` line conceded that the demanded contents could not exist yet. Furthermore, direction intake lacked a gate to refuse impossible brief demands before execution began.

The result was an unresolvable failure cycle: an impossible brief passed outbound without inspection, could not be fulfilled during execution, and failed inbound reporting checks, penalizing the reporter for the author's unfulfillable demand.

## User Stories

### US-1: Reachable Brief Demands (Authoring Boundary)

As an execution coordinator or dispatching agent, I want brief demands and acceptance criteria to require only what the recipient can hold at the point it stops, so that workers are never assigned impossible deliverables.

- **AC-1.1**: Given a user request for a multi-stage change, when a coordinator or supervisor constructs a brief or task for an agent or worker, then the brief's report demands and acceptance criteria state only observable outcomes and artifacts that the recipient itself produces before terminating.
- **AC-1.2**: Given a fire-and-forget dispatcher, planning agent, or early-stage design worker, when a brief is issued, then the brief never demands subsequent pipeline deliverables (such as pull request URLs from downstream workers, merged code branches, or decisions delegated to future stages).

### US-2: Direction Intake Satisfiability Verification (Intake Boundary)

As a delegated worker or subagent receiving an incoming direction, I want to verify that all brief demands are satisfiable at my execution boundary before accepting work, so that impossible demands are caught and returned immediately.

- **AC-2.1**: Given an incoming direction or brief, when the receiving agent verifies instructions before logging deliverables, then the agent evaluates whether all demanded deliverables can be produced by its own role and route.
- **AC-2.2**: Given an incoming brief demanding artifacts or decisions belonging to subsequent pipeline stages, when the receiving agent conducts intake evaluation, then the agent refuses the direction with `REVISE` citing unfulfillable brief demands before starting work.

### US-3: Premise-Check Evaluation of Unfulfillable Asks (Checking Boundary)

As a report checker evaluating an argument under `premise-check`, I want the `Answered` test to evaluate whether brief demands were satisfiable by construction, so that a reporter is never failed or looped for an ask it could not fulfill.

- **AC-3.1**: Given an argument reporting on a brief whose demands were unfulfillable by construction at the recipient's stopping point, when the report conclusion establishes why the demanded artifact cannot exist at this stage, then the `Answered` test treats that conclusion as answering the ask ID.
- **AC-3.2**: Given an argument where all inference steps hold and unfulfillable demands are demonstrated unreachable, when the checker records the verdict, then the checker does not record `Answered: <ask_id> unanswered` or return `REVISE` / `FAIL` for the unfulfillable ask.

## Instruction Surfaces and One-Step Moves

Prescriptions and checks for brief demands span authoring, intake, and review surfaces across the framework. Each receives a calibrated one-step change:

| Surface | Location | Current State & Failure Mode | One-Step Move | Category & Severity |
| - | - | - | - | - |
| **Front Agent Authoring** | `plugins/ida/agents/ida.md` | `Report route` directs stating what reports must contain with no reachability limit. Agent fills slot with end-state pipeline deliverables. | Update `Report route` and `Relayed directions`: Mandate that report demands ask only for what the recipient can hold at the point it stops; never demand downstream pipeline outcomes, PR links from subsequent workers, or future decisions. | `instructions`, `imperative` |
| **Dispatcher & Supervisor Briefing** | `plugins/ida/agents/sara.md`, `plugins/ida/agents/james.md` | Persona delegation rules prohibit line-pinned prescriptions but do not restrict brief demands to recipient stopping state. | Update delegation instructions: Brief demands to workers and reification must specify only what the recipient holds upon completion. | `instructions`, `imperative` |
| **Work-Unit Contract** | `specs/enforcement/task-contract.md` | Governs task contract invariants; lacks explicit brief and stage satisfiability boundaries. | Add Brief and Stage Satisfiability Invariant: Task criteria and brief demands must be bounded strictly to artifacts produced by the assigned worker before release. | `spec`, `imperative` |
| **Direction Intake Verification** | `plugins/ida/skills/premise-check/SKILL.md` (§ Directions) | Checks derivation from `## Ask` and method prescriptions; does not verify satisfiability at recipient stopping point. | Update Directions intake procedure: Add mandatory satisfiability verification; refuse (`REVISE`) directions demanding deliverables belonging to subsequent pipeline stages before logging deliverables. | `instructions`, `required gate` |
| **Report Argument Evaluation** | `plugins/ida/skills/premise-check/SKILL.md` (§ Reports) | `Answered` test fails reports if substantive artifact is missing, even when proven unfulfillable by construction, forcing false `REVISE`. | Update `Answered` test: An ask whose demand was unfulfillable by construction at the reporter's stopping point is satisfied when the conclusion establishes unreachability; checkers must not mark it `unanswered` or issue `REVISE` / `FAIL`. | `instructions`, `required gate` |
| **Checker Reason Specification** | `plugins/ida/skills/premise-check/references/checker-reason.md` | `Answered` row assumes either valid line link (`← (n)`) or `unanswered`. | Clarify `Answered` documentation: A conclusion line `(n)` demonstrating why an unfulfillable brief demand is unreachable satisfies the ask and links under `Answered: <ask_id> ← (n)`. | `instructions`, `advisory` |
| **Evidence Contract Specification** | `specs/enforcement/evidence-contract.md` | Lacks explicit rules governing brief satisfiability and unfulfillable brief demand handling. | Add Brief Satisfiability and Reachable Proof sections aligning authoring and checking standards with the evidence contract. | `spec`, `imperative` |

## Enforcement-Map Extracts

The following rows are added to `specs/ENFORCEMENT-MAP.md`:

```markdown
| Brief demand reachability invariant: brief demands and acceptance criteria ask only for what the recipient can hold at the point it stops; downstream pipeline outcomes and later worker decisions excluded | `ida.md`, `sara.md`, `james.md`, `specs/enforcement/task-contract.md` | Brief authors (Ida, Sara, James) | Imperative | `plugins/ida/agents/ida.md:49`, `plugins/ida/agents/sara.md:43`, `plugins/ida/agents/james.md:15`: A brief's report demand must ask only for what the recipient itself can hold at the point it stops; never demand downstream pipeline outcomes (PR links from subsequent workers, merge states, or later decisions). Observation: Eliminates impossible report demands on dispatchers and early-stage workers (#3262). |
| Direction satisfiability intake verification: receiving agent verifies demanded deliverables are holdable upon completion, refusing directions demanding downstream pipeline outcomes | `premise-check` skill (§ Directions) | All receiving agents | Required gate | `plugins/ida/skills/premise-check/SKILL.md:75-82`: When receiving a direction, verify satisfiability before logging deliverables; refuse (`REVISE`) directions demanding deliverables of subsequent pipeline stages. Observation: Prevents unfulfillable brief demands passing into execution (#3263). |
| Unfulfillable brief demand satisfaction in premise-check: conclusion establishing unreachability by construction satisfies the ask; checkers must not record unanswered or issue REVISE | `premise-check` skill (§ Reports), `specs/enforcement/evidence-contract.md` | Checkers (Ida, Sara) | Required gate | `plugins/ida/skills/premise-check/SKILL.md:85-93`: An ask whose demand was unfulfillable by construction at the recipient's stopping point is satisfied when the conclusion establishes unreachability; checkers must link the conclusion and not mark it `unanswered` or issue REVISE/FAIL. Observation: Eliminates false REVISE loops on valid dispatch handbacks (#3263). |
```

## Enforcement Pyramid & Proportionality Analysis

Per `specs/enforcement/enforcement.md`, changes shaping agent behavior must be evaluated across the enforcement pyramid from least to most invasive:

1. **`doctrine only`**: Evaluated and rejected. Core principles (e.g. `Proportion`, `Do One Thing`) already exist, but without explicit reachability and satisfiability instructions, coordinators defaulted to demanding end-state pipeline deliverables.
2. **`instructions` (`imperative`)**: **Selected as the primary mechanism for authoring and intake.** Updating persona briefing rules and skill intake checklists directly prevents impossible demands at the point of origin and intake without mechanical overhead.
3. **`JIT injection`**: Evaluated and deferred. `honesty.md` and `hearsay.md` already remind agents of report formats and hearsay boundaries; adding runtime injection for brief reachability would add unnecessary token cost when clear imperative instructions suffice.
4. **`structural`**: Evaluated and rejected. Deterministic regex or AST checkers parsing brief bodies for terms like "PR link" would violate `judgment-non-delegable`, breaking legitimate uses (e.g. tasks whose explicit deliverable is opening a PR).
5. **`process` (`required gate`)**: **Selected for premise-check evaluation.** `premise-check` is the existing process gate. Refining the semantic definition of the `Answered` test ensures the gate recognizes unfulfillability proofs without requiring changes to mechanical recorder code.
6. **`post-hoc` (`observability`)**: Retained. Phoenix span traces record brief payloads and premise-check verdict attributes, enabling verification of compliance.

## Outcome-Level Build Criteria for Implementation

The implementation task (Stage 2: Build) must satisfy the following verifiable criteria:

1. **Brief Authoring Reachability**: Coordinator and supervisor delegation instructions in `ida.md`, `sara.md`, and `james.md` explicitly restrict report demands to deliverables holdable by the recipient at its stopping point, forbidding downstream pipeline outcomes.
2. **Direction Intake Satisfiability Check**: The direction-checking procedure in `premise-check/SKILL.md` mandates that receiving agents verify the satisfiability of demanded deliverables before logging deliverables, requiring `REVISE` on unfulfillable demands.
3. **Unfulfillable Ask Resolution in Premise-Check**: The `Answered` evaluation table in `premise-check/SKILL.md` and reference documentation in `checker-reason.md` specify that a report conclusion establishing the unreachability of an unfulfillable demand satisfies that ask ID, forbidding checkers from recording `unanswered` or returning `REVISE`/`FAIL` when unreachability is validly established.
4. **Task and Evidence Contract Synchronization**: `specs/enforcement/task-contract.md` and `specs/enforcement/evidence-contract.md` incorporate the brief satisfiability invariant and unfulfillable ask satisfaction rules.
5. **Enforcement Register Alignment**: `specs/ENFORCEMENT-MAP.md` is updated with the three corresponding enforcement rows.
6. **Zero Code Regression**: All existing unit tests and mechanical premise-check recorder checks continue to pass cleanly.

## Baseline-vs-Changed Verification Protocol

### 1. Specimen Scenario (Derived from Issues #3262 & #3263)

A coordinator issues a brief to a fire-and-forget dispatcher (`sara`):

> _"Dispatch the framework change tasks for issue #3262. Your report must give the PR link and say where the rules now live."_

### 2. Baseline Run (Pre-Change Behavior)

- **Outbound brief**: Coordinator writes the brief demanding PR links and rule locations from the dispatcher.
- **Intake**: Dispatcher accepts the brief without assessing reachability.
- **Execution**: Dispatcher dispatches tasks and reports that no PR link exists yet.
- **Inbound check**: Checker records `Valid: (n) holds`, but marks `Answered: c1 unanswered` and issues `REVISE`, triggering an impossible retry loop.

### 3. Changed Run (Post-Change Behavior)

- **Outbound brief**: Coordinator instructions restrict brief demands to dispatch confirmation (e.g. _"Dispatch the framework change tasks; report the dispatched task IDs and statuses"_).
- **Intake guard (Defense-in-Depth)**: If an unconstrained brief arrives demanding a PR link, the dispatcher's intake check catches the unfulfillable demand and immediately returns `REVISE` before execution.
- **Inbound check (Fail-Safe)**: If an unfulfillable demand reaches execution and the dispatcher's conclusion proves why the PR link cannot exist at the dispatch stage, `premise-check` evaluates the unreachability conclusion under `Answered: c1 ← (n)` and records `PASS` rather than `REVISE`.

## Open Questions

None. The architectural boundaries, entry-point interventions, and verification criteria are fully resolved.
