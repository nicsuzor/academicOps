---
title: Graph/Network Visualization Layouts
type: reference
category: ref
permalink: excalidraw-graph-layouts
description: Three-tier radial pattern for visualizing strategic goals, projects, and tasks in a network layout that emphasizes relationships and hierarchy.
---

# Graph/Network Visualization Layouts

## Three-Tier Radial Pattern (Goal → Project → Task)

**Purpose**: Visualize strategic goals, concrete projects, and actionable tasks in a radial network layout that emphasizes relationships and hierarchy.

### Tier 1 - Central Goal Nodes (Innermost)

- **Placement**: Center of canvas
- **Size**: Largest (200-300px wide rectangles or 150-200px circles)
- **Color**: Saturated, high-contrast (e.g., blue-7 fill, blue-9 stroke)
- **Font**: XL (40-48px), bold if possible
- **Purpose**: High-level strategic objectives
- **Count**: 1-3 goals maximum (too many = unclear focus)

### Tier 2 - Project Nodes (Middle Ring)

- **Placement**: Radially distributed around goal nodes, 200-300px from center
- **Size**: Medium (120-180px rectangles or 80-120px circles)
- **Color**: Mid-saturation, varied by category (e.g., green-6, purple-6, orange-6)
- **Font**: L (24-32px)
- **Purpose**: Concrete projects that advance goals
- **Count**: 3-8 projects per goal (cluster related projects together)
- **Connections**: Direct lines/arrows FROM goals TO projects

### Tier 3 - Task Nodes (Outer Ring)

- **Placement**: Around their parent projects, 150-250px from project nodes
- **Size**: Smallest (80-120px rectangles or 40-60px circles)
- **Color**: Desaturated or lighter (e.g., same family as parent project but shade 3-4)
- **Font**: M (16-20px)
- **Purpose**: Specific actionable tasks
- **Visual state indicators**:
  - ✅ Completed tasks: Green fill or checkmark, lower opacity (60-70%)
  - ⚪ Outstanding tasks: Full opacity, normal colors
  - 🔴 Blocked/critical: Red accent or border
- **Count**: 2-6 tasks per project (too many = create sub-projects)
- **Connections**: Lines FROM projects TO tasks

## Clustering Strategy

- **Group related projects spatially**: Same sector around goal = related theme
- **Create visual zones**: Use subtle background frames (20-30% opacity) to group clusters
- **Maintain breathing room**: 60-100px minimum between unrelated project clusters
- **Directional flow**: Position projects clockwise by priority or temporal sequence

## Connection Styling

- **Goal → Project arrows**: Thick (3-4px), solid, directional
- **Project → Task arrows**: Thin (1-2px), solid or dotted for completed tasks
- **Color inheritance**: Match arrow color to source node for clarity
- **Avoid crossing**: Rearrange nodes to minimize arrow intersections

## Radial Layout Tips

- **Use polar thinking**: Think in degrees/sectors rather than grid alignment
- **Balance visual weight**: Distribute projects evenly around goals (avoid one-sided clustering)
- **Vary radius**: Projects at different distances = different priority/urgency
- **Create rhythm**: Alternate between dense and sparse sectors for visual breathing

## Example Layout (Conceptual)

```
                    [Task] [Task]
                       ↑
         [Task] ← [Project-A] → [Task]
              ↖       ↑
                 [GOAL] ← (center, largest)
              ↗       ↓
    [Project-B] → [Task] [Task]
         ↓
      [Task]
```

## Anti-Patterns to Avoid

- ❌ Too many goals (loses focus, creates chaos)
- ❌ Perfectly symmetric layout (looks rigid, template-y)
- ❌ All projects same size (loses hierarchy)
- ❌ Linear/tree layout when radial works better (wastes space)
- ❌ Crossing arrows everywhere (rearrange nodes!)

## When to Use This Pattern

✅ **Good for**:
- Portfolio/project overview dashboards
- Strategic planning visualizations
- Personal task/goal tracking
- Research program structure (goals = research themes, projects = papers/grants, tasks = milestones)

❌ **Not suitable for**:
- Sequential processes (use left-to-right flow instead)
- Deep hierarchies (5+ levels → use tree diagram)
