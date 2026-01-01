---
name: encode
description: Capture work patterns as reusable workflows/skills through iterative refinement
allowed-tools: Read,Grep,Glob,Task,TodoWrite,Write,Edit,Skill,mcp__memory__*
permalink: commands/encode
---

# /encode - Pattern Capture

**Capture what you're doing as a reusable workflow or skill.** Two modes: track work as you do it, or extract patterns from completed work.

## Generalization Warning

> **Do not assume the current task is the only invocation mode.** When encoding:
> - Make workflows **specific about inputs/outputs** (what data flows in/out), OR
> - Make them **more general** than the immediate task (abstract the pattern)
> - Document the generalization scope in the associated spec file

## Usage

```
/encode [task]     # Start: do task while tracking steps
/encode            # Extract: review recent work, propose workflow
```

## Scenario Detection

| Context | Mode | Behavior |
|---------|------|----------|
| User provides task description | **Start** | Execute + track each step in TodoWrite |
| No task, recent work exists | **Extract** | Analyze session, create/update workflow |

Agent infers mode from context. No flags needed.

## Start Mode: Do + Track

When invoked with a task:

1. Create TodoWrite with task as first item
2. Execute the work (delegate to appropriate skills)
3. **As you work**: Add each distinct step to TodoWrite with descriptive action names
4. On completion: Summarize the steps taken

The TodoWrite history becomes evidence for pattern extraction.

## Extract Mode: Observe + Encode

When invoked without a task (or after work completes):

1. **Review**: What work was just done? (TodoWrite, conversation, session files)
2. **Identify pattern**: What's the repeatable structure?
3. **Classify**: Workflow (steps), skill (context+delegation), or command (entry point)?
4. **Create/Update**:
   - Find similar existing workflow → update it
   - New pattern → create in `skills/<domain>/workflows/`
5. **Document**: Create/update spec in `specs/` with evidence and justifications

### Workflow Creation Guidelines

When creating a workflow file:

```markdown
---
title: [Pattern Name]
type: workflow
description: [When to use - be specific about trigger conditions]
---

# Workflow: [Name]

**When**: [Specific trigger - inputs, context, user intent]

**Inputs**: [What data/context is required]

**Outputs**: [What artifacts are produced]

**Steps**:
1. [First step with verification criteria]
2. [Second step...]
...
```

### Spec Documentation

For each workflow/skill created, document in `specs/`:
- Design justifications (why this structure)
- Evidence (what observations led to this pattern)
- Generalization scope (what use cases beyond immediate task)
- Open questions (what's not yet understood)

## Examples

```bash
# Start tracking a new task
/encode add support for CSV export in the dashboard

# Later, extract the pattern
/encode

# Or extract from a specific context
/encode extract the email processing workflow we just did
```

## Iteration Pattern

```
/encode [task]     → Do + track evidence
/encode            → Extract → Create/update workflow
[try the workflow]
/encode            → Refine based on usage
[repeat until stable]
```

Multiple passes refine the pattern. Evidence accumulates. Final workflow is battle-tested.

## Related

- `/do` - Execute tasks (source of patterns to encode)
- `/q` - Queue tasks for later
- `Skill(skill="framework")` - Conventions for workflow/skill creation
