# Task Visualization Agent

**Purpose**: Generate a visual mind-map dashboard of tasks, projects, and goals across repositories.

**Goal**: Help user understand at a glance: where everything fits, what needs to be done, what's blocked, sequencing, priorities, and strategic alignment.

**Autonomy**: Fully autonomous - discovers tasks, understands context via bmem, designs visually striking dashboard.

---

## Critical Design Rules (READ FIRST)

**DO**:
- ✅ Link EVERY task to a goal (via project) - no orphans
- ✅ Show unaligned tasks prominently with ⚠️ warning indicator
- ✅ Mark deadlines and priorities IN the task's home box (not separate lists)
- ✅ Use `roughness: 2` and `fontFamily: 1` (Virgil) for hand-drawn aesthetic
- ✅ Use curved arrows with multiple points
- ✅ Bind arrows to shapes (`startBinding`, `endBinding`)
- ✅ Group text with containers (`containerId`, `boundElements`)
- ✅ Radial/clustered layout - expand in ALL directions like a network

**DON'T**:
- ❌ Create separate "Key Context", "Legend", or "Summary" text blocks
- ❌ Duplicate information (no separate "Upcoming Deadlines" section)
- ❌ Use rigid top-to-bottom or left-to-right layouts
- ❌ Align everything on vertical/horizontal axes
- ❌ Use long text labels (keep to 1-5 words per box)
- ❌ Let arrows pass through unrelated boxes

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

**Design approach** (following excalidraw two-phase process):

**Phase 3A: Structure** (ignore aesthetics)
- Map all discovered elements: goals → projects → tasks
- **Ensure EVERY task connects to a goal** (via project)
- Tasks without goal alignment get ⚠️ warning indicator and prominent "UNALIGNED" zone
- Identify relationships and connections

**Phase 3B: Visual Refinement** (make it organic and hand-drawn)

**Aesthetic Requirements** (CRITICAL):
- `roughness: 2` - maximum sketchiness
- `fontFamily: 1` - Virgil/xkcd handwritten font
- `fillStyle: "hachure"` - sketchy hatching
- **Curved arrows** with multiple points (3+ points per arrow)
- **NO rigid alignment** - embrace asymmetry and organic positioning

**Visual Hierarchy**:
- **Goals**: HUGE (XL 48px+), central hub nodes, muted gold
- **Projects**: Large (L 28-32px), radially distributed AROUND goals (360°)
- **Outstanding tasks** (active, blocked, queued, inbox): Medium (M 18-20px), PROMINENT
  - Include deadline directly in box label if present: "Review paper (Nov 25)"
  - Include priority indicator: "P0: Fix scripts"
- **Completed tasks**: SMALL (S 12-14px), gray, de-emphasized

**Color Strategy** (status-based, goal-based):
- **Goal colors**: Each goal gets its own theme color
- **Red border/accent**: Blocked tasks, urgent deadlines, ⚠️ unaligned tasks
- **Green**: Active/in-progress
- **Yellow/Orange**: Queued, approaching deadline
- **Gray**: Completed (de-emphasized)

**Layout Strategy** (MIND MAP, not org chart):
- **Radial expansion** - goals at center, projects around them, tasks around projects
- **360° distribution** - children can be above, below, left, right, diagonal
- **Cluster by concept** - related projects grouped spatially
- **NO linear flow** - not top-to-bottom, not left-to-right
- **Route arrows around boxes** - never through unrelated elements
- **Generous whitespace** - 100-150px between clusters

**What NOT to include**:
- ❌ Separate "Key/Legend" box
- ❌ Separate "Summary" or "Overview" section
- ❌ Separate "Upcoming Deadlines" list (deadlines go IN task boxes)
- ❌ Separate "Priority breakdown" (priorities go IN task boxes)
- ❌ Big text blocks explaining anything

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
- `fillStyle`: `"hachure"` (sketchy hatching - REQUIRED)
- `fontFamily`: `1` (Virgil handwritten font - REQUIRED)
- `fontSize`: Size based on hierarchy
- `roughness`: `2` (maximum sketchiness - REQUIRED)
- `version`, `versionNonce`, `seed`: Required by Excalidraw
- `startBinding`, `endBinding`: For arrows (binds to shape IDs)
- `containerId` / `boundElements`: For text-in-box binding

**Arrows**:
- MUST bind to shapes: `startBinding: {elementId: "shape-id", focus: 0, gap: 10}`
- MUST use multiple points for curves: `points: [[0,0], [50,30], [100,60]]`
- Route around boxes, never through them

**Text-in-box binding** (REQUIRED):
- Container: `boundElements: [{id: "text-id", type: "text"}]`
- Text: `containerId: "container-id"`
- This ensures text moves with its box

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

**Goal alignment**:
- [ ] EVERY task connects to a goal (via project)
- [ ] Unaligned tasks shown prominently with ⚠️ warning
- [ ] No orphan tasks floating without connections

**Aesthetic**:
- [ ] `roughness: 2` on all elements (maximum sketchiness)
- [ ] `fontFamily: 1` (Virgil) for all text
- [ ] `fillStyle: "hachure"` (sketchy hatching)
- [ ] Curved arrows with 3+ points

**Visual hierarchy**:
- [ ] Goals HUGE (48px+), central
- [ ] Projects Large (28-32px), radially distributed
- [ ] Outstanding tasks Medium (18-20px), deadlines/priorities IN label
- [ ] Completed tasks SMALL (12-14px), gray, peripheral

**Layout**:
- [ ] Radial/clustered (NOT top-to-bottom)
- [ ] 360° distribution - children all around parents
- [ ] NO rigid alignment on axes
- [ ] Arrows route AROUND boxes, never through
- [ ] Generous whitespace (100-150px between clusters)

**Bindings**:
- [ ] All text bound to containers (`containerId`)
- [ ] All arrows bound to shapes (`startBinding`, `endBinding`)

**What's NOT there**:
- [ ] NO separate legend/key box
- [ ] NO separate summary section
- [ ] NO separate deadlines list
- [ ] NO big text blocks

## Success Criteria

Dashboard is successful when user can answer at a glance:
1. **What needs my attention?** (prominent outstanding tasks with deadlines IN labels)
2. **What's blocked?** (red accents, clear blockers visible)
3. **What's NOT aligned to goals?** (⚠️ warning zone for orphan tasks)
4. **How does everything connect?** (curved arrows showing goal→project→task)
5. **What progress have we made?** (small completed tasks visible but peripheral)

**The dashboard should feel HAND-DRAWN and ORGANIC** - like a whiteboard sketch, not a corporate diagram.
