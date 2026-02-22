---
title: Workflow Constraints Specification
type: spec
category: architecture
status: draft
created: 2026-01-23
related: [workflow-system-spec, prompt-hydration, enforcement]
---

# Workflow Constraints Specification

## Giving Effect

- [[workflows/constraint-check.md]] - Constraint checking workflow in hydrator
- [[specs/constraint-checking-tests.md]] - Test spec for constraint validation
- [[specs/predicate-registry.md]] - Registry of available predicates
- [[commands/pull.md]] - Dispositor pattern: `/pull` executes enqueued work

## Purpose

This spec defines two architectural changes:

1. **Logical-statement workflow format** - Express workflows as constraints, not procedures
2. **Dispositor pattern** - Main agent enqueues work; `/pull` executes it

## Part 1: Logical-Statement Workflow Format

### Current State (Procedural)

Workflows are procedural instructions:

```markdown
## Steps

1. Capture user story
2. Analyze requirements
3. Write failing tests
4. Implement code
5. Run tests
6. Commit
```

**Problems:**

- Agents skip steps (verification, planning, tests)
- Order is rigid but work is often non-linear
- Hard to compose or check compliance
- Hydrator generates sequential TodoWrite without constraint awareness

### Proposed State (Constraint-Based)

Workflows become constraint specifications. The hydrator generates task sequences that _satisfy_ the constraints; agents cannot generate valid work that violates them.

#### Rule Types

| Type              | Syntax           | Meaning                      | Example                               |
| ----------------- | ---------------- | ---------------------------- | ------------------------------------- |
| **PRECONDITION**  | `BEFORE X: Y`    | Y must be satisfied before X | `BEFORE commit: tests_pass`           |
| **POSTCONDITION** | `AFTER X: Y`     | Y must be satisfied after X  | `AFTER implement: run_tests`          |
| **INVARIANT**     | `ALWAYS: X`      | X must hold throughout       | `ALWAYS: one_task_in_progress`        |
| **PROHIBITION**   | `NEVER: X`       | X must not occur             | `NEVER: commit_failing_tests`         |
| **CONDITIONAL**   | `IF X THEN Y`    | When X is true, Y required   | `IF modifying_python THEN run_pytest` |
| **TRIGGER**       | `ON X: INVOKE Y` | X triggers skill/action Y    | `ON tests_fail: INVOKE halt`          |

#### Constraint Format

```yaml
# workflows/feature-dev.yaml
workflow: feature-dev
description: Test-driven feature development with planning and review

context:
  applies_when:
    - adding new features
    - building significant functionality
  not_when:
    - simple bug fixes
    - documentation-only changes

constraints:
  # Preconditions - what must happen first
  - BEFORE implement: plan_approved
  - BEFORE implement: tests_exist AND tests_fail
  - BEFORE commit: tests_pass
  - BEFORE commit: critic_reviewed

  # Postconditions - what must happen after
  - AFTER implement: run_tests
  - AFTER complete: update_spec

  # Invariants - always true
  - ALWAYS: one_task_in_progress
  - ALWAYS: changes_tracked_in_task

  # Prohibitions - never allowed
  - NEVER: commit_with_failing_tests
  - NEVER: implement_without_plan
  - NEVER: skip_critic_review

  # Conditionals - context-dependent
  - IF modifying_framework THEN use_detailed_critic
  - IF tests_fail THEN halt_and_fix

triggers:
  # Actions that invoke skills
  - ON plan_needed: INVOKE plan-agent
  - ON tests_needed: INVOKE tdd-cycle
  - ON review_needed: INVOKE critic
  - ON tests_fail: INVOKE halt

predicates:
  # Define how predicates are evaluated
  plan_approved:
    check: task.body contains "## Approved Plan"
    or: user said "approved" or "lgtm"

  tests_exist:
    check: grep for "def test_" in relevant test files

  tests_pass:
    check: pytest exit code == 0

  tests_fail:
    check: pytest exit code != 0

  critic_reviewed:
    check: task.body contains "## Critic Review" or critic agent spawned
```

#### Comparison: Procedural vs Constraint

**Procedural (current tdd-cycle.md):**

```markdown
## Core Cycle

1. Red: Write failing test for ONE thing
2. Verify failure: Confirm test fails
3. Green: Minimal implementation to pass
4. Verify pass: Confirm test passes
5. Refactor: Clean up
6. Commit: Cycle complete
7. Repeat: If more acceptance criteria
```

**Constraint (proposed):**

```yaml
workflow: tdd-cycle
description: Red-green-refactor cycle

constraints:
  - BEFORE implement: test_exists AND test_fails
  - BEFORE commit: test_passes
  - AFTER implement: run_test
  - AFTER refactor: tests_still_pass
  - NEVER: implement_before_test
  - NEVER: commit_failing_test

triggers:
  - ON test_fails: PROCEED_TO implement
  - ON test_passes: PROCEED_TO refactor_or_commit
```

**Key difference:** Constraints don't prescribe order. They define what must be true. Agent can work in any order that satisfies constraints.

### Predicate Evaluation

Predicates are evaluated by the hydrator using available context:

| Predicate Type | Evaluation Method                |
| -------------- | -------------------------------- |
| File content   | Grep/Read tool results           |
| Command output | Bash exit codes, stdout          |
| Task state     | MCP task tools                   |
| Session state  | Session state reader             |
| User statement | Pattern match on recent messages |

**Important limitation:** Hydrator performs constraint-_checking_, not constraint-_solving_. It verifies that a proposed action sequence satisfies constraints; it doesn't synthesize sequences from scratch.

### Workflow Composition via Constraint Inheritance

Workflows can inherit constraints from other workflows:

```yaml
workflow: framework-feature
extends: feature-dev

additional_constraints:
  - BEFORE implement: FRAMEWORKS.md reviewed
  - ALWAYS: use_detailed_critic  # override default
  - AFTER complete: update_HEURISTICS if pattern discovered
```

### Migration Path

1. **Phase 1:** Create constraint equivalents for 3 pilot workflows (feature-dev, decompose, tdd-cycle)
2. **Checkpoint:** Manually verify no semantic loss in translation
3. **Phase 2:** Update hydrator to read constraint format
4. **Phase 3:** Convert remaining workflows
5. **Phase 4:** Deprecate procedural format

## Part 2: Dispositor Pattern

### Current State

```
User prompt → Hydrator → Main agent executes immediately
```

Main agent does everything: classifies, plans, executes, commits.

**Problems:**

- No queue visibility (what work is pending?)
- No interruptibility (user can't reprioritize mid-work)
- Complex work blocks simple interactions
- Agent scope creep (does more than asked)

### Proposed State

```
User prompt → Hydrator → Main agent enqueues → /pull executes
```

Main agent becomes "dispositor" - it receives, classifies, and routes work but does not execute it directly.

#### Core Principle

**Separation of concerns:**

- **Dispositor (main agent):** Understand intent, check constraints, create/update tasks, respond to questions
- **Executor (/pull):** Claim task, execute work, verify completion

#### Direct Execution Paths

Not everything goes through the queue. These bypass and execute immediately:

| Path                   | Why Direct                         | Example                |
| ---------------------- | ---------------------------------- | ---------------------- |
| `/command` invocations | User explicitly requests action    | `/commit`, `/help`     |
| Skill invocations      | User explicitly invokes skill      | `/pdf`, `/daily`       |
| Simple questions       | No state changes, immediate answer | "What is X?"           |
| Conversational         | Dialog, not work                   | "Thanks", "Can you..." |
| `/pull` itself         | This IS the execution path         | `/pull`                |

**Detection heuristic for direct execution:**

1. Starts with `/` → direct (command or skill)
2. Hydrator classifies as `simple-question` → direct
3. No file modifications implied → likely direct
4. Everything else → enqueue

#### Enqueue Semantics

"Enqueue" means: create a task via MCP with sufficient context for later execution.

```python
# What main agent does when enqueuing
mcp__pkb__create_task(
    task_title="Implement dark mode toggle",
    type="task",
    project="webapp",
    priority=2,
    body="""
## Context
User requested dark mode toggle in settings page.

## Relevant Files
- src/components/Settings.tsx
- src/styles/theme.ts

## Acceptance Criteria
- Toggle visible in settings
- Theme persists across sessions
- System preference respected by default

## Workflow
feature-dev (constraints apply)
""",
    tags=["feature", "ui"]
)
```

#### Agent Communication

When main agent enqueues instead of executing:

```
User: "Add a dark mode toggle to settings"

Dispositor response:
---
Created task: aops-abc123 "Implement dark mode toggle"
Priority: 2 (normal)
Workflow: feature-dev

Run `/pull` to execute, or continue with other work.
---
```

**Key behaviors:**

- Acknowledges the request was understood
- Shows task was created (with ID for reference)
- Indicates workflow/constraints that will apply
- Prompts user about next step

#### /pull Task Selection

When user runs `/pull`:

1. `list_tasks(status="active")` returns candidate tasks
2. If specific task ID provided: claim that task
3. If no ID: claim highest priority active task
4. Apply workflow constraints during execution

**Multiple tasks ready:** User can specify task ID or `/pull` takes highest priority.

#### "Just Do It" Resistance

What if user tries to bypass the queue?

```
User: "No, just implement it now, don't create a task"
```

**Dispositor response options:**

A. **Comply with acknowledgment** (for simple work):

```
Proceeding directly. Note: work won't be tracked in task system.
[executes]
```

B. **Gentle redirect** (for complex work):

```
This work has dependencies and verification requirements that
the task system helps track. I've created task aops-abc123.
Run `/pull aops-abc123` to execute with proper tracking.
```

C. **Explain trade-offs** (if user insists):

```
Direct execution means:
- No constraint verification
- No task-level audit trail
- No interruptibility

Proceeding anyway...
```

**Principle:** Dispositor pattern is opt-out, not opt-in. User can force direct execution, but the default encourages queue discipline.

### Interaction Examples

#### Example 1: Feature Request (Enqueue)

```
User: "Add email notifications for task deadlines"

Dispositor:
Created task: aops-def456 "Add email notifications for task deadlines"
Priority: 2
Workflow: feature-dev

Constraints that will apply:
- Plan required before implementation
- Tests must exist before code
- Critic review before commit

Run `/pull aops-def456` to start, or I can answer questions about the design.
```

#### Example 2: Simple Question (Direct)

```
User: "What's the format for workflow constraint files?"

Dispositor:
Workflow constraints use YAML with these rule types:
- BEFORE X: Y (precondition)
- AFTER X: Y (postcondition)
- ALWAYS: X (invariant)
- NEVER: X (prohibition)
- IF X THEN Y (conditional)
- ON X: INVOKE Y (trigger)

See aops-core/specs/workflow-constraints.md for full specification.
```

#### Example 3: Command (Direct)

```
User: "/commit"

[Skill executes directly, no task created]
```

#### Example 4: Decomposition (Hybrid)

```
User: "I need to write my dissertation"

Dispositor:
This is a multi-session project that benefits from decomposition.

Created goal: aops-ghi789 "Write dissertation"
Workflow: decompose

Running initial decomposition to identify major components...
[spawns decompose workflow, creates child tasks]

Created 5 initial tasks:
1. [TBD] Literature review scope
2. [TBD] Chapter outline
3. [TBD] Methodology section
4. [CLARIFY] Data source decisions
5. Review: Approve decomposition

The REVIEW task blocks the others. Run `/pull` when ready to approve structure.
```

### Architectural Implications

#### Session State Changes

New session state field: `mode: dispositor | executor | direct`

- `dispositor`: Main agent in enqueue-only mode
- `executor`: Running `/pull`, executing task
- `direct`: Bypassed queue (command, skill, question)

#### Hydrator Changes

Hydrator output gains `execution_path` field:

```markdown
## Prompt Hydration

**Intent**: Add dark mode toggle
**Workflow**: feature-dev
**Execution Path**: enqueue ← NEW

### Task Specification

[details for task creation]
```

#### Agent Prompt Changes

Main agent system prompt includes:

```markdown
## Role: Dispositor

You are a work router, not a worker. Your responsibilities:

1. Understand user intent
2. Select appropriate workflow
3. Create tasks with full context
4. Answer questions about work
5. Direct user to `/pull` for execution

You do NOT:

- Modify code files
- Run tests
- Make commits
- Execute implementation work

Exceptions (direct execution allowed):

- Commands: `/commit`, `/help`, etc.
- Skills: `/pdf`, `/daily`, etc.
- Questions: No state changes needed
- Conversation: Social interaction
```

## Acceptance Criteria

### Part 1: Logical-Statement Format

1. [x] Rule syntax defined (6 types: BEFORE, AFTER, ALWAYS, NEVER, IF-THEN, ON-INVOKE)
2. [x] Can express feature-dev as constraints without procedural loss
3. [x] Can express decompose as constraints without procedural loss
4. [x] Can express tdd-cycle as constraints without procedural loss
5. [x] Predicate evaluation methods specified
6. [x] Composition via inheritance defined

### Part 2: Dispositor Pattern Acceptance Criteria

1. [x] Separation of enqueue vs execute clearly defined
2. [x] Direct execution paths enumerated with detection heuristics
3. [x] Enqueue semantics specified (what task creation looks like)
4. [x] Agent communication pattern defined
5. [x] /pull task selection logic defined
6. [x] "Just do it" resistance strategy defined
7. [x] Session state implications documented
8. [x] Hydrator output changes specified

## Implementation Notes

### Not In Scope (Deferred)

- **Constraint solver**: Hydrator checks, doesn't solve
- **Automated rollback**: Still manual revert
- **Cross-session constraint memory**: Each session starts fresh
- **Workflow versioning**: Git suffices

### Open Questions for Pilot

1. **YAML vs Markdown**: This spec uses YAML for constraints. Alternative: keep markdown with structured constraint block.
2. **Predicate registry**: Should predicates be globally defined or per-workflow?
3. **Constraint conflict resolution**: What if workflow A says ALWAYS X and workflow B says NEVER X?
4. **Partial satisfaction**: Can agent proceed if only some constraints are verifiable?

## Relationships

- Supersedes procedural aspects of [[workflow-system-spec]]
- Extends [[prompt-hydration]] with constraint checking
- Works with [[enforcement]] layer model
- Parent task: [[aops-a31d483c]]
