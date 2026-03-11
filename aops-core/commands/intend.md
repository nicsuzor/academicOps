---
name: intend
type: command
category: instruction
description: Declare, list, or complete active intentions
triggers:
  - "I intend to"
  - "my intention is"
  - "set intention"
  - "focus on"
  - "what am I working on"
  - "what are my intentions"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Task, Bash, Read, Write, Edit, Grep, Skill, AskUserQuestion, mcp__pkb__search, mcp__pkb__task_search, mcp__pkb__get_task, mcp__pkb__get_task_children, mcp__pkb__update_task
permalink: commands/intend
---

# /intend — Declare What You Intend to Accomplish

**Purpose**: Set 1-3 active intentions that organise everything downstream — daily notes, `/pull`, dashboard, focus scoring, and agent dispatch all scope to your intention subgraphs.

An intention is a pointer to an existing PKB node (goal, project, or epic). It is NOT a new document. It says: "this is what I'm trying to accomplish right now."

## Usage

| Command                           | Behaviour                                  |
| --------------------------------- | ------------------------------------------ |
| `/intend "get the OSB study out"` | Declare a new intention                    |
| `/intend`                         | List active intentions with subgraph stats |
| `/intend done "OSB study"`        | Complete an intention                      |
| `/intend clear`                   | Clear all intentions (with confirmation)   |

## Workflow

### Declare: `/intend "description"`

1. **Search PKB** for matching goal, project, or epic using `mcp__pkb__search` with the user's description. If results are weak or empty, also try `mcp__pkb__task_search`.

2. **Filter to valid root types**: Only show results where `type` is `goal`, `project`, or `epic`. Individual tasks are too granular for intentions — use `/pull` for those.

3. **Present candidates** with breadcrumb and child count. For each:

```
1. [osb-benchmarking-abc123] OSB Benchmarking Study (project)
   Goal > Digital Platform Regulation > OSB Benchmarking Study
   12 descendants, 4 ready, 3 done

2. [osb-pao-def456] OSB PAO 2025E Review (epic)
   Goal > Digital Platform Regulation > OSB PAO Reviews > 2025E
   6 descendants, 2 ready, 1 done
```

Use `mcp__pkb__get_task(id=...)` for each to get parent chain, then `mcp__pkb__get_task_children(id=..., recursive=True)` for descendant stats.

4. **User confirms** which node is the intention root.

5. **Check for empty subgraph**: If the root has no leaf tasks (all descendants are goals/projects/epics with no actionable children), ask:

```
AskUserQuestion: "This node has no actionable tasks yet. Shall I decompose it into concrete tasks?"
Options: "Yes, decompose" | "No, just set it"
```

If yes, invoke the effectual planner's Mode 2 (decomposition) via `Skill(skill="planning")`.

6. **Write to intentions file**: Read `$ACA_DATA/intentions.yaml` (create with `version: 1, active: [], max_active: 3` if missing). If at capacity (`active` count ≥ `max_active`), ask the user which intention to replace. Append the new entry with `root_id`, `declared` (ISO 8601 now), and `label` (user's original description). Write back.

7. **Report**:

```
Intention set: "Get the OSB benchmarking study out"
Root: [osb-benchmarking-abc123] OSB Benchmarking Study (project)
Progress: ██████░░░░ 12/20 tasks (60%)
Ready now: 4 tasks
Next task: [ns-abc] Write methods section (P1)
```

### List: `/intend` (no arguments)

1. Read `$ACA_DATA/intentions.yaml`
2. If empty, prompt user to declare an intention
3. For each active intention:
   - Load root node: `mcp__pkb__get_task(id=root_id)`
   - Get descendants: `mcp__pkb__get_task_children(id=root_id, recursive=True)`
   - Compute stats (total, done, ready, blocked, in_progress)
   - Identify next task (highest-priority ready leaf)
   - Check staleness (>7 days with no completed tasks)

4. Display:

```
## Active Intentions

### 1. Get the OSB benchmarking study out
Root: [osb-benchmarking] OSB Benchmarking Study (project)
Progress: ██████░░░░ 12/20 (60%)
Ready: 4 | Blocked: 2 | In Progress: 1
Next: [ns-abc] Write methods section (P1)
Declared: 3 days ago

### 2. Ship the intentions feature
Root: [aops-intentions] Intentions Feature (epic)
Progress: ██░░░░░░░░ 3/15 (20%)
Ready: 2 | Blocked: 0 | In Progress: 0
Next: [ns-mno] Write intentions spec (P0)
Declared: today

Use `/intend done "label"` to complete, `/intend "description"` to add.
```

### Complete: `/intend done "label"`

1. Read `$ACA_DATA/intentions.yaml`
2. Match by label (fuzzy) or root_id
3. Show final stats:

```
Completing intention: "Get the OSB benchmarking study out"
Final progress: ██████████ 20/20 (100%)
Duration: 14 days (declared 2026-02-24)
```

4. Prompt for brief reflection:

```
AskUserQuestion: "Brief reflection on this intention — what went well, what was harder than expected?"
Options: "Skip reflection" | "Went smoothly" | "Harder than expected"
```

5. Remove from `$ACA_DATA/intentions.yaml`
6. If user provides reflection, append to daily note's Today's Story section
7. Ask if they want to declare a replacement intention

### Clear: `/intend clear`

1. Confirm: "Clear all N active intentions? This resets to the global task view."
2. If confirmed, write empty `active: []` to `$ACA_DATA/intentions.yaml`
3. Report: "Intentions cleared. `/pull` and daily note will use the full task queue."

## Progress Bar Format

Use a 10-character bar: filled blocks (█) for `round(done / total * 10)` characters, empty (░) for the remainder. If `total` is 0, show all empty. Example: 6/10 done → `██████░░░░`.

## File Format

The `$ACA_DATA/intentions.yaml` file:

```yaml
version: 1
active:
  - root_id: "osb-benchmarking-abc123"
    declared: "2026-03-10T09:00:00+10:00"
    label: "Get the OSB benchmarking study out"
max_active: 3
```

If the file doesn't exist, treat as empty (no intentions). Create on first `/intend` declaration.

## Constraints

- **Max 3 active intentions** (configurable via `max_active` in YAML). More than 3 defeats the purpose — you're not focusing.
- **Root must be goal, project, or epic.** Tasks are too granular. Use `/pull <task-id>` for single-task focus.
- **Intentions persist across sessions** until explicitly completed or cleared.
- **No duplicate roots.** If user tries to add an intention for a node that's already active, report that it's already an intention.
