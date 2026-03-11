---
name: qa-handoff-chain
title: QA Handoff Chain
description: Orchestration reference for the three-phase QA workflow — evaluate, decompose, implement.
triggers: [QA chain, QA handoff, QA workflow chain, QA phases]
type: chain
phases: [evaluate-dashboard, decompose-qa-report, implement]
---

# QA Handoff Chain: Evaluate → Decompose → Implement

A three-phase workflow where each phase runs in a **separate session** with an explicit STOP boundary. This prevents the well-documented failure mode where QA agents attempt to both evaluate and fix, resulting in technical rearrangements that miss the UX intent.

## Origin

Issues #729, #731, #732 documented a pattern where QA agents would:

1. Identify a UX problem (correct)
2. Immediately decompose it as a technical task (loses UX intent)
3. Implement the technical fix (wrong solution to the right problem)

The fix: force a handoff between evaluation and decomposition so that task design is done with UX empathy, not engineering reflexes.

## The Three Phases

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Phase 1: Evaluate  │────▶│ Phase 2: Decompose  │────▶│ Phase 3: Implement  │
│                     │     │                     │     │                     │
│  - Run visual QA    │     │  - Read QA report   │     │  - Pick up tasks    │
│  - Check specs      │     │  - Design UX AC     │     │  - Implement fixes  │
│  - Write report     │     │  - Create tasks     │     │  - Verify against   │
│  - STOP             │     │  - STOP             │     │    UX acceptance    │
│                     │     │                     │     │    criteria         │
│  Output:            │     │  Output:            │     │                     │
│  qa/results file    │     │  Tasks in queue     │     │  Output:            │
│                     │     │  decomposition log  │     │  Committed code     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Phase 1: Evaluate Dashboard

**Workflow**: `evaluate-dashboard`
**Skill mode**: Qualitative Assessment or Acceptance Testing
**Agent**: QA agent with browser tools
**Input**: Live dashboard + specs
**Output**: `qa/dashboard-qa-results-{YYYY-MM-DD}.md`

The evaluator inhabits the user persona, walks the scenarios, and documents deviations between spec and implementation. The report uses narrative prose, not pass/fail checklists.

**Boundary**: Produces a report file. Does NOT create tasks or suggest fixes.

## Phase 2: Decompose QA Report

**Workflow**: `decompose-qa-report`
**Skill mode**: QA Planning
**Agent**: Any agent with PKB access
**Input**: QA results file from Phase 1 + specs
**Output**: Tasks with UX acceptance criteria + `qa/dashboard-qa-decomposition-{YYYY-MM-DD}.md`

The decomposer reads the QA report and designs UX-centered acceptance criteria for each finding. Acceptance criteria describe what the user should experience, not what the code should do.

**Boundary**: Creates tasks and a decomposition log. Does NOT implement fixes.

## Phase 3: Implement

**Workflow**: Standard task execution (no special workflow needed)
**Agent**: Implementation agent
**Input**: Tasks from Phase 2 (with UX acceptance criteria in the task body)
**Output**: Code changes committed and verified

Implementation agents pick up tasks from the queue. The UX acceptance criteria from Phase 2 guide what "done" looks like. After implementation, the task can be re-evaluated through Phase 1 to verify.

## Invocation

### Full chain (human-orchestrated)

```
# Session 1: Evaluate
"Evaluate the overwhelm dashboard"
→ Triggers evaluate-dashboard workflow
→ Agent writes report, stops

# Session 2: Decompose
"Decompose the QA report at qa/dashboard-qa-results-2026-03-04.md"
→ Triggers decompose-qa-report workflow
→ Agent creates tasks, stops

# Session 3+: Implement
"Pull next task"
→ Agent picks up tasks created in session 2
→ Normal task execution
```

### Automated (future)

The chain could be automated via polecat swarm orchestration where each phase spawns the next. However, the human review point between Phase 1 and Phase 2 is valuable — the human can triage which findings warrant decomposition.

## Key Principles

1. **Each phase = one session.** No phase crosses a session boundary with the next.
2. **Reports are artifacts.** Each phase produces a file that the next phase reads.
3. **UX acceptance criteria, not technical specs.** Phase 2 writes criteria from the user's perspective.
4. **Human triage is welcome.** The human can review the Phase 1 report before triggering Phase 2, filtering out findings that don't warrant action.
5. **The loop closes.** After Phase 3, re-running Phase 1 verifies that fixes actually improved the UX.
