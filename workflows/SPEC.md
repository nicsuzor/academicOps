---
id: workflows-spec
category: meta
description: Defines what workflows are, their structure, and how the hydrator composes them
---

# Workflows Specification

This document defines what workflows are in academicOps, their structure, and how the prompt-hydrator agent selects and composes them.

## What Is a Workflow?

A **workflow** is a documented procedure for accomplishing a category of work. Workflows are:

- **Declarative**: They describe *what to do*, not *who does it*
- **Composable**: One workflow can reference or hand off to another
- **Agent-agnostic**: Any agent with the right tools can follow a workflow

**Key distinction**: Agents have *expertise* (judgment, selection logic). Workflows have *procedures* (step-by-step instructions). The hydrator agent selects workflows; the main agent executes them.

## Workflow Structure

Every workflow follows this structure:

```markdown
---
id: [kebab-case-name]
category: [planning | routing | operations | meta]
---

# [Workflow Name]

## Overview
[1-2 sentences: what this workflow does and why it exists]

## When to Use
[Bulleted list of triggering conditions]

## When NOT to Use
[Bulleted list of exclusion criteria, pointing to alternative workflows]

## Steps
[Numbered procedure with clear actions]

## Quality Gates / Success Metrics
[Checkboxes for completion verification]
```

### Optional Sections

- **Philosophy**: For complex workflows that need conceptual grounding
- **Examples**: Concrete scenarios showing the workflow in action
- **Anti-Patterns**: Common mistakes to avoid
- **Integration with Other Workflows**: How this workflow connects to others

## Workflow Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **routing** | Directs requests to the right place | direct-skill, simple-question |
| **planning** | Structures work before execution | decompose, spec-review |
| **operations** | Executes tracked work | bd-workflow, interactive-triage |
| **meta** | Documents the workflow system itself | this spec |

## How the Hydrator Selects Workflows

The prompt-hydrator agent receives a user prompt and selects the appropriate workflow through this process:

### 1. Context Gathering

Hydrator gathers:
- User intent from the prompt
- Relevant memories (`mcp__memory__retrieve_memory`)
- Current work state (`bd ready`, `bd list`)
- Pre-loaded workflow index (WORKFLOWS.md)

### 2. Scope Detection

Hydrator classifies the request:

| Scope | Indicators | Implications |
|-------|------------|--------------|
| **Single-session** | Bounded task, known path, can complete now | One workflow, no deferred work |
| **Multi-session** | Goal-level request, uncertain path, spans days+ | Decomposition task needed |

### 3. Path Assessment

Hydrator determines execution path:

| Path | Criteria | Output |
|------|----------|--------|
| **EXECUTE** | What/Where/Why/How all known, session-scoped | Execution plan with TodoWrite |
| **TRIAGE** | Missing info, needs human judgment, exceeds scope | Triage guidance, then HALT |

### 4. Workflow Selection

Hydrator matches intent to workflow using the decision tree in WORKFLOWS.md:

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────> [[direct-skill]]
    │
    ├─ Simple question, no files? ─────────────> [[simple-question]]
    │
    ├─ Bug or unexpected behavior? ────────────> [[debugging]]
    │
    ├─ Multi-session goal, uncertain path? ────> [[decompose]]
    │
    ├─ Review needed before implementation? ───> [[spec-review]]
    │
    ├─ New feature with known steps? ──────────> [[feature-dev]]
    │
    ├─ Small, bounded change? ─────────────────> [[minor-edit]]
    │
    └─ Already tracked in bd? ─────────────────> [[bd-workflow]]
```

### 5. Output

Hydrator returns a structured plan:

```markdown
## HYDRATION RESULT

**Intent**: [what user wants]
**Scope**: single-session | multi-session
**Path**: EXECUTE | TRIAGE
**Workflow**: [[workflows/selected-workflow]]

### BD Task Routing
[How to track this work]

### Execution Plan
[TodoWrite items for the main agent]
```

The main agent then follows the selected workflow.

## Workflow Composition Patterns

Workflows can reference each other in several ways:

### 1. Sequential Handoff

One workflow completes, then explicitly hands off to another:

```markdown
## Integration with Other Workflows

After decomposition completes, actionable tasks enter [[bd-workflow]] for execution.
```

### 2. Conditional Routing

A workflow routes to different workflows based on conditions:

```markdown
If the request matches a single skill: use [[direct-skill]]
If the request requires planning: use [[spec-review]]
```

### 3. Nested Invocation

A workflow invokes another as part of its steps:

```markdown
### Step 4: Get Critic Review

Invoke spec-review workflow for feedback:
- Spawn critic agent
- Iterate until convergence
```

### 4. Parallel Tracks

Multiple workflows apply to different aspects of the same work:

```markdown
- [[decompose]] breaks down the goal
- [[bd-workflow]] tracks each task
- [[feature-dev]] implements code tasks
```

## Composition Rules

### DO

- **Reference by wikilink**: Use `[[workflows/name]]` for discoverability
- **Specify handoff points**: Make clear when one workflow ends and another begins
- **Match granularity**: Don't invoke a heavy workflow for a light task
- **Preserve context**: Pass relevant state when handing off

### DON'T

- **Create circular dependencies**: Workflow A invoking B invoking A
- **Skip the hydrator**: The hydrator selects the initial workflow; composition happens within execution
- **Mix agent logic with workflow steps**: Workflows are procedures, not decision-making
- **Duplicate steps**: If another workflow does it, reference it

## Adding New Workflows

1. **Identify the gap**: What category of work lacks a documented procedure?
2. **Check for overlap**: Could an existing workflow be extended instead?
3. **Follow the structure**: Use the standard sections (Overview, When to Use, etc.)
4. **Add to WORKFLOWS.md**: Update the decision tree with selection criteria
5. **Link from hydrator**: Ensure the hydrator can route to the new workflow

## Maintaining Workflows

- **Review stale workflows**: If a workflow isn't being selected, it may need revision or removal
- **Track friction**: If users override hydrator selections, the decision tree needs adjustment
- **Version carefully**: Workflow changes affect all agents that follow them

## Related Documents

- [[agents/prompt-hydrator]]: The agent that selects workflows
- [[WORKFLOWS.md]]: The workflow index with decision tree (pre-loaded to hydrator)
- [[HEURISTICS.md]]: Framework principles that inform workflow design
