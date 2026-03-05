---
title: Graph Initiative — Iteration 1 Results
type: qa
status: active
created: 2026-03-04
project: overwhelm-dashboard
---

# Graph Initiative — Iteration 1 Evaluation

**Date**: 2026-03-04
**Changes**: Focus scope default + ego network focus mode
**Commit**: 1763f245

## What Changed

1. Default scope changed from "All" (3,992 nodes → ~650 after filter) to "Focus" (~622 nodes pre-filtered to active/recent work)
2. Status summary replaced generic count with "585 active · 18 in-progress · 7 blocked · 12 waiting | 1127 links"
3. New ego network focus mode: click node → "Focus" button → 579/624 nodes hidden, 45 visible → auto-zoom
4. "← Full view" button exits focus mode, restores all nodes

## Functional Verification

- **Node count**: 624 rendered ✓
- **Ego network on click**: Detail panel opens, "Focus" button present ✓
- **Focus mode**: 579 hidden (display="none"), 45 visible ✓ (93% reduction from 624)
- **Back button**: Restores all 624 nodes, hides back button ✓
- **Focus label**: Shows selected node name ✓

One issue noted: auto-zoom to fit ego network fires but does not visibly re-center on the 45-node neighborhood — the transform changes but the nodes remain in the lower-right region. Likely cause: the FA2 layout has these nodes genuinely in that quadrant, and the zoom is working but the nodes are spread widely enough that the scale doesn't dramatically improve. Not a blocker, but degrades D4 score.

## Rubric Scores

### D1: Cognitive Load — 2/5 (was 1/5)

Default view still has 622 nodes — a mass of small boxes with lines. The FA2 precomputed layout creates some cluster structure (nodes group by project), which is a slight improvement over random force layout. But "opening the graph page" still produces sensory overload. The status bar summary is much better ("585 active · 18 in-progress · 7 blocked") but doesn't reduce visual noise.

Marginal improvement: the Focus scope drops from 3,992 to 622, which is better. But 622 is still overwhelming.

### D2: Relationship Clarity — 3/5 (was 2/5)

In focus mode (45 nodes), edge types are clearly distinguishable: blue S-curves for parent hierarchy, red manhattan-routed lines for dependencies, gray dashed for references. Can trace a dependency chain through 3-4 hops. In full view, still lost in density. Score reflects the improved focus-mode experience.

### D3: Priority Visibility — 2/5 (was 2/5)

No change. 95% of nodes still have downstream_weight=0, so node sizes are nearly uniform. Priority is encoded only in border color/width, which is invisible at the zoom level needed to show 622 nodes. Cannot identify P0 items at a glance without zooming in.

### D4: Focus Navigation — 4/5 (was 2/5)

**Core win of this iteration.** Click any node → detail panel → "Focus" button → 45-node ego network. This is the "blinders mode" the user needs. The "← Full view" exit is clean. The transition works. The only knock is the auto-zoom doesn't perfectly center on the visible nodes, so you sometimes need to pan slightly after focusing. Deducting 1 point for this UX friction.

### D5: Actionability — 2/5 (was 1/5)

Marginal improvement. In focus mode, you can understand one task's context (what it blocks, what contains it). But the default view still doesn't tell you "start here." There's no priority-ordered entry point, no "most important 5 tasks" view, no guided starting point. You have to already know what to click.

## Iteration 1 Total: 13/25 — ISSUES

| Dimension                | Baseline | Iter 1    | Delta  |
| ------------------------ | -------- | --------- | ------ |
| D1: Cognitive Load       | 1        | 2         | +1     |
| D2: Relationship Clarity | 2        | 3         | +1     |
| D3: Priority Visibility  | 2        | 2         | 0      |
| D4: Focus Navigation     | 2        | 4         | +2     |
| D5: Actionability        | 1        | 2         | +1     |
| **Total**                | **8/25** | **13/25** | **+5** |

**Verdict: ISSUES** (up from CRITICAL). Real progress on D4. D1 and D5 are the blocking problems.

## Root Cause Analysis

The two biggest remaining gaps (D1=2, D5=2) share the same root cause:

**The default view has no smart reduction.** 622 nodes is still too many. There is no way to open the graph and immediately see "what matters most" without clicking around.

The ego network solves "understand one thing" but doesn't solve "know what to work on next."

## Iteration 2 Plan

**Hypothesis**: If we reduce the default view to ~50-80 nodes using an importance score (priority + status + recency, no DW required), the opening view will feel manageable and actionable.

**Changes to implement**:

1. **Smart "Top N" filter in Python** (`dashboard.py`):
   - New importance score: `priority_score + status_score + recency_score` (no DW needed)
   - `status_score`: blocked=500, in_progress=300, active=100, waiting=50
   - `priority_score`: P0=1000, P1=200, P2=50, P3=10, P4=2
   - `recency_score`: 50 - (days_since_modified * 2), floored at 0
   - Default to "Top 80" mode. Sidebar slider to expand (80/150/all)
   - Always include structural parents of top nodes (epics/projects/goals)
   - Result: ~80-120 nodes instead of 622

2. **Project convex hulls in JS** (`index.html`):
   - Draw translucent background polygons (D3 convex hull) behind project node clusters
   - Color each project with a distinct hue (derived from project name hash)
   - Label each hull with project name
   - Immediately makes cluster structure legible without reading node labels

3. **"Start here" visual signal**:
   - Top 3 nodes by importance score get a pulsing gold ring animation
   - These are the "highest priority right now" items
   - Makes D5 immediate: eyes land on the 3 glowing nodes

**Expected rubric improvements**:

- D1: 2 → 4 (80 nodes + project hulls → manageable, structured)
- D3: 2 → 3 (importance score independent of DW)
- D5: 2 → 4 ("start here" nodes glowing)

Target total after Iter 2: 4+3+3+4+4 = 18/25 — borderline VERIFIED.
