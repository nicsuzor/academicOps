# Task Visualization Dashboard

Generate a visual mind-map of tasks, projects, and goals across repositories.

## Workflow

You are tasked with creating a visual task dashboard in Excalidraw format. The goal is to help the user quickly understand: where everything fits, what needs to be done, what we're waiting on, what sequencing/blockers exist, and how things are prioritised and aligned.

### 1. Discover Task Files and Projects

Use the Glob tool to find all task files:
- Pattern: `data/tasks/inbox/*.md`
- Search current repository first
- If time permits, search `~/src/*/data/tasks/inbox/*.md` for cross-repo view

Use bmem to discover projects and goals:
- Query for project entities to understand strategic context
- Map projects to their parent goals
- Identify projects with no tasks (why not? progress indicator)

### 2. Read and Parse Tasks

For each task file found:
1. Use Read tool to get the file content
2. Parse YAML frontmatter to extract:
   - `title` (required)
   - `status` (required: active, blocked, queued, completed)
   - `priority` (required: 0-3, where 0=highest)
   - `project` (optional, default to "uncategorized")
   - `blockers` (optional list)
3. Fail-fast if required fields are missing (per AXIOMS #5)

### 3. Design Visual Layout

Based on the data gathered, design a mind-map that shows:

**Visual Hierarchy**:
- **Goals** at the top level (strategic context from bmem)
- **Projects** connected to their goals
- **Outstanding tasks** (active, blocked, queued) in PROMINENT display
  - Larger font, bold, positioned prominently
  - Show blockers clearly for blocked tasks
- **Completed tasks** in SMALL font attached to projects
  - Show where we've been, but don't dominate visual space
- **Projects with no tasks** explicitly indicated
  - This is an important signal: are we making progress? Why no tasks?

**Visual Encoding**:
- Color by status: active (blue), blocked (red), queued (yellow), completed (green/gray)
- Size by importance: outstanding tasks larger, completed tasks smaller
- Position: strategic priorities higher/more central
- Connections: arrows from goals → projects → tasks
- Blockers: explicit visual indication (icon, color, label)

### 4. Generate Excalidraw JSON

Create the Excalidraw JSON structure directly:
1. Define elements array with:
   - Rectangles/ellipses for goals, projects, tasks
   - Text elements for labels
   - Arrows for relationships (goal→project, project→task, task→blocker)
2. Apply visual encodings decided in step 3
3. Layout elements spatially (top-to-bottom hierarchy, grouped by project)
4. Use Excalidraw element properties:
   - `type`: "rectangle", "ellipse", "arrow", "text"
   - `strokeColor`, `backgroundColor`, `fillStyle`
   - `fontSize`, `fontFamily`
   - `x`, `y`, `width`, `height`
   - `startBinding`, `endBinding` for arrows

### 5. Write and Report

1. Use Write tool to create `~/current-tasks.excalidraw` with the generated JSON
2. Verify the output file was created
3. Provide a summary:
   - Total tasks found (breakdown by status)
   - Projects discovered (with/without tasks)
   - Goals mapped
   - Location of generated dashboard: `~/current-tasks.excalidraw`

## Error Handling

**Fail-fast cases** (halt with clear error):
- Task file with malformed YAML frontmatter
- Task missing required fields (title, status, priority)
- Invalid status value (not: active, blocked, queued, completed)
- Visualization script execution fails

**Graceful degradation**:
- Missing optional fields (project, blockers) → Use defaults
- No task files found → Create empty dashboard with message
- Some tasks malformed → Skip those, report count, continue with valid tasks

## Expected Output

User should receive:
1. Summary of tasks discovered
2. Confirmation that dashboard was generated
3. Path to open: `~/current-tasks.excalidraw`
4. Any warnings about skipped/malformed tasks
