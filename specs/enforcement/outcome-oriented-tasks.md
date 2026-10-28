---
title: Outcome-Oriented Task Reification and Full-Context File Inspection
status: draft
type: spec
tags: [enforcement, task-contract, reify, execution, verification]
---

# Outcome-Oriented Task Reification and Full-Context File Inspection

This specification governs the boundaries of task reification, task contract formation, and worker file inspection across academicOps. It eliminates the systemic failure mode where coordinators and planning agents pass narrow `file:line` pinpoints and mechanism prescriptions into task acceptance criteria, driving downstream implementation workers to execute isolated keyhole reads and out-of-context code splices.

## Problem Statement & Observed Pathology

When a coordinator pre-investigates a multi-file change, identifies exact line numbers via file searches, and passes an implementation plan containing `file:line` coordinates into task reification (`/reify`), the reification process transcribes those mechanism prescriptions directly into frozen task acceptance criteria (`AC1`–`ACn`) and `Instructions`.

Downstream implementation workers (optimizing for token efficiency and literal checklist compliance) pass the line coordinates directly to `read_file(StartLine, EndLine)` in narrow 15–75 line windows. The worker never reads the full target files, surrounding module conventions, or existing helper utilities.

In empirical production traces across multi-file changes (documented in issue #3157), this failure mode resulted in:

1. Additive bullet points bolted onto agent personas instead of refactoring existing sections;
2. Duplicated logic clauses inserted at separate line ranges of the same file (e.g. lines 10..30 and lines 105..130);
3. Inline string prompts hardcoded deep within hook handlers because the worker never inspected lines 1..250 where modular message loaders resided;
4. Ad-hoc dialect splits and fallback cascades added to satisfy literal, over-specified acceptance criteria;
5. The collapse of the two-stage lifecycle (Design followed by Build) into a single unreviewed implementation pass.

## User Stories

### US-1: Outcome-Oriented Task Reification

As an execution coordinator or dispatching agent, I want reified tasks to specify observable end-state conditions and verification criteria rather than implementation mechanisms, so that workers solve problems in context rather than executing mechanical line edits.

- **AC-1.1**: Given a user or coordinator brief containing exact file and line coordinates, when `/reify` generates a task, then `Goal`, `Acceptance`, and `Instructions` contain zero line numbers, line ranges, or narrow code slice prescriptions.
- **AC-1.2**: Given an incoming request specifying a desired system change, when acceptance criteria are generated, then each criterion expresses an observable condition (in Given/When/Then or verifiable state format) that an independent reviewer can evaluate.

### US-2: Architectural Staging Preservation

As a framework architect, I want multi-file and architectural changes to maintain separate Design and Build stages, so that structural decisions are verified before code edits occur.

- **AC-2.1**: Given an ask involving multi-file modifications or judgment among alternative implementations, when `/reify` composes the workflow from the code task base, then Stage 1 (Design) is reified as an independent task preceding Stage 2 (Build).
- **AC-2.2**: Given a brief that already includes an implementation proposal, when `/reify` composes the task graph, then it does not collapse Stage 1 (Design) into Stage 2 (Build).

### US-3: Full-Context File Inspection

As a quality reviewer, I want implementation workers to read complete files in context before modifying them, so that code changes conform to existing module conventions and abstractions.

- **AC-3.1**: Given a task targeting repository files, when a worker begins implementation, then the worker reads each target file in full before executing any edits.
- **AC-3.2**: Given a task referencing advisory file or line hints, when a worker executes file reads, then the worker treats line numbers strictly as advisory starting pointers and never restricts file reads to narrow line windows around those pointers without first inspecting the whole file.

## Entry Point Analysis & One-Step Changes

Prescriptions enter reified tasks and drive out-of-context edits across four sequential entry points in the execution lifecycle. Per the enforcement pyramid (`specs/enforcement/enforcement.md`), each entry point receives a calibrated one-step intervention.

| Entry Point | Location | Current Failure Mode | One-Step Move | Enforcement Category & Severity |
| - | - | - | - | - |
| **1. Coordinator Briefing** | `plugins/ida/agents/ida.md`, `sara.md`, `james.md` | Coordinators run preliminary file/grep searches and pass line-pinned implementation plans into `/reify` or worker briefs, pre-empting the design stage. | Update agent persona instructions: Delegation briefs to `/reify` and workers must state the goal, observable outcome, and target artifacts or systems; they must never prescribe line numbers, line ranges, narrow code slices, or implementation mechanisms. | `instructions`, `imperative` |
| **2. Task Reification** | `plugins/ida/skills/reify/SKILL.md`, `plugins/ida/agents/pauli.md`, `specs/agents/reify.md` | `/reify` transcribes line numbers and mechanism prescriptions verbatim into `AC1`–`ACn` and `Instructions`, and collapses Design and Build stages when given an implementation plan. | Update reification instructions: `/reify` must filter incoming mechanism prescriptions and translate them into observable outcome criteria. Line numbers, line ranges, and code snippets are strictly forbidden in `Acceptance` and `Instructions`. When multi-file changes or architectural choices are required, Stage 1 (Design) and Stage 2 (Build) must remain separate tasks. | `instructions`, `imperative` |
| **3. Workflow Base Templates** | `plugins/ida/skills/workflow-library/workflows/wf-code-task-base.md`, `wf-task-base.md` | Base workflows do not explicitly forbid line-pinned acceptance criteria in Stage 2 (Build), nor do they mandate whole-file context reads before editing. | Update workflow templates: Explicitly specify that Stage 2 (Build) acceptance criteria define observable behaviors rather than line edits, and mandate that workers read target files in full to understand architecture and conventions before editing. | `instructions`, `imperative` |
| **4. Worker Execution Contract** | `plugins/ida/skills/pull/SKILL.md`, `specs/enforcement/task-contract.md` | Workers receive tasks and execute `read_file(StartLine, EndLine)` in 15–75 line windows around mentioned line numbers, splicing edits blindly without reading imports or helper functions. | Update worker execution contract: Mandate that workers must read target files in full before making edits. Keyhole line-slice reads (`read_file` with narrow line windows) in isolation without prior whole-file context are strictly prohibited. Advisory line hints are starting pointers only. | `instructions`, `imperative` |

## Enforcement Pyramid & Proportionality Analysis

Per `specs/enforcement/enforcement.md`, any change that shapes agent behavior must run through the enforcement pyramid options from least invasive to most invasive before establishing a mechanism:

1. **`doctrine only`**: Evaluated and rejected. High-level principles (e.g. Proportion, Do One Thing, Single Source of Truth) are already declared, but without explicit operative instructions at the reification and execution boundaries, agents reliably optimized for token brevity by transcribing line numbers and performing keyhole reads.
2. **`instructions` (`imperative`)**: **Selected as the primary mechanism.** Instructions work in the vast majority of cases when placed prominently at the operative decision boundary. Updating the coordinator rules, reification requirements, workflow templates, and worker execution instructions directly addresses the cause at the least cost in system complexity and token overhead.
3. **`JIT injection`**: Evaluated and deferred. Injecting dynamic reminders during tool execution introduces token overhead on every turn. If imperative instructions exhibit residual non-compliance in future evaluations, targeted JIT reminders on `PreToolUse` for `read_file` can be evaluated.
4. **`structural`**: Evaluated and rejected. A mechanical AST or regex check blocking tasks containing line numbers or rejecting `read_file` calls with `StartLine`/`EndLine` would violate the governing principle ("agents all the way down") and `judgment-non-delegable`, breaking legitimate uses (such as reading log slices or stack trace pinpoints).
5. **`process` (`required gate`)**: Retained as the verification backstop. The dialectical review lens (`wf-review`, `/strategic-review` with `rbg`, `pauli`, and `marsha`) inspects PRs and task contracts post-hoc to verify adherence to architectural boundaries and quality standards.
6. **`post-hoc` (`observability`)**: Retained. Telemetry traces in Phoenix record tool call parameters (`read_file` arguments) and task criteria, providing auditability for compliance verification.

## Outcome-Level Build Criteria for Implementation

The implementation task (Stage 2: Build) must satisfy the following verifiable criteria:

1. **Reified Task Contract Hygiene**: Reified tasks generated by `/reify` given briefs that contain file/line pinpoints and mechanism prescriptions produce task bodies where `Goal`, `Acceptance criteria`, and `Instructions` contain zero line numbers, line ranges, or narrow slice prescriptions. All criteria state observable outcome conditions.
2. **Workflow Staging Invariant**: Reification of multi-file or architectural changes under `wf-code-task-base` preserves a distinct Stage 1 (Design) task preceding Stage 2 (Build), even when the incoming brief provides an implementation plan.
3. **Worker Context-Reading Compliance**: Worker instructions in `pull/SKILL.md` and `task-contract.md` mandate whole-file reads before editing. In execution traces of file modifications, target files are read in full prior to edits.
4. **Enforcement Register Sync**: `specs/ENFORCEMENT-MAP.md` is updated with rows for the reification outcome invariant and worker context-read invariant at severity `imperative`.
5. **Verification Suite**: The full test suite and repository linters pass cleanly.

## Baseline-vs-Changed Verification Protocol

The effectiveness of this change is verified through an empirical baseline-vs-changed experiment:

### 1. Specimen Input Brief

A multi-workstream implementation brief containing explicit file and line coordinates (derived from issue #3157):

> _"Implement the fix across four workstreams: Workstream 1: plugins/ida/agents/ida.md:40-47, plugins/ida/agents/sara.md:46-47 (restrict caller delegation briefs...); Workstream 2: plugins/ida/hooks/hearsay_gate.py:918 (inline prompt adjustment)..."_

### 2. Baseline Run (Pre-Change Behavior)

- **Reification output**: `/reify` transcribes line numbers directly into frozen criteria (e.g. `AC1: Update plugins/ida/agents/ida.md lines 40-47...`).
- **Worker tool calls**: Downstream worker executes `read_file(Path='plugins/ida/agents/ida.md', StartLine=35, EndLine=55)`, followed by `edit_file` splicing clauses additively without reading the rest of the file.
- **Worker defect**: Fails to see surrounding section conventions or modular loaders in lines 1..250.

### 3. Changed Run (Post-Change Behavior)

- **Reification output**: `/reify` transforms the brief into outcome-level acceptance criteria (e.g. `AC1: Delegation briefs to /reify and workers state observable goals and omit line-pinned mechanism prescriptions`). Zero line numbers or line ranges appear in `Acceptance` or `Instructions`.
- **Worker tool calls**: Downstream worker executes `read_file(Path='plugins/ida/agents/ida.md')` without line limits, reading all lines. The worker reviews the entire file structure before executing contextual edits.
- **Worker outcome**: Edits conform to existing section architecture and existing helper abstractions.

### 4. Observable Verification Signal

- **Task text evaluation**: Running regex check `grep -E ':\b[0-9]+\b|lines?\s+[0-9]+' <reified-task>` over `Acceptance` and `Instructions` yields zero matches.
- **Telemetry audit**: Phoenix trace spans for the worker session show `read_file` calls on modified files without narrow `StartLine`/`EndLine` parameters on initial inspection.

## Open Questions

None. The design choices, entry point assignments, enforcement pyramid evaluations, and verification protocols are fully resolved.
