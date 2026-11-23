---
id: brief-satisfiability
title: Brief Satisfiability and Report Demand Boundaries
status: ready
type: spec
decisions: [ADR-0003]
tags: [enforcement, brief-authoring, premise-check, direction-intake, verification]
---

# Brief Satisfiability and Report Demand Boundaries

This specification establishes the architectural contracts governing brief authoring, direction intake, and premise-check evaluation across academicOps. It eliminates the systemic failure mode where coordinators demand end-of-pipeline deliverables from early-stage workers (#3262), and where premise-check grades reports against impossible demands and forces unresolvable revision loops (#3263).

## Problem Statement & Observed Pathology

When coordinating work across asynchronous pipelines, briefing agents frequently demand end-state deliverables that the recipient cannot hold when it terminates.

Empirical session traces (documented in GitHub issues #3262 and #3263) demonstrated two interlocking defects:

1. **Unbounded Brief Demands (#3262)**: The front agent rule governing report routes ("Say what its report must contain") lacked reachability constraints. The briefing agent filled this slot with the ultimate outcome desired by the user (demanding a PR link and code landing location) when briefing a fire-and-forget dispatcher whose route terminates upon dispatch. The recipient cannot fulfill this demand by design.
2. **Verification Miss in Premise-Check (#3263)**: When the recipient reported what it executed and noted that downstream artifacts cannot exist yet, `premise-check` lacked a satisfiability evaluation and treated the absent downstream deliverable as an unanswered ask forcing a `REVISE` verdict, even when the report validly established that the demanded contents could not exist yet. Furthermore, direction intake lacked a check to flag impossible brief demands before execution began.

The result was an unresolvable failure cycle: an impossible brief passed outbound without inspection, could not be fulfilled during execution, and failed inbound reporting checks, penalizing the reporter for the author's unfulfillable demand.

## User Stories

### US-1: Reachable Brief Demands (Authoring Boundary)

As the user, I want coordinator briefs and acceptance criteria to require only what the recipient can hold at the point it stops, so that workers are never assigned impossible deliverables.

- **AC-1.1**: Given a user request for a multi-stage change, when a coordinator or supervisor constructs a brief or task for an agent or worker, then the brief's report demands and acceptance criteria state only observable outcomes and artifacts that the recipient itself produces before terminating.
- **AC-1.2**: Given a fire-and-forget dispatcher, planning agent, or early-stage design worker, when a brief is issued, then the brief never demands subsequent pipeline deliverables (such as pull request URLs from downstream workers, merged code branches, or decisions delegated to future stages).

### US-2: Direction Intake Satisfiability Verification (Intake Boundary)

As the user, I want delegated workers and subagents receiving an incoming direction to verify whether brief demands are satisfiable at their execution boundary on Turn 1, so that impossible demands are flagged to the supervisor immediately without stalling or declining handed work.

- **AC-2.1**: Given an incoming direction or brief, when the receiving agent verifies instructions on Turn 1 before logging deliverables, then the agent evaluates whether all demanded deliverables can be produced by its own role and route.
- **AC-2.2**: Given an incoming brief demanding artifacts or decisions belonging to subsequent pipeline stages (or adding unverified caller method prescriptions), when the receiving agent conducts Turn-1 intake evaluation, then the agent flags the unreachable demand to the supervisor as a clarification in a prose Argdown block without declining the task, and proceeds to execute its assigned role (disarming first via `verdict.py --claim <id> --verdict PASS --no-claim --reason-file <path>` when armed, or skipping `verdict.py` when unarmed; if required inputs are missing so execution cannot begin, the agent asks the supervisor in a prose Argdown block without declining, disarming via `--verdict REVISE --no-claim` as a clarification-hold gate token when armed).

### US-3: Premise-Check Evaluation of Unfulfillable Asks (Checking Boundary)

As the user, I want formal compliance review under `premise-check` to evaluate whether brief demands were satisfiable by construction, so that a reporter is never failed or looped for an ask it could not fulfill.

- **AC-3.1**: Given a report on a brief whose demands were unfulfillable by construction at the recipient's stopping point, when the report's conclusion validly establishes why the demanded artifact cannot exist at this stage, then formal compliance review treats that conclusion as satisfying the ask.
- **AC-3.2**: Given a report where all inferences hold and unfulfillable demands are demonstrated unreachable on the record, when the checker records appealable verdict reasons, then the checker does not treat the ask as unanswered or return `REVISE` / `FAIL` for the unfulfillable demand.

## Instruction Surfaces and Active Controls

Prescriptions and checks for brief demands span authoring, intake, and review surfaces across the framework:

| Surface | Location | Addressed Failure Mode | Active Enforcement Contract | Category & Severity |
| - | - | - | - | - |
| **Front Agent Authoring** | `plugins/ida/agents/ida.md` | Filling report-route slots with end-state pipeline deliverables unreachable by the recipient. | Delegation and scoping rules restrict report demands strictly to what the recipient holds when it stops, prohibiting downstream pipeline outcomes, subsequent-worker PR links, or future decisions. | `instructions`, `imperative` |
| **Dispatcher & Supervisor Briefing** | `plugins/ida/agents/sara.md`, `plugins/ida/agents/james.md` | Briefs demanding post-stop pipeline artifacts outside the worker's boundary. | Delegation rules require briefs to specify only observable outcomes and deliverables holdable by the recipient upon completion. | `instructions`, `imperative` |
| **Work-Unit Contract** | `specs/enforcement/task-contract.md` | Task criteria spanning beyond the assigned worker's release boundary. | Brief and Stage Satisfiability Invariant bounds task criteria and brief demands strictly to artifacts produced by the assigned worker before release. | `spec`, `imperative` |
| **Direction Intake Verification** | `plugins/ida/skills/premise-check/SKILL.md` (§ Checking an Incoming Direction Brief) | Accepting impossible brief demands silently and failing later on handback. | Turn-1 direction intake checks brief satisfiability, flags demands belonging to subsequent pipeline stages (or unverified caller prescriptions) to the supervisor as a clarification in a prose Argdown block without declining, and executes the assigned role (disarming via `verdict.py --verdict PASS --no-claim` first when armed; missing required inputs ask the supervisor in a prose Argdown block without declining, using `--verdict REVISE --no-claim` as a clarification-hold token when armed; unarmed briefs skip `verdict.py`). | `instructions`, `required gate` |
| **Formal Compliance Evaluation** | `plugins/ida/skills/premise-check/SKILL.md` (§ Reviewing a Message) | Grading an unfulfillable demand as an unanswered ask and forcing `REVISE` loops. | Ask-completeness review treats an unfulfillable demand as satisfied when the report validly proves unreachability by construction, forbidding `REVISE` or `FAIL` for that demand. | `instructions`, `required gate` |
| **Evidence Contract Specification** | `specs/enforcement/evidence-contract.md` | Unaligned authoring and review rules for unreachable demands. | Honest Endings and Directions Relayed Intact define brief satisfiability and unreachability proof satisfaction across authoring and formal compliance review. | `spec`, `imperative` |

## Enforcement Register Alignment

Brief demand reachability, Turn-1 direction satisfiability, and unfulfillable-ask satisfaction are enforced under `Axiom: Reasons` in [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md), anchored at `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md`, `plugins/ida/skills/premise-check/SKILL.md`, `specs/enforcement/task-contract.md`, and `specs/enforcement/evidence-contract.md`.

## Enforcement Pyramid & Proportionality Analysis

Per `specs/enforcement/enforcement.md`, changes shaping agent behavior must be evaluated across the enforcement pyramid from least to most invasive:

1. **`doctrine only`**: Evaluated and rejected. Core principles (e.g. `Proportion`, `Do One Thing`) already exist, but without explicit reachability and satisfiability instructions, coordinators defaulted to demanding end-state pipeline deliverables.
2. **`instructions` (`imperative`)**: **Selected as the primary mechanism for authoring and intake.** Updating persona briefing rules and skill intake checklists directly prevents impossible demands at the point of origin and intake without mechanical overhead.
3. **`JIT injection`**: Evaluated and deferred. `honesty.md` and `hearsay.md` already remind agents of report prose and formal compliance boundaries; adding runtime injection for brief reachability would add unnecessary token cost when clear imperative instructions suffice.
4. **`structural`**: Evaluated and rejected. Deterministic regex or AST checkers parsing brief bodies for terms like "PR link" would violate `judgment-non-delegable`, breaking legitimate uses (e.g. tasks whose explicit deliverable is opening a PR).
5. **`process` (`required gate`)**: **Selected for premise-check evaluation.** `premise-check` is the existing formal compliance review process. Refining its ask-completeness criterion ensures evaluators recognize valid unreachability proofs without adding mechanical code.
6. **`post-hoc` (`observability`)**: Retained. Phoenix span traces record brief payloads and `premise_check_verdict` spans with appealable natural-language reasons, enabling verification of compliance.

## Outcome-Level Build Criteria for Implementation

The implementation satisfies the following verifiable criteria:

1. **Brief Authoring Reachability**: Coordinator and supervisor delegation instructions in `ida.md`, `sara.md`, and `james.md` explicitly restrict report demands to deliverables holdable by the recipient at its stopping point, forbidding downstream pipeline outcomes.
2. **Direction Intake Satisfiability Check**: The direction-checking procedure in `premise-check/SKILL.md` mandates that receiving agents verify the satisfiability of demanded deliverables on Turn 1 before logging deliverables, flagging unfulfillable demands to the supervisor as a clarification in a prose Argdown block without declining while executing their role (disarming armed briefs via `verdict.py --verdict PASS --no-claim`, or `--verdict REVISE --no-claim` when holding for missing inputs).
3. **Unfulfillable Ask Resolution in Premise-Check**: The ask-completeness check in `premise-check/SKILL.md` specifies that a report conclusion validly proving the unreachability of an unfulfillable demand satisfies that ask, forbidding checkers from returning `REVISE`/`FAIL` when unreachability is validly established.
4. **Task and Evidence Contract Synchronization**: `specs/enforcement/task-contract.md` and `specs/enforcement/evidence-contract.md` incorporate the brief satisfiability invariant and unfulfillable ask satisfaction rules.
5. **Enforcement Register Alignment**: `specs/ENFORCEMENT-MAP.md` aligns `Axiom: Reasons` to the updated instruction and specification coordinates.
6. **Zero Code Regression**: All unit and integration gate/verdict tests pass cleanly.

## Baseline-vs-Changed Verification Protocol

### 1. Specimen Scenario (Derived from Issues #3262 & #3263)

A coordinator issues a brief to a fire-and-forget dispatcher (`sara`):

> _"Dispatch the framework change tasks for issue #3262. Your report must give the PR link and say where the rules now live."_

### 2. Baseline Run (Pre-Change Behavior)

- **Outbound brief**: Coordinator writes the brief demanding PR links and rule locations from the dispatcher.
- **Intake**: Dispatcher accepts the brief without assessing reachability.
- **Execution**: Dispatcher dispatches tasks and reports that no PR link exists yet.
- **Inbound check**: Checker treats the absent PR link as an unanswered ask and issues `REVISE`, triggering an impossible retry loop.

### 3. Changed Run (Post-Change Behavior)

- **Outbound brief**: Coordinator instructions restrict brief demands to dispatch confirmation (e.g. _"Dispatch the framework change tasks; report the dispatched task IDs and statuses"_).
- **Intake guard (Defense-in-Depth)**: If an unconstrained brief arrives demanding a PR link, the dispatcher's Turn-1 intake check catches the unfulfillable demand, flags it to the supervisor as a clarification in a prose Argdown block without declining the task (disarming via `verdict.py --verdict PASS --no-claim` first if armed), and executes its dispatch role.
- **Inbound check (Fail-Safe)**: If an unfulfillable demand reaches execution and the dispatcher's conclusion validly proves why the PR link cannot exist at the dispatch stage, `premise-check` treats the ask as satisfied on the face of the record and records `PASS` with appealable reasons rather than `REVISE`.

## Open Questions

None. The architectural boundaries, entry-point interventions, and verification criteria are fully resolved.
