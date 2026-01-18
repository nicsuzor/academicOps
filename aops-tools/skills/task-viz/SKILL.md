---
name: task-viz
description: Generate visual mind-map of bd issues using force-directed layout via excalidraw
---

# Task Visualization

Generate a force-directed visualization of bd issues as an excalidraw file.

## Usage

```bash
uv run python $AOPS/aops-tools/skills/task-viz/scripts/task_viz_bd.py output.excalidraw [--include-closed] [--prefix PREFIX]
```

## Options

- `--include-closed`: Include closed issues (excluded by default)
- `--prefix PREFIX`: Filter issues by ID prefix (e.g., `ns-`, `aops-`)

## Output

- Epics: Large green ellipses
- Tasks/bugs: Rectangles colored by priority (P0=red, P1=orange, P2=yellow, P3=gray)
- Arrows: Parent-child relationships
- Legend: Color key in corner
- Timestamp: Generation time

## Example

```bash
# Visualize all ns- prefixed issues
uv run python $AOPS/aops-tools/skills/task-viz/scripts/task_viz_bd.py ~/writing/current-tasks.excalidraw --prefix ns-

# Open result
xdg-open ~/writing/current-tasks.excalidraw
```
