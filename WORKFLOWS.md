---
name: workflows
title: Workflow Index
type: index
category: framework
description: Index of all available workflows for routing and execution
permalink: workflows
tags: [framework, routing, workflows, index]
---

# Workflow Index

All work MUST follow one of the workflows in this index. No exceptions.

## Available Workflows

### Development Workflows

#### [[workflows/feature-dev]]
- **ID**: `feature-dev`
- **Title**: Feature Development Workflow
- **Category**: development
- **When to use**: Adding new features, complex modifications, architectural decisions
- **Key steps**: User story → Acceptance criteria → Spec review → Approval → TDD → QA verification
- **Quality gates**: Critic review, TDD, QA verification

#### [[workflows/minor-edit]]
- **ID**: `minor-edit`
- **Title**: Minor Edit Workflow
- **Category**: development
- **When to use**: Small bug fixes, typo fixes, minor refactoring, simple one-file changes
- **Key steps**: Claim issue → Write test → Implement → Verify → Commit
- **Quality gates**: TDD, test checkpoint

#### [[workflows/debugging]]
- **ID**: `debugging`
- **Title**: Debugging Workflow
- **Category**: development
- **When to use**: Investigating bugs, root cause analysis, reproducing issues
- **Key steps**: Claim issue → Define success → Design durable test → Investigate → Report findings
- **Quality gates**: Reproducible test

#### [[workflows/tdd-cycle]]
- **ID**: `tdd-cycle`
- **Title**: Test-Driven Development Cycle
- **Category**: development
- **When to use**: Implementing features, fixing bugs, any testable code change
- **Key steps**: Red (failing test) → Green (minimal implementation) → Refactor → Commit
- **Quality gates**: Tests pass, no regression

### Planning Workflows

#### [[workflows/spec-review]]
- **ID**: `spec-review`
- **Title**: Spec Review Loop (Critic Feedback)
- **Category**: planning
- **When to use**: Designing features, planning refactoring, architectural decisions
- **Key steps**: Create spec → Invoke critic → Analyze feedback → Iterate → Converge
- **Quality gates**: Critic approval, convergence criteria

### Quality Assurance Workflows

#### [[workflows/qa-demo]]
- **ID**: `qa-demo`
- **Title**: QA Verification Demo
- **Category**: quality-assurance
- **When to use**: Before completing features, after tests pass, for user-facing changes
- **Key steps**: Gather context → Invoke QA → Analyze verdict → Fix issues → Re-verify
- **Quality gates**: QA verification (functionality, quality, completeness)

### Operations Workflows

#### [[workflows/batch-processing]]
- **ID**: `batch-processing`
- **Title**: Batch Processing Workflow
- **Category**: operations
- **When to use**: Processing multiple similar items, batch updates, parallel work
- **Key steps**: Claim issue → Identify scope → Spawn parallel agents → Monitor → Checkpoint → Commit
- **Quality gates**: All items processed, results verified

### Information Workflows

#### [[workflows/simple-question]]
- **ID**: `simple-question`
- **Title**: Simple Question Workflow
- **Category**: information
- **When to use**: Pure informational questions, no modifications needed
- **Key steps**: Answer question → HALT
- **Quality gates**: None (information only)

### Routing Workflows

#### [[workflows/direct-skill]]
- **ID**: `direct-skill`
- **Title**: Direct Skill/Command Invocation
- **Category**: routing
- **When to use**: User request maps 1:1 to existing skill/command
- **Key steps**: Identify skill → Invoke directly (no TodoWrite wrapping)
- **Quality gates**: None (delegated to skill)

## Workflow Selection Guide

### Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ─────────────> [[workflows/direct-skill]]
    │
    ├─ Simple question only? ─────────────────> [[workflows/simple-question]]
    │
    ├─ Multiple similar items? ───────────────> [[workflows/batch-processing]]
    │
    ├─ Investigating/debugging? ──────────────> [[workflows/debugging]]
    │
    ├─ Planning/designing? ───────────────────> [[workflows/spec-review]]
    │
    ├─ Small, focused change? ────────────────> [[workflows/minor-edit]]
    │
    ├─ New feature or complex work? ──────────> [[workflows/feature-dev]]
    │
    └─ Need QA verification? ─────────────────> [[workflows/qa-demo]]
```

### When to Upgrade Workflows

Start minimal, upgrade if needed:

1. **simple-question** → **feature-dev**: If answer reveals work needed
2. **minor-edit** → **feature-dev**: If change becomes complex during implementation
3. **debugging** → **minor-edit** or **feature-dev**: After understanding root cause

## Quality Gates by Workflow

| Workflow | Quality Gates |
|----------|--------------|
| feature-dev | Acceptance criteria, Critic review, TDD, Tests pass, QA verification |
| minor-edit | TDD, Tests pass |
| debugging | Reproducible test |
| tdd-cycle | Tests pass, No regression |
| spec-review | Critic feedback, Convergence |
| qa-demo | Functionality, Quality, Completeness |
| batch-processing | All items processed, Results verified |
| simple-question | None (information only) |
| direct-skill | Delegated to skill |

## Workflow Composition

Workflows can reference other workflows using [[wikilinks]]:

- **feature-dev** includes:
  - [[workflows/spec-review]] for critic feedback
  - [[workflows/tdd-cycle]] for implementation
  - [[workflows/qa-demo]] for verification

- **Any development workflow** can include:
  - [[workflows/tdd-cycle]] for test-driven development
  - [[workflows/qa-demo]] for quality assurance

## Beads (bd) Integration

Most workflows integrate with bd issue tracking:

**Standard bd workflow:**
1. Find or create issue: `bd ready`, `bd create`
2. Claim work: `bd update <id> --status=in_progress`
3. Track progress in issue
4. Close when complete: `bd close <id>`
5. Sync at session end: `bd sync`

**Workflows that require bd:**
- feature-dev
- minor-edit
- debugging
- batch-processing

**Workflows that skip bd:**
- simple-question (information only)
- direct-skill (delegated to skill)

## TodoWrite Structure by Workflow

The prompt hydrator generates TodoWrite plans based on the selected workflow:

- **feature-dev**: Full TDD cycle with QA
- **minor-edit**: Simplified without QA
- **debugging**: Investigation-focused
- **batch-processing**: Parallel execution
- **simple-question**: No TodoWrite (just answer)
- **direct-skill**: No TodoWrite (direct invocation)

See individual workflow files for detailed steps.

## Adding New Workflows

To add a new workflow:

1. Create `workflows/new-workflow.md` with YAML frontmatter
2. Add entry to this index file
3. Update hydrator selection logic if needed
4. Document when to use and quality gates
5. Create example executions

## Workflow Metadata

Each workflow file contains YAML frontmatter:

```yaml
---
id: workflow-id
title: Human Readable Title
type: workflow
category: development|planning|qa|operations|information|routing
dependencies: []  # Other workflows this composes
steps:
  - id: step-id
    name: Step Name
    workflow: null  # Or [[other-workflow]] for composition
    description: What this step does
---
```

## Next Steps

Phase 2 (Composition):
- Implement wikilink resolver
- Update hydrator to compose workflows
- Enable visual workflow graphs

Phase 3 (Enrichment):
- Integrate axioms (P# references)
- Integrate heuristics (H# references)
- Add vector memory context

Phase 4 (Decomposition):
- Auto-create bd issues from workflow steps
- Link issues with dependencies
- Enable agents to execute issues
