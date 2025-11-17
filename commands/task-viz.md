# Task Visualization Dashboard

Generate a visual dashboard of all tasks across repositories.

## Workflow

You are tasked with creating a visual task dashboard in Excalidraw format.

### 1. Discover Task Files

Use the Glob tool to find all task files:
- Pattern: `data/tasks/inbox/*.md`
- Search current repository first
- If time permits, search `~/src/*/data/tasks/inbox/*.md` for cross-repo view

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

### 3. Group and Structure Data

1. Group tasks by `project`
2. Within each project, sort by:
   - Priority (0 first, 3 last)
   - Then by status (active, blocked, queued, completed)
3. Create structured JSON for the visualization script:

```json
{
  "projects": [
    {
      "name": "framework",
      "tasks": [
        {
          "id": "task-001",
          "title": "Active framework task",
          "status": "active",
          "priority": 1,
          "blockers": []
        }
      ]
    }
  ]
}
```

### 4. Generate Visualization

1. Write the structured JSON to `/tmp/task-viz-data.json`
2. Use Bash tool to run the generation script:
   ```bash
   python ~/.claude/skills/framework/scripts/generate_task_viz.py /tmp/task-viz-data.json ~/current-tasks.excalidraw
   ```
3. Verify the output file was created

### 5. Report Results

Provide a summary:
- Total tasks found
- Breakdown by status (active, blocked, queued, completed)
- Breakdown by project
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
