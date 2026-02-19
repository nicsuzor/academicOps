---
title: BD Markdown Integration
type: spec
status: active
created: 2026-01-14
---

# BD Markdown Integration

This spec defines how the task system (`bd` CLI / Task MCP) integrates with the markdown-based knowledge base.

## 1. Core Model

Tasks are stored as markdown files with YAML frontmatter.

### 1.1 Ownership

- **Who owns it?** (@polecat for automated, @human for human, unassigned for triage)

## 2. Visualization

The `task ready` command and `task_graph.py` script use these identifiers:

- ├─◐ aops-da01 [P1] @human Data analysis

### 2.1 Legend

| Marker     | Meaning           |
| ---------- | ----------------- |
| `@polecat` | Assigned to agent |
| `@human`   | Assigned to human |
| `[P0-4]`   | Priority          |

## 3. Command Examples

### 3.1 Creating a Discovery Task

```bash
task create "[discovery] Clarify methodology approach" --parent=aops-da01 --assignee=human
```

## 4. Triage Workflow

All new tasks entered via `/q` or manual markdown creation start as:

- status: inbox
- Assigned (@polecat or @human)

| Scenario     | Action                                       |
| ------------ | -------------------------------------------- |
| Path unclear | Create `[discovery]` task assigned to @human |
| Mechanical   | Assign to @polecat                           |
