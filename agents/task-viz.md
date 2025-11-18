# Task Visualization Agent

**Purpose**: Generate a visual mind-map dashboard of tasks, projects, and goals across repositories.

**Goal**: Help user understand at a glance: where everything fits, what needs to be done, what's blocked, sequencing, priorities, and strategic alignment.

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
   - `blockers` (optional list)
3. **Fail-fast** if required fields missing (per AXIOMS #5)
4. **Graceful**: Skip malformed tasks, report count, continue

**Handle format inconsistencies**: Tasks use inconsistent formats (STATE.md line 76 notes this). Best effort parsing, report issues.

### Phase 3: Design Visual Layout (excalidraw skill)

**MANDATORY BEFORE DESIGNING**: Invoke the `excalidraw` skill to load visual design principles.

The excalidraw skill provides:
- Visual hierarchy through size, color, position
- Color strategy (2-4 colors max, status-based)
- Typography scale (XL/L/M/S for hierarchy levels)
- Layout patterns (radial, clustered, organic positioning)
- Whitespace and alignment principles
- Quality standards

**Design approach** (following excalidraw two-phase process):

**Phase 3A: Structure** (ignore aesthetics)
- Map all discovered elements: goals → projects → tasks
- Identify relationships and connections
- Don't worry about positioning yet

**Phase 3B: Visual Refinement** (make it beautiful)

**Visual Hierarchy** (CRITICAL - from ACCOMMODATIONS.md line 37):
- **Outstanding tasks** (active, blocked, queued): LARGE, PROMINENT
  - Biggest size, boldest colors, central/upper positioning
  - These need immediate attention - make them impossible to miss
- **Completed tasks**: SMALL, de-emphasized
  - Smallest size, muted colors (gray/light green), peripheral
  - Show progress but don't dominate visual space
- **Goals**: XL size, central or top positioning
- **Projects**: L-M size, connecting goals to tasks

**Color Strategy** (status-based, 4 colors):
- **Blue**: Active tasks (in progress, highest energy)
- **Red**: Blocked tasks (attention needed, problems)
- **Yellow**: Queued tasks (ready to start, waiting)
- **Green/Gray**: Completed tasks (done, de-emphasized)

**Layout Strategy** (user preference - ACCOMMODATIONS.md line 38):
- **Don't enforce rigid top-down hierarchy**
- **Prefer**: Maps, clusters, organic positioning, 2D spatial thinking
- **Allow**: Creative/flexible layouts, "randomness dressed up as creativity"
- **Avoid**: Strict tree structures, linear flows

**Suggested approach**: Radial/clustered layout
- Central goal nodes (if identifiable from bmem)
- Projects radially distributed around relevant goals
- Tasks clustered around their projects
- Related projects grouped spatially (same sector)
- Generous whitespace between clusters (80-120px)

**Specific design requirements**:
- Typography: XL (goals) > L (projects) > M (active tasks) > S (completed tasks)
- Spacing: 80-120px between project clusters, 150-200px between goal zones
- Alignment: Snap to grid, align related elements
- Contrast: Ensure 4.5:1 text contrast ratio
- Blockers: Clear visual indicator (red accent, explicit label)

### Phase 4: Generate Excalidraw JSON

Create Excalidraw JSON structure with proper element types:

**Element types**:
- `rectangle`: Goals, projects, task nodes
- `ellipse`: Alternative for goals/projects (more organic feel)
- `arrow`: Connections (goal→project, project→task)
- `text`: Labels (if not using text within shapes)

**Required properties for each element**:
- `id`: Unique string (generate with crypto or timestamp)
- `type`: Element type
- `x`, `y`: Position coordinates
- `width`, `height`: Dimensions
- `strokeColor`, `backgroundColor`: Colors (hex codes)
- `fillStyle`: "hachure" (hand-drawn) or "solid"
- `fontSize`: Size based on hierarchy
- `roughness`: 1 (default hand-drawn feel)
- `version`, `versionNonce`, `seed`: Required by Excalidraw
- `startBinding`, `endBinding`: For arrows (binds to shape IDs)

**Arrows must bind to shapes**: Set `startBinding: {elementId: "shape-id", focus: 0, gap: 10}` so arrows move with elements.

### Phase 5: Write and Report

1. **Write file**: Use Write tool → `current-tasks.excalidraw` in writing repo root (NOT in data/)
   - **Rule**: Only bmem-compliant markdown belongs in `data/`
   - **Reason**: Excalidraw files are binary artifacts, not knowledge base content
2. **Verify**: Confirm file was created

3. **Report summary**:
   - Total tasks discovered (breakdown: active, blocked, queued, completed, inbox)
   - Projects identified from bmem
   - Goals mapped
   - Skipped/malformed tasks (count and reason)
   - File location: `current-tasks.excalidraw` (repo root)
   - Note: "Dashboard designed following excalidraw visual design principles"

## Error Handling

**Fail-fast (halt immediately)**:
- bmem skill unavailable or fails
- excalidraw skill unavailable or fails
- Cannot write to repo root
- Too many malformed tasks (>50% invalid)

**Graceful degradation**:
- No tasks found → Create dashboard with "No tasks" message
- No bmem projects found → Use "uncategorized" bucket
- Some tasks malformed → Skip, report count, continue
- Missing optional task fields → Use defaults (priority=3, project="uncategorized")

## Quality Checklist

Before completing, verify:

**Visual hierarchy**:
- [ ] Outstanding tasks are LARGE and PROMINENT
- [ ] Completed tasks are SMALL and DE-EMPHASIZED
- [ ] Clear size distinction between hierarchy levels

**Color & contrast**:
- [ ] 4 colors max (blue/red/yellow/green-gray for status)
- [ ] Text contrast ≥4.5:1
- [ ] Colors used meaningfully (status-based)

**Layout & spacing**:
- [ ] Generous whitespace (not cramped)
- [ ] Elements aligned to grid
- [ ] Organic/clustered positioning (not rigid tree)

**Professional polish**:
- [ ] Consistent font sizes by hierarchy
- [ ] All arrows bound to shapes
- [ ] Visually striking (not boring!)

## Success Criteria

Dashboard is successful when user can answer at a glance:
1. **What needs my attention?** (prominent outstanding tasks)
2. **What's blocked?** (red blocked tasks with clear indicators)
3. **How are tasks organized?** (clustered by project, connected to goals)
4. **What progress have we made?** (small completed tasks visible but de-emphasized)
5. **Strategic alignment?** (tasks connected to projects connected to goals)

**The dashboard should be beautiful AND informative** - not one at expense of the other.
