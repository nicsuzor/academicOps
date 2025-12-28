---
name: task-expand
description: Expand tasks into context-aware subtasks with automation detection and dependency tracking. Asynchronous, intelligent task breakdown.
allowed-tools: Read,Grep,Glob,mcp__memory__retrieve_memory,mcp__memory__retrieve_with_quality_boost
version: 1.0.0
permalink: skills-task-expand
---

# Task Expansion Skill

Intelligently expand tasks into actionable subtasks using project context, memory retrieval, and dependency analysis.

## When to Use

Use this skill when:
- Creating a new task that needs breakdown
- Expanding a captured idea into executable steps
- Preparing tasks for delegation or automation

Do NOT use for:
- Simple, atomic tasks ("send email to X")
- Tasks user wants to keep high-level
- When user explicitly says "don't expand"

## Core Principles

### 1. Conservative Expansion (No Mountains from Molehills)

**CRITICAL**: Not every task needs expansion. Before expanding, check:

| Task Type | Expansion? | Rationale |
|-----------|------------|-----------|
| Single clear action | NO | "Schedule meeting with Bob" is already atomic |
| Multi-step deliverable | YES | "Complete grant application" has clear phases |
| Vague goal | CLARIFY FIRST | "Improve workflow" needs scoping before expansion |
| Decision needed | MAYBE | "Choose conference to submit to" might need research subtasks |

**Rule**: If the task can be done in one sitting without context switches, don't expand it.

### 2. Authority Boundaries

Never expand beyond the task's stated scope:

- If task says "draft outline", don't add "finalize and submit"
- If task is about research, don't add implementation steps
- Respect the user's implied completion point

### 3. Project Context First

Before generating subtasks, query memory server for:

```
mcp__memory__retrieve_memory(query="project [project-name] workflow patterns")
mcp__memory__retrieve_memory(query="[task-topic] previous approaches")
```

Use discovered patterns to:
- Match existing workflows (don't invent new approaches)
- Reference established conventions
- Identify related prior work

### 4. Usefully-Sized Subtasks

Good subtasks are:
- Completable in one focused session (15 min - 2 hours)
- Independently verifiable ("done" is unambiguous)
- Not redundant with each other

Bad subtasks:
- Too granular: "Open email app", "Click compose", "Type greeting"
- Too vague: "Do the research part"
- Overlapping: "Review draft" + "Check draft quality"

## Expansion Process

### Step 1: Assess Expansion Need

```
Is this task:
- Already atomic? → SKIP expansion
- Clear multi-step? → PROCEED to Step 2
- Vague? → ASK for clarification first
```

### Step 2: Gather Context

Query memory server:
```
1. Project context: "project [project] current status"
2. Topic patterns: "[topic] how we handle"
3. Dependencies: "[topic] related tasks or blockers"
```

Check existing tasks:
```bash
grep -li "[keyword]" $ACA_DATA/tasks/inbox/*.md
```

### Step 3: Generate Subtasks

For each subtask, determine:

| Field | Description |
|-------|-------------|
| **title** | Clear action verb + object |
| **depends_on** | Which other subtasks must complete first (by index) |
| **automatable** | Could an agent do this without human decisions? |
| **effort** | quick (<15min), short (15-60min), medium (1-2hr) |

### Step 4: Format Output

Output subtasks as checklist items with inline metadata:

```markdown
## Checklist

- [ ] Research existing approaches [effort:: quick] [automatable:: yes]
- [ ] Draft initial structure [effort:: short] [depends:: 1]
- [ ] Review with stakeholder [effort:: short] [depends:: 2] [automatable:: no]
- [ ] Incorporate feedback [effort:: medium] [depends:: 3]
```

## Automation Detection

Mark subtask as **automatable: yes** when:
- Pure research/information gathering
- File operations (create, move, organize)
- Compilation/build steps
- Template application
- Routine data extraction

Mark subtask as **automatable: no** when:
- Requires human judgment or creativity
- Involves external human interaction
- Needs approval or sign-off
- Contains subjective decisions

Mark subtask as **automatable: partial** when:
- Agent can prepare, human finalizes
- Research can be done, but decision is human's
- Draft can be generated, but review needed

## Dependency Notation

Use `[depends:: N]` where N is the subtask number(s):

```markdown
- [ ] 1. Gather requirements [effort:: short]
- [ ] 2. Design solution [depends:: 1]
- [ ] 3. Implement core [depends:: 2]
- [ ] 4. Write tests [depends:: 2] <!-- can parallel with 3 -->
- [ ] 5. Integration testing [depends:: 3, 4]
```

This enables:
- Parallel execution of independent subtasks
- Clear critical path identification
- Proper sequencing when working through tasks

## Integration with /q Command

When invoked via `/q`:

1. Accept raw task fragment (zero friction capture)
2. Query memory for context
3. Decide: expand or keep atomic
4. If expanding, generate subtasks with metadata
5. Create task via `task_add.py` with checklist

## Integration with /add Command

When invoked via `/add`:

1. Receive task from session context
2. Check for related existing tasks (avoid duplicates)
3. If task warrants expansion, apply this skill
4. Add as new task or checklist item to existing task

## Anti-Patterns

### Don't Over-Engineer

```
# BAD - too granular
Task: "Send status update email"
- [ ] Open email client
- [ ] Click compose
- [ ] Enter recipient
- [ ] Write subject
- [ ] Draft body
- [ ] Review for typos
- [ ] Click send

# GOOD - atomic, no expansion needed
Task: "Send status update email"
(no expansion - this is a single action)
```

### Don't Scope Creep

```
# BAD - exceeds original scope
Task: "Research conference submission options"
- [ ] Research conferences
- [ ] Choose best fit
- [ ] Write paper abstract  <!-- SCOPE CREEP -->
- [ ] Submit paper          <!-- SCOPE CREEP -->

# GOOD - stays within scope
Task: "Research conference submission options"
- [ ] List relevant conferences in field
- [ ] Check deadlines and formats
- [ ] Note submission requirements
- [ ] Summarize options for decision
```

### Don't Ignore Existing Patterns

```
# BAD - invents new workflow
Task: "Process grant application"
- [ ] Create new tracking spreadsheet
- [ ] Set up custom reminder system

# GOOD - uses existing patterns (from memory context)
Task: "Process grant application"
- [ ] Add to grants project in task system
- [ ] Follow grant-submission workflow from specs/
```

## Example Usage

**Input** (via /q):
```
"need to prepare presentation for faculty meeting next week about our new AI tools policy"
```

**Memory Query**:
```
mcp__memory__retrieve_memory(query="faculty meetings presentation format")
mcp__memory__retrieve_memory(query="AI tools policy current state")
```

**Output**:
```markdown
---
title: Prepare AI tools policy presentation for faculty meeting
priority: 1
due: 2025-01-03
project: qut-governance
---

# Prepare AI tools policy presentation for faculty meeting

## Context
Faculty meeting presentation on AI tools policy. Follows standard faculty meeting format.

## Checklist

- [ ] Review current AI policy draft [effort:: quick] [automatable:: yes]
- [ ] Identify key points for faculty audience [effort:: short] [automatable:: partial]
- [ ] Create slides using faculty template [effort:: medium] [depends:: 1, 2]
- [ ] Prepare speaking notes [effort:: short] [depends:: 3]
- [ ] Practice run-through [effort:: short] [depends:: 4] [automatable:: no]
```

## When to HALT

- Task is ambiguous and user not available to clarify
- Conflicting information from memory/context
- Task implies work outside user's known projects
- Expansion would require creating new workflows not in specs/
