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

<<<<<<< Updated upstream
**Color Strategy** (status-based, 4 colors):
- **Blue**: Active tasks (in progress, highest energy)
- **Red**: Blocked tasks (attention needed, problems)
- **Yellow**: Queued tasks (ready to start, waiting)
- **Green/Gray**: Completed tasks (done, de-emphasized)
=======
**Star/Orbital Layout** (CRITICAL - like solar systems):
- **Goals** are "SUNS" at center of their own system - HUGE, prominent
- **Projects** ORBIT their goal (inner ring, 300-400px from goal center) - BALANCED SPACING
- **Tasks** ORBIT their project (outer ring, 150-200px from project center) - BALANCED SPACING
- **Minimum spacing between elements**: 100-150px (prevent crowding but not too sparse)
- Each goal is a separate "solar system" spread across the canvas (800-1200px between goal centers)
- **EVERY element has an arrow** connecting it to its parent
- **Arrows MUST bind to box edges** using `startBinding`/`endBinding` - NOT center-to-center
>>>>>>> Stashed changes

**Layout Strategy** (user preference - ACCOMMODATIONS.md line 38):
- **Don't enforce rigid top-down hierarchy**
- **Prefer**: Mind maps, organic clusters, spatial positioning, 2D thinking
- **Allow**: Creative/asymmetric layouts, "randomness dressed up as creativity"
- **Avoid**: Strict tree structures, linear flows, perfectly aligned grids, org-chart style

**Suggested approach**: Comprehensive relationship map (see excalidraw skill)

**Hierarchy**: Goals → Projects → Tasks (3-tier structure)
- **Goals** (top tier): XL size, positioned strategically across canvas
- **Projects** (mid tier): L size, clustered near their goal(s)
- **Tasks** (bottom tier): M/S size, distributed around their project

**Spatial distribution** (CRITICAL for avoiding arrow overlap):
- **Use 360° positioning**: Children can be placed ANYWHERE around parent (not just below)
- **Arrows are directional**: Direction shows relationship, position prevents overlap
- **Spread tasks radially**: Around project (top, bottom, left, right, diagonals)
- **Calculate spacing**: Ensure minimum 100-150px between task nodes to prevent arrow crossings
- **Cluster intelligently**: Group related tasks on same side, but vary angles (30°, 45°, 60° offsets)
- **Generous whitespace**: 80-120px between project clusters, 150-200px between goal zones

<<<<<<< Updated upstream
**Relationship visualization**:
- Goal → Project (bold arrows, muted color)
- Project → Task (standard arrows, status-colored)
- Show ALL connections (orphaned tasks stand out visually)
- Use arrow direction to free up positioning (don't force top-down)
=======
**Layout Strategy** (MIND MAP, not org chart):
- **Radial expansion** - goals at center, projects around them, tasks around projects
- **360° distribution** - children can be above, below, left, right, diagonal
- **Cluster by concept** - related projects grouped spatially
- **NO linear flow** - not top-to-bottom, not left-to-right
- **Route arrows around boxes** - never through unrelated elements
- **BALANCED whitespace** (CRITICAL - readable but not wasteful):
  - Between tasks: 100-150px minimum
  - Between projects: 200-300px minimum
  - Between goal systems: 800-1200px minimum
  - Canvas can be 4000-6000px wide/tall - use space efficiently
>>>>>>> Stashed changes

**Specific design requirements** (from theme [[references/theme-colors.md]]):
- **Typography**: XL (40-48px goals) > L (24-32px projects) > M (16-20px active tasks) > S (12-14px completed)
- **Spacing**: 80-120px between project clusters, 150-200px between goal zones
- **Alignment**: Snap to grid for precision, but embrace creative positioning (not rigid rows)
- **Contrast**: Ensure 4.5:1 text contrast ratio (theme colors already provide this)
- **Blockers**: Clear visual indicator (red `#ff6666`, explicit label, warning icon)
- **Colors**: Theme palette only - muted gold `#c9b458`, soft green `#8fbc8f`, blue `#7a9fbf`, orange `#ffa500`, red `#ff6666`
- **Icons**: Optional Material Symbols for status (check_circle, pending, block) - see [[references/icon-integration.md]]
- **Arrows**: Curved, not straight (for organic feel)

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
- `width`, `height`: Dimensions (text should auto-size to container width)
- `strokeColor`, `backgroundColor`: Colors (hex codes from theme)
- `fillStyle`: "solid" (clean) or "hachure" (hand-drawn)
- `fontSize`: Size based on hierarchy
- `roughness`: 1 (default hand-drawn feel)
- `version`, `versionNonce`, `seed`: Required by Excalidraw
- `startBinding`, `endBinding`: For arrows (binds to shape IDs)
- `boundElements`: Array of element IDs bound to this element (for containers)
- `containerId`: ID of container element (for text inside containers)

**Text in containers** (MANDATORY - FAILURE TO BIND TEXT = UNUSABLE OUTPUT):

<<<<<<< Updated upstream
**CRITICAL**: Every box MUST have visible text. Text binding is non-negotiable.
=======
**Text-in-box binding** (MANDATORY - NO EXCEPTIONS):

**IF TEXT IS NOT VISIBLE, THE DASHBOARD IS UNUSABLE - THIS IS THE #1 FAILURE MODE**

Every container (rectangle/ellipse) MUST have bound text. Follow this pattern EXACTLY:

**Step 1 - Create container with boundElements:**
```json
{
  "id": "container-123",
  "type": "rectangle",
  "boundElements": [
    {"id": "text-123", "type": "text"}
  ],
  "width": 200,
  "height": 80,
  ...other properties...
}
```

**Step 2 - Create text element with containerId:**
```json
{
  "id": "text-123",
  "type": "text",
  "containerId": "container-123",
  "text": "Goal Name Here",
  "width": 180,
  "fontSize": 24,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  ...other properties...
}
```

**CRITICAL REQUIREMENTS:**
- ✅ Text `id` MUST appear in container's `boundElements` array
- ✅ Container `id` MUST match text's `containerId`
- ✅ Text width should be container width minus 20px padding
- ✅ Text must have `textAlign: "center"` and `verticalAlign: "middle"`
- ✅ Text font size must match visual hierarchy (goals 48px+, projects 28-32px, tasks 16-18px)
- ❌ NEVER create containers without bound text
- ❌ Text MUST NOT have x,y coordinates - position comes from container
>>>>>>> Stashed changes

**Step-by-step text binding**:
1. Create container element with unique `id`
2. Container MUST have: `boundElements: [{id: "text-123", type: "text"}]`
3. Create text element with:
   - `containerId`: MUST match container's `id`
   - `width`: Container width minus 20px padding
   - `textAlign`: `"center"`
   - `verticalAlign`: `"middle"`
   - `x`: Container x + 10 (half padding)
   - `y`: Container y + (height/2) - (fontSize*0.6)

**Example JSON** (COPY THIS PATTERN):
```json
{
  "id": "box-1",
  "type": "rectangle",
  "x": 100, "y": 100,
  "width": 200, "height": 80,
  "boundElements": [{"id": "txt-1", "type": "text"}],
  "strokeColor": "#c9b458",
  "backgroundColor": "#c9b45830",
  "fillStyle": "solid"
}
{
  "id": "txt-1",
  "type": "text",
  "x": 110,  // 100 + 10 padding
  "y": 125,  // Vertically centered
  "width": 180,  // 200 - 20 padding
  "text": "Goal Name Here",
  "fontSize": 44,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "box-1"
}
```

**Common mistakes** (these cause blank boxes):
- ❌ Missing `containerId` in text → text floats separately
- ❌ Missing `boundElements` in container → binding broken
- ❌ Mismatched IDs between container and text
- ❌ Text positioned outside container bounds
- ❌ Text width > container width

**Canvas background**: Use `transparent` or `#ffffff` (white) - NOT dark backgrounds
**Text color**: Use `#1a1a1a` (dark) for high contrast on white canvas

**Arrows must bind to shapes**: Set `startBinding: {elementId: "shape-id", focus: 0, gap: 10}` so arrows move with elements. Arrows connect: Goal→Project, Project→Task.

### Phase 5: Write, Verify, and Report

1. **Write file**: Use Write tool → `/home/nic/src/writing/current-tasks.excalidraw` (repo root, NOT data/)
   - **Path**: MUST be repo root (`/home/nic/src/writing/`), NOT `data/` subdirectory
   - **Rule**: Only bmem-compliant markdown belongs in `data/`
<<<<<<< Updated upstream
   - **Reason**: Excalidraw files are binary JSON artifacts, not knowledge base content
   - **Filename**: `current-tasks.excalidraw` (replaces any previous version)

2. **CRITICAL VERIFICATION** (DO NOT SKIP):
   - Read back the generated JSON file
   - Sample 3-5 random elements to verify text binding:
     - Find a container element → verify it has `boundElements: [{id: "text-X", type: "text"}]`
     - Find corresponding text element with id="text-X" → verify `containerId` matches container id
     - Verify text `x`, `y` are inside container bounds
     - Verify text `width` < container `width`
   - If ANY verification fails → HALT and fix the JSON before reporting success
   - **Do NOT claim success based only on element count** - text binding MUST be verified

3. **Report summary**:
   - **Total tasks discovered**: Breakdown by status (active, blocked, queued, completed, inbox)
   - **Projects identified**: From bmem + task metadata
   - **Goals mapped**: From bmem
   - **Relationship stats**:
     - Tasks connected to projects: X/Y
     - Projects connected to goals: X/Y
     - Orphaned tasks (no project): List them
     - Orphaned projects (no goal): List them
   - **Project health**: For each project, show:
     - Last 2-3 completed tasks (recent progress indicator)
     - Outstanding tasks count (active/blocked/queued)
     - Visual balance: Are projects evenly distributed or clustered?
   - **Spatial layout**: Confirm arrow overlap minimized via 360° positioning
   - **Skipped/malformed tasks**: Count and reason
   - **File location**: `/home/nic/src/writing/current-tasks.excalidraw` (repo root)
   - **Design notes**: "Comprehensive goal→project→task map on white canvas, 360° positioning to prevent arrow overlap, recent completed tasks shown per project"
=======
   - **Reason**: Excalidraw files are binary artifacts, not knowledge base content

2. **MANDATORY VERIFICATION** (DO NOT SKIP - TEXT BINDING FAILURE IS THE #1 ISSUE):

   **Read back the generated JSON file and verify text binding on a sample:**

   a. Sample 5 random container elements (goals, projects, tasks)
   b. For EACH sampled container, verify:
      - ✅ Container has `boundElements` array with text reference
      - ✅ Corresponding text element exists with matching `containerId`
      - ✅ Text element has `textAlign: "center"` and `verticalAlign: "middle"`
      - ✅ Text element has appropriate `fontSize` for hierarchy
      - ✅ Text element has `fontFamily: 1` (Virgil)
      - ✅ Text content is not empty

   c. If ANY verification fails:
      - ❌ HALT immediately
      - ❌ Report which binding failed and why
      - ❌ DO NOT report success to user
      - ❌ Fix the generation code and regenerate

   d. Sample verification output should look like:
      ```
      ✅ Container "goal-1" → text "txt-goal-1" bound correctly
      ✅ Container "project-3" → text "txt-proj-3" bound correctly
      ✅ Container "task-15" → text "txt-task-15" bound correctly
      ✅ All 5 samples verified - text binding working
      ```

3. **Report summary**:
   - Total tasks discovered (breakdown: active, blocked, queued, completed, inbox)
   - Projects identified from bmem
   - Goals mapped
   - Skipped/malformed tasks (count and reason)
   - File location: `current-tasks.excalidraw` (repo root)
   - Verification status: "Text binding verified on 5 sample elements"
   - Note: "Dashboard designed following excalidraw visual design principles"
>>>>>>> Stashed changes

## Error Handling

**Fail-fast (halt immediately)**:
- bmem skill unavailable or fails
- excalidraw skill unavailable or fails
- Cannot write to repo root
- Too many malformed tasks (>50% invalid)
- **Text binding verification fails** - any container missing text or text unbound
- **Visual check fails** - blank boxes in output (indicates text binding broken)

**Graceful degradation**:
- No tasks found → Create dashboard with "No tasks" message
- No bmem projects found → Use "uncategorized" bucket
- Some tasks malformed → Skip, report count, continue
- Missing optional task fields → Use defaults (priority=3, project="uncategorized")

**Troubleshooting text binding failures**:

If boxes appear blank (no text visible):
1. **Check container has boundElements**:
   ```json
   "boundElements": [{"id": "text-123", "type": "text"}]
   ```
2. **Check text has containerId**:
   ```json
   "containerId": "container-456"
   ```
3. **Verify IDs match** - container's boundElements[].id MUST equal text's id
4. **Check text positioning** - text x/y must be INSIDE container bounds
5. **Check text width** - must be less than container width (typically -20px for padding)
6. **Verify all required properties** exist on both elements

**Example of correctly bound text-in-container**:
See Phase 4 example JSON above - copy that pattern exactly.

## Quality Checklist

Before completing, verify:

**Visual hierarchy**:
- [ ] Goals (XL: 40-48px) > Projects (L: 24-32px) > Active tasks (M: 16-20px) > Completed (S: 12-14px)
- [ ] Outstanding tasks are LARGE and PROMINENT (bold colors)
- [ ] Completed tasks are SMALL and DE-EMPHASIZED (gray, 60% opacity)
- [ ] Clear 4-level size distinction

**Relationship mapping**:
- [ ] ALL tasks connected to a project (or marked as orphaned)
- [ ] ALL projects connected to a goal (or marked as orphaned)
- [ ] Arrows show: Goal→Project, Project→Task (directional, bound to shapes)
- [ ] Recent completed tasks (2-3 per project) visible for context
- [ ] Orphaned tasks/projects visually distinct (different color or position)

**Layout & spacing (CRITICAL)**:
- [ ] 360° positioning used (tasks distributed around projects, not just below)
- [ ] Minimum 100-150px between task nodes (prevents arrow crossings)
- [ ] 80-120px between project clusters
- [ ] 150-200px between goal zones
- [ ] Arrows do NOT run through other elements (spatial planning successful)
- [ ] Curved arrows for organic feel

**Text & grouping** (CRITICAL - CHECK ACTUAL FILE):
- [ ] EVERY container has `boundElements: [{id: "...", type: "text"}]`
- [ ] EVERY text has `containerId` matching its container
- [ ] Text positioned INSIDE containers (x/y within container bounds)
- [ ] Text width < container width (typically container width - 20px)
- [ ] IDs match exactly between container.boundElements[].id and text.containerId
- [ ] **VISUAL CHECK**: Open current-tasks.excalidraw and verify ALL boxes show text
- [ ] **FAILURE CONDITION**: If any box is blank → HALT and fix text binding

**Color & contrast**:
- [ ] White/transparent canvas background
- [ ] Dark text (`#1a1a1a`) for contrast
- [ ] Theme colors for boxes (gold/green/blue/orange/red)
- [ ] Status-based coloring (blocked=red, active=green, queued=orange)

**Professional polish**:
- [ ] All arrows bound to shapes
- [ ] Consistent font sizes by hierarchy
- [ ] Visually striking and informative

## Success Criteria

Dashboard is successful when user can answer at a glance:
1. **What needs my attention?** (prominent outstanding tasks, clearly visible)
2. **What's blocked?** (red blocked tasks with clear indicators)
3. **Strategic alignment?** (EVERY task → project → goal, orphans visible)
4. **Project balance?** (Can see which projects are neglected vs. active)
5. **Goal coverage?** (Which goals have active work vs. being ignored?)
6. **Recent progress?** (Last 2-3 completed tasks per project for context)
7. **Orphaned work?** (Tasks/projects not connected to strategy)
8. **Spatial clarity?** (No arrow overlap, easy to trace relationships)

**The dashboard should be beautiful AND informative** - not one at expense of the other.
