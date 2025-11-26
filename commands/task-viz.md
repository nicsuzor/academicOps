# Task Visualization Dashboard

Launch the task-viz agent to generate a visual mind-map of tasks, projects, and goals.

The agent will:
1. Use bmem skill to understand current projects, goals, and strategic context
2. Use excalidraw skill for professional visual design principles (organic mind-map layout, theme colors, icons)
3. Create a visually striking dashboard showing task hierarchy and status
4. Save to writing repository root as `current-tasks.excalidraw`
5. Open the generated file with `xdg-open` for immediate viewing

**Key features**:
- Organic mind-map layout (NOT rigid hierarchies)
- Muted terminal theme colors (gold, greens, blues)
- Outstanding tasks LARGE and PROMINENT
- Completed tasks SMALL and de-emphasized
- Curved arrows, asymmetric positioning
- Optional Material Symbols icons for status

Launch with Task tool, subagent_type "general-purpose", reading agents/task-viz.md for complete workflow.
