---
title: Graph Initiative — Iteration 2 Results
type: qa
status: active
created: 2026-03-04
project: overwhelm-dashboard
---

# Graph Initiative — Iteration 2 Evaluation

**Date**: 2026-03-04
**Changes**: Top-N importance filter + project convex hulls + spotlight "start here" signal
**Branch**: crew/layleen_55 (dirty)

## What Changed

1. **Top-N importance filter** (`dashboard.py`): New `_importance_score()` function scoring by
   `priority_score + status_score + dw_score + recency_score + depth_bonus`. Default "Top 80" mode
   reduces the default view from 622 → ~103 nodes. Slider in sidebar (25/50/80/120/200). Always
   includes structural parents of top nodes (2 levels up).
2. **Project convex hulls** (`index.html`): D3 `d3.polygonHull()` renders translucent colored
   background polygons behind project node clusters. 8 hulls rendered. Each hull has a distinct
   hue (deterministic from project name hash), 5% fill opacity, 22% stroke opacity, dashed border.
   Hull labels (project name) rendered at hull centroid.
3. **Spotlight "start here" signal** (`index.html` + `task_graph_d3.py`): Top 3 nodes by
   importance score get a pulsing gold ring (`@keyframes spotlight-pulse`) and "★ START HERE"
   label above the node. `spotlight: true` field passed through Python → JS.

## Functional Verification

- **Node count**: 103 rendered (vs 622 in Iter 1 — 83% reduction) ✓
- **Status bar**: "79 active · 17 in-progress · 7 blocked | 212 links" ✓
- **Project hulls**: 8 hull paths + 8 hull labels rendered ✓
- **Spotlight rings**: 3 `.spotlight-ring` elements rendered ✓
- **Spotlight labels**: "★ START HERE" text on top 3 nodes ✓
- **Spotlight nodes**: "Project: Diagnose framework eagerness and graph health",
  "Project: Knowledge architecture -- deep cross-referencing...", "Use relative paths..."
- **Click spotlight node**: Detail panel opens with correct title ✓
- **Focus mode on spotlight**: 55/103 hidden, 48 visible (53% reduction) ✓
- **Back button**: Shows "← Full view", labeled with node name ✓

One bug fixed mid-session: `modified` field is ISO 8601 string, not Unix float — added
`_parse_mod()` helper to handle both formats.

## Rubric Scores

### D1: Cognitive Load — 3/5 (was 2/5)

**+1 improvement.** 103 nodes vs 622 is transformative on paper, but the default auto-zoom
renders nodes at 0.138 scale (nodes ~8px wide) because the FA2 layout places one outlier node
far from the main cluster, forcing the bounding box to include it. The main cluster is visible
with clear hierarchical structure (parent nodes above children), but nothing is readable at the
initial zoom level. One manual scroll/zoom makes the graph fully legible.

The status bar summary ("79 active · 17 in-progress · 7 blocked") is informative and immediately
readable without any interaction.

### D2: Relationship Clarity — 3/5 (same as Iter 1)

No change to edge rendering. Same as Iter 1 — edge types are distinguishable (blue S-curves,
red manhattan, gray dashed) and traceable in focus mode (48-node ego network). Default view
still requires zoom to trace paths. Would score 4 if default zoom were fixed.

### D3: Priority Visibility — 3/5 (was 2/5)

**+1 improvement.** 3 spotlight nodes have gold pulsing rings visible as bright gold dots even
at 0.138 default zoom. But the "★ START HERE" labels are 8px text invisible at that scale. After
one zoom gesture, the spotlights are unambiguous and visually dominant. The project hulls provide
faint cluster coloring but are too subtle (5% opacity) to create clear spatial regions at a
glance.

### D4: Focus Navigation — 4/5 (same as Iter 1)

No regression. Click any node → detail panel → "Focus" button → 48-node ego network. Clean
"← Full view" exit. The auto-zoom in focus mode centers on the neighborhood adequately.
Same minor zoom centering issue (nodes sometimes in lower-right region) as Iter 1.

### D5: Actionability — 3/5 (was 2/5)

**+1 improvement.** The "start here" concept works: 3 top-priority nodes are tagged with gold
rings. After zooming in, the graph immediately answers "what should I work on?" But because the
initial zoom is too far back, the first 30 seconds still requires a manual zoom gesture before
the signal is readable. The status bar tells you "7 blocked" but doesn't name the spotlight nodes
directly.

## Iteration 2 Total: 16/25 — ISSUES

| Dimension                | Iter 1 | Iter 2 | Delta  |
| ------------------------ | ------ | ------ | ------ |
| D1: Cognitive Load       | 2      | 3      | +1     |
| D2: Relationship Clarity | 3      | 3      | 0      |
| D3: Priority Visibility  | 2      | 3      | +1     |
| D4: Focus Navigation     | 4      | 4      | 0      |
| D5: Actionability        | 2      | 3      | +1     |
| **Total**                | **13** | **16** | **+3** |

**Verdict: ISSUES** (up from 13/25). Target was 18/25; we got 16/25. Good progress but one
critical root cause is blocking further gains on D1, D3, and D5.

## Root Cause Analysis

All three stalled dimensions (D1, D3, D5) share the same root cause:

**The default auto-zoom includes outlier nodes.** `autoZoomToFit` computes a bounding box from
ALL nodes with layout data. One node in the FA2 layout is placed far from the main cluster.
This forces the scale to 0.138, making the entire graph unreadable on first glance. The spotlight
rings and "★ START HERE" labels exist but are invisible at that scale.

Fix: Compute zoom bounding box from the 90th percentile of node positions, excluding outliers.
This single change would make the default view immediately readable.

Secondary: Project hulls are too subtle (5% fill / 22% stroke). They provide structure but don't
create the "this is clearly a cluster" gestalt that would help D1.

## Iteration 3 Plan

**Hypothesis**: If the default zoom shows the main cluster at a readable scale (not 0.138), the
spotlight "★ START HERE" nodes will be immediately visible, making D1, D3, and D5 all ≥ 4.

**Changes to implement**:

1. **Percentile-based auto-zoom** (`index.html`): Replace the full-extent bounding box in
   `autoZoomToFit` (when called from `applyLayout`) with a 90th percentile bounds computation
   that excludes outlier nodes. Outlier nodes are still rendered; they just don't dictate the
   initial zoom level.
   - Expected: D1 3→4, D3 3→4, D5 3→4

2. **"Start here" summary in status bar** (`dashboard.py`): Append the top 3 spotlight node
   titles to the status bar caption, e.g. "★ Start: Project: Diagnose framework eagerness... +2".
   Gives the actionable signal in plain text without requiring any interaction.
   - Expected: D5 3→4 (or 4→5 with zoom fix)

3. **Critical path hover highlight** (`index.html`): On node hover (or shift-click), highlight
   the full dependency chain — both ancestors (things this is blocked by) and descendants (things
   this is blocking). Use a bright red path overlay distinct from the normal edge rendering.
   - Expected: D2 3→4

**Expected rubric after Iter 3**: D1=4, D2=4, D3=4, D4=4, D5=4 → **20/25 — VERIFIED**
