---
id: decompose
category: planning
---

# Decompose Workflow

## Overview

Progressive decomposition of goals into actionable work under genuine uncertainty. Combines effectual planning (knowledge-building, assumption-tracking) with hierarchical task structures stored in bd and project markdown files.

**Key insight**: We don't decompose because we know what to do. We decompose to discover what we don't know.

## When to Use

- Scoping multi-month or multi-year projects (dissertations, books, grants)
- Breaking down goals when the path forward is unclear
- Converting high-level aspirations into trackable work
- When "I need to do X" becomes "what does X actually require?"

## When NOT to Use

- Implementation planning for known tasks (use Plan agent / EnterPlanMode)
- Simple task tracking (use bd-workflow directly)
- Tasks that can be done in one session without context switches

## Philosophy

### Effectual Decomposition

Traditional planning assumes you know the goal and work backwards to steps. Effectual decomposition works forward from what you know:

1. **Start with means** - What do you have? (skills, resources, relationships, knowledge)
2. **Surface assumptions** - What must be true for this to work? Which are untested?
3. **Find affordable probes** - What's the cheapest way to learn if this path is viable?
4. **Expand just-in-time** - Only decompose what you need to act on now

### Granularity Is Strategic

Not all tasks need the same level of detail:

| Granularity | When to Use | Example |
|-------------|-------------|---------|
| **Coarse** | Clear inputs/outputs, path uncertain | "Write chapter 3" |
| **Medium** | Some structure known, details fuzzy | "Draft methodology section" |
| **Fine** | Ready to execute, next session's work | "Outline 5 key arguments" |

Keep tasks coarse when you understand their *boundaries* but not their *internals*. Expand only when you have enough information to know *how* to do each part.

## Artifacts

This workflow produces two complementary artifacts:

### 1. bd Issues (Operational)

- Trackable, queryable, dependency-aware
- Hierarchical via `--parent` (epics contain children)
- Sequential via `bd dep` (blocks/depends-on relationships)
- Status tracked: open → in_progress → closed

### 2. Project Markdown (Contextual)

- Human-readable narrative in `$ACA_DATA/projects/<project>/`
- Rich context: why we're doing this, what we've learned, what's uncertain
- Assumption log: load-bearing hypotheses that need validation
- Decision record: choices made and their rationale

**bd is the worklist. Markdown is the memory.**

## Steps

### 1. Articulate the Goal

State what you're trying to achieve. Accept vagueness - clarity comes from work, not wishes.

```markdown
## Goal: [Name]

**Desired outcome**: [What does success look like?]
**Why now**: [What makes this timely?]
**Means available**: [Skills, resources, relationships, existing work]
**Known constraints**: [Budget, time, dependencies, politics]
```

Create a bd epic:
```bash
bd create "Goal: [Name]" --type=epic --priority=1 --description="[brief]"
```

### 2. Surface Assumptions

Every plan rests on untested beliefs. Make them explicit.

**Prompts to surface assumptions:**
- "This assumes that..." (complete the sentence for each major claim)
- "If [X] turns out to be false, this plan breaks because..."
- "The riskiest bet here is..."

Document in project markdown:
```markdown
## Assumptions

### Load-bearing (plan depends on these)
- [ ] **[Assumption]**: [Why it matters] → Probe: [How to test cheaply]

### Background (probably true, monitor)
- [Assumption]: [Why we believe it]
```

### 3. Identify Coarse-Grained Components

What are the major chunks of work? Don't detail them yet - just name the territories.

**Good coarse components:**
- Have clear-ish boundaries (you know when you're done)
- Have identifiable inputs and outputs
- Could be done somewhat independently
- Are too big to do in one session

Create as bd children:
```bash
bd create "[Component]" --parent=[epic-id] --priority=2 --description="[brief]"
```

### 4. Sequence by Information Value

Ask: "What would we learn most from doing first?"

**Prioritization heuristics:**
- **Assumption-testing**: Tasks that validate critical assumptions
- **Risk-reducing**: Tasks that eliminate paths early if they won't work
- **Enabling**: Tasks that unlock other work
- **Learning**: Tasks that build knowledge for later decisions

Set dependencies:
```bash
bd dep add [child-id] depends-on [other-id]
```

### 5. Expand One Layer

Take the highest-priority component that's ready to work. Decompose it one level deeper.

**Expansion triggers:**
- You're about to start work on this component
- You've learned something that clarifies the path
- A dependency resolved and this is now actionable

**Expansion questions:**
- What's the first thing I'd actually do?
- What decision points exist within this component?
- Where might I get stuck? (those become their own tasks)

Create finer-grained children:
```bash
bd create "[Subtask]" --parent=[component-id] --priority=2
```

### 6. Mark Ready Work

Identify what's actionable now - tasks with no unmet dependencies that are detailed enough to execute.

```bash
bd ready --epic=[epic-id]  # Show actionable tasks in this goal
```

These become candidates for the next work session.

### 7. Work and Learn

Execute ready tasks. After each significant piece of work:

**Update bd:**
```bash
bd close [task-id]  # When done
bd update [task-id] --description="[learned X, changed approach]"  # When learning
```

**Update markdown:**
- New assumptions discovered?
- Assumptions validated or invalidated?
- New components identified?
- Sequencing changes needed?

### 8. Periodic Review

Every few sessions (or when stuck), review the decomposition:

- **Orphans**: Tasks not connected to anything. Link or prune.
- **Zombies**: Tasks that no longer make sense. Close with notes.
- **New knowledge**: What have we learned that changes the plan?
- **Assumption check**: Any critical assumptions still untested?

## Example: "Write a Research Paper"

### Initial State (Coarse)

```
Epic: Write paper on X
├── Literature review (coarse - know boundaries, not internals)
├── Data collection (coarse - method unclear)
├── Analysis (coarse - depends on data)
├── Writing (coarse - structure will emerge)
└── Submission (coarse - journal TBD)
```

**Assumptions logged:**
- [ ] Dataset exists and is accessible → Probe: email data custodian
- [ ] Method Y is appropriate → Probe: pilot with 10 records
- [ ] Journal Z accepts this topic → Probe: check scope statement

### After One Session (Partial Expansion)

```
Epic: Write paper on X
├── Literature review
│   ├── Search databases for [terms] (ready)
│   ├── Screen 50 abstracts (depends on search)
│   └── Synthesize themes (depends on screening)
├── Data collection (still coarse - waiting on access)
├── Analysis (still coarse)
├── Writing (still coarse)
└── Submission (still coarse)
```

**Learned:** Database access requires ethics amendment. New task added.

### After Many Sessions (Progressively Detailed)

Components expand as work progresses and knowledge accumulates. Some areas stay coarse until needed.

## Integration with Other Workflows

- **bd-workflow**: Decompose produces bd issues; bd-workflow tracks execution
- **feature-dev**: When decomposition identifies code tasks, hand off to feature-dev
- **spec-review**: Complex components may need critic review before expansion

## Quality Gates

- [ ] Goal clearly articulated (even if vague)
- [ ] Major assumptions surfaced and documented
- [ ] Coarse components identified and linked
- [ ] At least one task is actionable (ready in bd)
- [ ] Assumption probes identified for critical unknowns

## Anti-Patterns

- **Premature detail**: Expanding everything at once. Only expand what you need to act on.
- **Hidden assumptions**: Planning as if everything is known. Surface the bets.
- **Urgency-driven sequencing**: Prioritizing by deadline instead of learning value.
- **Static plans**: Not revising decomposition as knowledge grows.
- **bd-only tracking**: Losing the rich context that markdown provides.

## Success Metrics

- Can answer "what's the next actionable step?" at any time
- Assumptions are explicit and have validation probes
- Decomposition evolves as understanding deepens
- Both bd (operational) and markdown (contextual) stay in sync
- Work blocked? Know exactly what's blocking and why
