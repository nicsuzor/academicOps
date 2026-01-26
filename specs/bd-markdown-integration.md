---
title: Markdown Integration Specification
type: spec
category: architecture
status: draft
created: 2026-01-18
---

# task-Markdown Integration Specification

## User Story

**As a** framework user
**I want** tasks connected to project markdown files with automatic decomposition and visual task trees
**So that** I can see the whole picture (strategy to tactics), throw loose goals at the system and have them structured, and know what's blocking me

## Design Principles

### Principle 1: Unified Task Abstraction

All work items are **tasks**. No separate "tiers" or "types" beyond what task already provides (epic, task, bug, etc.). The only distinctions that matter:

- **Can we decompose further?** (Do we have enough information?)
- **Is it skill-sized?** (Can @bot execute it?)
- **Who owns it?** (@bot for automated, @nic for human, unassigned for triage)

### Principle 2: Single Source of Truth

- **task** is the source of truth for tasks (status, dependencies, assignments)
- **Markdown** is the source of truth for projects/goals (context, knowledge, strategy)
- **Links** connect them (task tasks reference projects, projects display task trees)

### Principle 3: One-Way Sync for Data Integrity

Markdown task views are **read-only** and **generated from task**. Never edit task data in markdown - it will be overwritten. This prevents sync conflicts and data corruption.

### Principle 4: Progressive Decomposition

Tasks are decomposed **just-in-time** to the most detailed level currently known. Coarse tasks remain coarse until we have information to expand them. Discovery tasks bridge knowledge gaps.

---

## Component 1: Linking Schema

Tasks link to projects via the `project:` label.

**Convention**: `project:<project-slug>` where `<project-slug>` matches the markdown filename.

### Markdown Side: Project Frontmatter

Project files declare their identity:

```yaml
---
title: TJA Paper
type: project
project: tja-paper          # Must match task label
status: active
---
```


## Component 2: RO ASCII View Generator

### Purpose

Generate a read-only task tree in project markdown files, showing the full decomposition from epic to skill-sized tasks.

### tasks tree command 

```markdown
○ aops-nn1l [P1] [epic] Write TJA paper
├─○ aops-lr01 [P2] Literature review
│  ├─● aops-lr02 [P2] @bot Search databases for [terms]
│  └─○ aops-lr03 [P2] Screen 50 abstracts
├─◐ aops-da01 [P1] @nic Data analysis
│  └─○ aops-da02 [P2] [discovery] Clarify methodology
└─○ aops-wr01 [P2] Writing
   └─○ aops-wr02 [P3] Draft introduction
```

### Status Symbols

| Symbol | Meaning |
|--------|---------|
| `○` | Open |
| `●` | Closed |
| `◐` | In-progress |
| `⊘` | Blocked |

### Annotations

| Annotation | Meaning |
|------------|---------|
| `@bot` | Assigned to automated agent |
| `@nic` | Assigned to human |
| `[discovery]` | Needs human input to proceed |
| `[P1]` | Priority level |



## Component 3: Decomposition Algorithm

### Entry Point

User provides a loose goal:

```
"Write the TJA paper"
```

### Step 1: Create Epic

```bash
task create "Write TJA paper" --type=epic --priority=1 --label project:tja-paper
```

### Step 2: Infer Necessary Steps

Use domain knowledge to identify **strictly necessary** components. For "academic paper":

- Literature review
- Data collection/analysis
- Writing
- Submission

Create as children:

```bash
task create "Literature review" --parent=aops-nn1l --label project:tja-paper
task create "Data analysis" --parent=aops-nn1l --label project:tja-paper
task create "Writing" --parent=aops-nn1l --label project:tja-paper
task create "Submission" --parent=aops-nn1l --label project:tja-paper
```

### Step 3: Expand Where Possible

For each child, ask: **Do we have enough information to decompose further?**

- **Yes** → Create skill-sized subtasks
- **No** → Create discovery task to gather information

Example:
```bash
# We know how to do literature searches
task create "Search databases for [terms]" --parent=aops-lr01 --assignee=bot

# We don't know the methodology yet
task create "[discovery] Clarify methodology approach" --parent=aops-da01 --assignee=nic
```

### Step 4: Mark Ready Work

After decomposition, identify what's actionable:

```bash
task ready --label project:tja-paper
```

Shows tasks that are:
- Skill-sized (leaf nodes or explicitly marked ready)
- Have no unmet dependencies
- Assigned (@bot or @nic)

### Decomposition Heuristics

| Signal | Action |
|--------|--------|
| Domain knowledge exists (e.g., "paper" → known structure) | Infer necessary steps |
| User provided detail | Create detailed subtasks |
| Path unclear | Create `[discovery]` task assigned to @nic |
| Task is skill-sized | Stop decomposing, mark ready |
| Task is coarse but boundaries clear | Keep coarse, expand later |

### Skill-Sized Criteria (from Principle #6)

A task is skill-sized when:
- Maps to exactly one skill (python-dev, analyst, pdf, etc.)
- Clear input/output boundaries
- Can be verified independently
- No decision points requiring human input mid-task
