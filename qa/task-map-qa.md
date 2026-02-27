---
title: "QA Plan: Task Map Visualization"
type: qa
status: active
tags: [qa, task-map, overwhelm-dashboard]
created: 2026-02-23
epic: task-map-96a5b7b5
spec: specs/task-map.md
---

# QA Plan: Task Map Visualization

## Overview

This QA plan covers the task map improvements specified in [[specs/task-map.md]] and tracked under epic [[task-map-96a5b7b5]]. It is designed to be executed by a QA agent after the developer completes each task, and also as a comprehensive end-to-end evaluation after the full epic is complete.

The QA plan goes beyond checking that each individual task's acceptance test passes. It evaluates whether the task map, as a whole, meets the user's actual needs — orientation, legibility, bottleneck identification, and focus support for an ADHD academic with 500+ tasks.

## Prerequisites

- Dashboard running: `cd $AOPS && uv run streamlit run lib/overwhelm/dashboard.py`
- Fresh `graph.json`: `aops graph -o graph.json` or `aops reindex`
- Browser with devtools available (for performance checks)
- At least ~100 nodes in the reachable graph (representative of production data)

## Per-Task QA

Execute the relevant section after each task is marked as developer-complete.

### QA-1: Visual hierarchy (task-map-094ea270)

**Precondition**: Node sizing and shape rendering implemented.

| #   | Check                                       | Method                                                                                  | Pass criteria                                                                        |
| --- | ------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 1.1 | Goals are visually largest                  | Open dashboard, look at interactive graph at default zoom                               | Goal nodes are obviously larger than project nodes, which are larger than task nodes |
| 1.2 | Node size correlates with downstream_weight | Compare a node with known high downstream_weight (check graph.json) against a leaf task | High-weight node is noticeably larger                                                |
| 1.3 | Node shapes differentiate types             | Identify at least 3 distinct shapes on screen                                           | Goals, projects/epics, and leaf tasks use different shapes                           |
| 1.4 | Shape rendering is clean at all zoom levels | Zoom in and out through full range                                                      | Shapes don't degrade to blobs or render artifacts at any zoom level                  |
| 1.5 | Size doesn't cause overlap at default zoom  | Default zoom, check if large nodes overlap/obscure neighbors                            | Repulsion force keeps nodes separated; no permanent overlap of important nodes       |
| 1.6 | Performance with sizing                     | Open devtools, check frame rate during layout animation                                 | Maintains ≥30fps during force simulation with ~500 nodes                             |

### QA-2: Meaningful labels (task-map-51f509c0)

**Precondition**: Label source changed to `title`, progressive reveal implemented.

| #   | Check                            | Method                                                                             | Pass criteria                                                                                                  |
| --- | -------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 2.1 | Labels show titles not IDs       | Find a node whose previous label was its ID (e.g., `overwhelm-dashboard-e993b43b`) | Now shows human-readable title                                                                                 |
| 2.2 | No ID fallback visible           | Scan all visible labels at various zoom levels                                     | No labels consist of hash-style IDs like `xxxx-xxxxxxxx`                                                       |
| 2.3 | Progressive reveal — zoomed out  | Zoom out to see full graph                                                         | Only goal and project labels visible; task labels hidden                                                       |
| 2.4 | Progressive reveal — zoomed in   | Zoom into a specific cluster                                                       | Task-level labels appear as you zoom in                                                                        |
| 2.5 | No label overlap at default zoom | Default zoom, inspect label rendering                                              | Project-level labels are readable without overlapping each other                                               |
| 2.6 | Label truncation is reasonable   | Find a node with a long title (50+ chars)                                          | Title is either fully displayed or truncated with ellipsis at a sensible point (not mid-word, not at 30 chars) |

### QA-3: Legend strip (task-map-5e484bd8)

**Precondition**: Legend rendered near graph.

| #   | Check                                   | Method                                  | Pass criteria                                                                                 |
| --- | --------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------- |
| 3.1 | Legend is visible without interaction   | Open dashboard, scroll to graph         | Legend is visible without clicking any expander or toggle                                     |
| 3.2 | Legend explains colors                  | Read legend                             | All status colors shown with labels match what's rendered                                     |
| 3.3 | Legend explains sizes                   | Read legend                             | Size encoding (downstream weight) is explained                                                |
| 3.4 | Legend explains shapes (if implemented) | Read legend                             | Shape→type mapping shown if shapes are differentiated                                         |
| 3.5 | Legend is compact                       | Measure visual footprint                | Takes up ≤2 lines; doesn't push graph below the fold                                          |
| 3.6 | Legend matches rendering                | Compare legend to actual graph encoding | No mismatches (e.g., legend says purple=review but graph renders review as a different color) |

### QA-4: Blocker visibility (task-map-5d2f6a52)

**Precondition**: Blocker emphasis and downstream info implemented.

| #   | Check                                  | Method                                                                        | Pass criteria                                                                                             |
| --- | -------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 4.1 | High-impact blockers stand out         | Open graph, scan for red nodes                                                | Blocked nodes with high downstream_weight are visually alarming (large + red) — immediately catch the eye |
| 4.2 | Low-impact blockers are less prominent | Compare a blocked leaf (no dependents) to a blocked node with many dependents | Size difference makes impact obvious                                                                      |
| 4.3 | Click/hover shows downstream count     | Interact with a blocked node                                                  | Shows downstream impact: count or highlighted subgraph                                                    |
| 4.4 | Dependency edges are distinct          | Look at edges connected to a blocked node                                     | Dependency edges visually different from parent/hierarchy edges                                           |
| 4.5 | 5-second identification test           | Fresh page load, time yourself                                                | Can identify the single highest-impact blocker within 5 seconds                                           |

### QA-5: Recency heatmap (task-map-aa480699)

**Precondition**: Recency emphasis/fade implemented.

| #   | Check                           | Method                                            | Pass criteria                                            |
| --- | ------------------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| 5.1 | Recently-modified nodes glow    | Identify a node modified today (check file mtime) | Node has visible emphasis (glow, bright color, pulse)    |
| 5.2 | Stale nodes are faded           | Identify a node untouched for 2+ weeks            | Node is at reduced opacity or desaturated                |
| 5.3 | Fresh vs stale contrast         | Compare side by side                              | The visual difference is immediately obvious, not subtle |
| 5.4 | Modified timestamps in data     | Check graph.json for `modified` field on nodes    | Timestamps are present and accurate (match file mtimes)  |
| 5.5 | Heat shifts correctly over time | Modify a previously-stale task, re-index, reload  | The node's visual emphasis updates to reflect recency    |

### QA-6: Edge differentiation (task-map-67008a98)

**Precondition**: Edge styling per type implemented.

| #   | Check                             | Method                                             | Pass criteria                                             |
| --- | --------------------------------- | -------------------------------------------------- | --------------------------------------------------------- |
| 6.1 | Parent edges are distinct         | Find a parent→child relationship                   | Edge has different color/weight than dependency edges     |
| 6.2 | Dependency edges are prominent    | Find a `depends_on` relationship                   | Red/orange, thicker than parent edges                     |
| 6.3 | Soft dependency edges are lighter | Find a `soft_depends_on` relationship              | Visually lighter/dashed compared to hard dependencies     |
| 6.4 | Can trace a dependency chain      | Follow dependency edges visually through the graph | Chain is traceable without confusing it with hierarchy    |
| 6.5 | Edge type data present            | Check graph.json edges                             | Each edge has a `type` or equivalent classification field |

### QA-7: Project focus filter (task-map-32e9a670)

**Precondition**: Project selector dropdown implemented.

| #   | Check                              | Method                                     | Pass criteria                                                              |
| --- | ---------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------- |
| 7.1 | Dropdown lists all projects        | Open the project selector                  | All top-level projects from graph.json appear as options                   |
| 7.2 | Selecting a project filters        | Choose "overwhelm-dashboard"               | Only dashboard-related nodes visible                                       |
| 7.3 | Cross-project dependencies shown   | If filtered project has cross-project deps | Dependencies from other projects still visible (with visual distinction)   |
| 7.4 | Labels fully visible in focus mode | Single-project view                        | All node labels readable, no overlap (small enough node count)             |
| 7.5 | "All projects" returns to default  | Select "All" option                        | Full graph reappears                                                       |
| 7.6 | Layout re-adjusts                  | Switch between all and single project      | Nodes re-layout to fill available space (not a tiny cluster in the corner) |

### QA-8: Click-to-detail panel (task-map-a8d2ec1c)

**Precondition**: Detail panel and neighborhood highlighting implemented.

| #   | Check                       | Method                                  | Pass criteria                                                            |
| --- | --------------------------- | --------------------------------------- | ------------------------------------------------------------------------ |
| 8.1 | Click shows detail panel    | Click any node                          | Panel appears with full title, status, priority, assignee                |
| 8.2 | Breadcrumb shows hierarchy  | Click a task-level node                 | Breadcrumb shows: Goal → Project → Epic → Task                           |
| 8.3 | Children listed with status | Click a project or epic node            | Children shown with status badges                                        |
| 8.4 | Dependencies shown          | Click a node with `depends_on`          | Dependencies listed: "blocks X" / "blocked by Y"                         |
| 8.5 | Obsidian link works         | Click the file link in the detail panel | Opens the correct file in Obsidian (or provides correct URI)             |
| 8.6 | Neighborhood highlighted    | Click a node                            | Clicked node + direct connections brighten; everything else dims         |
| 8.7 | Clear selection             | Click empty space                       | Selection clears, all nodes return to normal opacity, detail panel hides |
| 8.8 | Panel shows within 1 second | Time from click to panel render         | ≤1 second                                                                |

### QA-BUG: Completed task leak (task-map-d8f2052e)

**Precondition**: Bug investigated and fixed.

| #   | Check                              | Method                                                         | Pass criteria                                                               |
| --- | ---------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------- |
| B.1 | No unexplained green nodes         | Open reachable view, identify all green (done) nodes           | Every green node has a traceable path to an active leaf                     |
| B.2 | Verify with graph.json             | For each green node, check its edges in graph.json             | Can manually trace upstream path from an active leaf through the green node |
| B.3 | Wikilinks don't create false paths | Check if any green nodes are reachable only via wikilink edges | Wikilinks should not count as upstream paths in filter_reachable            |
| B.4 | Fresh index matches                | Run `aops reindex`, reload dashboard                           | Green nodes match current task statuses (no stale data)                     |

## Comprehensive End-to-End Evaluation

Execute after the full epic is complete. These tests evaluate the task map holistically against the user's actual needs.

### E2E-1: The 3-Second Orientation Test

**Setup**: Close the dashboard. Wait 1 minute (simulate returning to work). Open the dashboard.

| #    | Question                             | Method                                          | Pass criteria                                           |
| ---- | ------------------------------------ | ----------------------------------------------- | ------------------------------------------------------- |
| E1.1 | "How many fronts am I fighting on?"  | Glance at graph, count distinct visual clusters | Can count project clusters within 3 seconds             |
| E1.2 | "Which project has the most work?"   | Identify the visually largest/densest cluster   | Obvious which cluster is biggest without reading labels |
| E1.3 | "Is anything blocked?"               | Scan for red/alarming nodes                     | Blocked items visible at a glance without zooming       |
| E1.4 | "Where was work happening recently?" | Look for visual emphasis (glow/brightness)      | Can point to 2-3 active areas without reading           |

### E2E-2: The Focus Transition Test

**Setup**: Full graph visible with all projects.

| #    | Step                                   | Pass criteria                                                            |
| ---- | -------------------------------------- | ------------------------------------------------------------------------ |
| E2.1 | Decide to work on one project          | Can identify the project cluster visually                                |
| E2.2 | Activate project focus filter          | Graph smoothly transitions to single-project view                        |
| E2.3 | Identify next task within that project | Can read all labels, see what's blocked, pick a task — within 10 seconds |
| E2.4 | Click the chosen task                  | Detail panel gives enough context to start working                       |
| E2.5 | Return to full view                    | Deactivating filter restores full graph without losing orientation       |

### E2E-3: The Bottleneck Discovery Test

**Setup**: Ensure at least 2 blocked tasks exist in the PKB with different downstream_weight values.

| #    | Step                            | Pass criteria                                                      |
| ---- | ------------------------------- | ------------------------------------------------------------------ |
| E3.1 | Identify highest-impact blocker | Visually obvious without clicking (size + color)                   |
| E3.2 | Understand what it's blocking   | Click reveals downstream count or highlights subgraph              |
| E3.3 | Compare to lower-impact blocker | Visual difference in urgency is clear (bigger vs smaller red node) |
| E3.4 | Trace the dependency chain      | Can follow dependency edges from blocker to blocked tasks          |

### E2E-4: The "New User" Legibility Test

**Setup**: Show the dashboard to someone unfamiliar with it (or evaluate as if you are unfamiliar).

| #    | Check                       | Pass criteria                                                          |
| ---- | --------------------------- | ---------------------------------------------------------------------- |
| E4.1 | Color meaning is clear      | Legend + visual encoding is self-explanatory within 10 seconds         |
| E4.2 | Size meaning is clear       | Obvious that larger nodes are "more important"                         |
| E4.3 | Interaction is discoverable | Hovering or clicking naturally produces useful feedback                |
| E4.4 | No jargon in labels         | All visible text is human-readable, not database IDs or internal codes |

### E2E-5: The Regression Check

Ensure improvements haven't broken existing functionality.

| #    | Check                     | Pass criteria                                                     |
| ---- | ------------------------- | ----------------------------------------------------------------- |
| E5.1 | SVG tab still works       | SVG graph renders with pan/zoom                                   |
| E5.2 | Layout modes work         | All 4 layout modes (td, lr, radial, force) render without errors  |
| E5.3 | Type filter works         | Filtering by type in the expander removes/adds nodes correctly    |
| E5.4 | Hide Orphans works        | Toggle removes disconnected nodes                                 |
| E5.5 | Knowledge Base view works | Switching to KB view renders notes/wikilinks graph                |
| E5.6 | Performance               | Graph loads within 2 seconds; maintains ≥30fps during interaction |
| E5.7 | Graph toggle works        | Hide/Show button collapses and expands the graph section          |
| E5.8 | No console errors         | Browser devtools console is clean (no JS errors from force-graph) |

### E2E-6: The ADHD Accommodation Check

Evaluate against the design principles from the spec.

| #    | Principle                 | Check                                            | Pass criteria                                              |
| ---- | ------------------------- | ------------------------------------------------ | ---------------------------------------------------------- |
| E6.1 | Scannable, not studyable  | Structure visible at a glance                    | Can get oriented without reading any text                  |
| E6.2 | Active work dominates     | Completed/stale nodes recede                     | Eye is drawn to active, recent work first                  |
| E6.3 | No flat displays at scale | Visual hierarchy exists                          | Size, shape, emphasis create clear entry points            |
| E6.4 | Focus transition support  | Can go from overview to single-project           | Project filter narrows attention without losing context    |
| E6.5 | Directive, not passive    | Graph communicates "here's what needs attention" | Blockers, recency, and size guide the eye to action        |
| E6.6 | No overwhelming density   | Default view is manageable                       | Not a blob of undifferentiated dots; clusters are distinct |

## Reporting

For each QA pass, report:

1. **Task ID** being validated
2. **Check results**: Pass/Fail for each numbered check
3. **Screenshots**: Before/after for visual changes
4. **Regressions**: Any broken existing behavior
5. **New issues**: Anything discovered during QA that isn't covered by existing tasks
6. **User-experience judgment**: Does it actually _feel_ better to use? Not just "does the check pass" but "would this help Nic orient faster?"

File QA results as comments on the relevant task, or as a QA summary in a daily note if doing end-to-end evaluation.
