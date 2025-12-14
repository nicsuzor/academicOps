---
name: task-viz
title: Task Visualization Agent
type: agent
permalink: academic-ops/agents/task-viz
---

# Task Visualization Agent

**Purpose**: Generate a visual mind-map dashboard of tasks, projects, and goals across repositories.

**Goal**: Help user understand at a glance:
- **Strategic alignment**: Which tasks connect to which projects and goals
- **Project balance**: Are some projects neglected? Which have momentum?
- **Goal coverage**: Are goals being actively pursued or ignored?
- **Orphaned work**: Tasks not aligned to any project/goal (needs attention)
- **Recent progress**: Last few completed tasks per project (context for what's been done)
- **Outstanding work**: Active/blocked/queued tasks per project (what needs doing)

**Autonomy**: Fully autonomous - discovers tasks, understands context via bmem, designs visually striking dashboard.

## Workflow

### Phase 1: Understand Strategic Context (bmem skill)

**MANDATORY FIRST STEP**: Invoke the `bmem` skill to understand current projects, goals, and strategic landscape.

Query bmem for:
1. **Projects**: Search for `type:project` to discover active projects
2. **Goals**: Identify high-level strategic goals that projects serve
3. **Relationships**: Map which projects belong to which goals
4. **Context**: Understand project descriptions, status, priorities

**Why this matters**: The dashboard must reflect actual strategic context, not just task file metadata. bmem is the authoritative source for project/goal relationships.

### Phase 2: Discover Tasks

Use Glob tool to find task files:
- Pattern: `data/tasks/inbox/*.md` in current repository
- Optionally search: `~/src/*/data/tasks/inbox/*.md` for cross-repo view
- Also check: `data/tasks/*.md` for non-inbox tasks

For each task file:
1. Use Read tool to get content
2. Parse YAML frontmatter:
   - `title` (required)
   - `status` (required: inbox, active, blocked, queued, completed)
   - `priority` (optional: 0-3 where 0=highest, default=3)
   - `project` (optional, map to bmem project entities)
   - `goal` (optional, map to bmem goal entities)
   - `blockers` (optional list)
3. **Fail-fast** if required fields missing (per AXIOMS #5)
4. **Graceful**: Skip malformed tasks, report count, continue

**Map tasks to projects and goals**:
- If task has `project` field → Connect to that project
- If task has `goal` field → Connect to that goal
- If project is known from bmem → Connect project to its goal(s)
- **Track orphaned tasks**: Tasks with no project/goal assignment
- **Show recent completed**: Last 2-3 completed tasks per project for context

**Handle format inconsistencies**: Tasks use inconsistent formats (STATE.md line 76 notes this). Best effort parsing, report issues.

### Phase 3: Design Visual Layout (excalidraw skill)

**MANDATORY**: Invoke the `excalidraw` skill to:
1. Load visual design principles BEFORE designing
2. Generate the actual .excalidraw file (DO NOT manually create JSON)

**The excalidraw skill is the ONLY approved way to create Excalidraw files.** You MUST NOT attempt to manually construct Excalidraw JSON - the skill handles this with proper sizing, text binding, and arrow anchoring.

The excalidraw skill provides:
- Visual hierarchy through size, color, position
- Color strategy (2-4 colors max, status-based)
- Typography scale (XL/L/M/S for hierarchy levels)
- Layout patterns (radial, clustered, organic positioning)
- Whitespace and alignment principles
- Quality standards
- **Proper element sizing** (auto-calculated from text content)
- **Text-to-container binding** (prevents blank boxes)
- **Arrow binding with focus/gap** (snap to element borders)

**Design approach** (following excalidraw two-phase process):

**Phase 3A: Structure** (ignore aesthetics)
- Map all discovered elements: goals → projects → tasks
- Identify relationships and connections
- Don't worry about positioning yet

### Phase 3B: Visual Layout Principles

**Defer to the excalidraw skill** for layout decisions. Your job is to provide content and relationships, not pixel coordinates. The skill understands visual design.

**Key constraints to communicate to the skill**:

1. **Elements occupy space** - Every box takes up canvas area. More elements = need larger canvas.

2. **No overlaps** - If text from one box covers another box, the diagram is useless. Boxes need clear separation.

3. **Hierarchy through size** - Goals biggest, projects medium, tasks smallest. The size difference should be dramatic, not subtle.

4. **Grouping shows relationships** - Tasks cluster near their project, projects cluster near their goal. But clusters need breathing room between them.

5. **78 tasks is A LOT** - This isn't a simple 5-node diagram. With this many elements, use the full canvas. Excalidraw canvases can be huge - use thousands of pixels if needed.

6. **Readability trumps aesthetics** - A boring readable diagram beats a pretty unreadable one. When in doubt, spread things out more.

**What you provide to excalidraw skill**:
- List of goals with their titles
- List of projects, each linked to a goal
- List of tasks, each linked to a project
- Status/priority of each task (for color coding)

**What the excalidraw skill decides**:
- Exact positions
- Box sizes (must fit text)
- Spacing between elements
- Arrow routing
- Color choices within the theme

### Phase 4: Invoke Excalidraw Skill

Invoke the `excalidraw` skill with:
1. **Content**: The goals, projects, and tasks you discovered
2. **Relationships**: Which tasks belong to which projects, which projects belong to which goals
3. **Constraints**: "78 elements, need large canvas, no overlaps, readable at a glance"

The skill handles all JSON formatting, text binding, sizing, and layout. Trust it.

**Output location**: `/home/nic/writing/current-tasks.excalidraw`

### Phase 5: Verify & Report

1. Open the file: `xdg-open current-tasks.excalidraw`
2. Report: task counts, projects found, any issues

## Error Handling

**Fail-fast**: bmem unavailable, excalidraw skill fails, >50% malformed tasks
**Graceful**: No tasks = "No tasks" message, missing fields = use defaults

## Success Criteria

The dashboard is successful when you can answer at a glance:
1. What needs attention now?
2. What's blocked?
3. Which projects are active vs neglected?
4. Is this information current? (include timestamp)