# Task Visualization Dashboard

Generate a visual mind-map of tasks, projects, and goals using the automated layout script.

**Process**:
1. Run the task visualization script:
   ```bash
   uv run python $AOPS/skills/tasks/scripts/task_viz.py $ACA_DATA current-tasks.excalidraw
   ```
2. Open the generated visualization:
   ```bash
   open current-tasks.excalidraw
   ```
3. **If manual refinement is needed** after the script runs, invoke the `excalidraw` skill: `Skill(skill="excalidraw")`

**What the script does**:
- Reads tasks from `$ACA_DATA/tasks/inbox/`
- Reads projects from `$ACA_DATA/projects/`
- Reads goals from `$ACA_DATA/goals/`
- Computes force-directed layout using networkx
- Generates complete excalidraw JSON file with:
  - Goals (large ellipses, muted gold)
  - Projects (medium rectangles, varied colors)
  - Tasks (small rectangles, priority-based colors)
  - Arrows showing relationships

**Visual features**:
- Force-directed layout prevents overlap
- Color-coded by goal/priority (muted terminal theme)
- Size hierarchy: Goals (largest) > Projects > Tasks
- Curved arrows showing connections
- Timestamp in corner

**When to use excalidraw skill**:
- After script runs, if you need to manually adjust layout
- Add annotations or emphasis
- Change colors or styling
- Reorganize specific sections
