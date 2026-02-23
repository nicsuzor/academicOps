---
title: Task Map Visualization
type: spec
status: active
tags: [spec, dashboard, task-map, visualization, graph, force-graph]
created: 2026-02-23
parent: overwhelm-dashboard
---

# Task Map Visualization

## Giving Effect

- [[scripts/task_graph.py]] — DOT/SVG graph generation from fast-indexer output (Graphviz sfdp)
- [[lib/overwhelm/dashboard.py]] — Streamlit rendering: `render_graph_section()`, `render_force_graph()`, `render_svg_graph()`
- [[skills/task-viz/SKILL.md]] — Task visualization skill (JSON, GraphML, DOT output)
- [[mcp__pkb__get_network_metrics]] — Graph metrics for dashboard
- [[fast-indexer]] — Rust binary that computes graph.json, including `downstream_weight`, `stakeholder_exposure`, parent/child/dependency relationships

## Purpose

The task map is a structural overview of the user's entire work graph. It is one section of the [[Overwhelm Dashboard]], positioned at the top of the page. Its job is to show how work *connects* — the shape of the network, where bottlenecks are, where effort has impact across branches.

The task map is the only part of the dashboard that shows cross-project structure. Other sections handle session context recovery (Your Path, Where You Left Off), prioritized next actions (Project Boxes / UP NEXT), and daily accomplishments. The task map shows the forest.

## The User

Nic is an academic with ADHD who runs parallel workstreams across multiple machines, terminals, and projects. His working memory is limited but his ambition isn't — at any given time there are 500+ incomplete tasks across research, tooling, governance, and teaching. He is building this system for himself because off-the-shelf project management tools don't work for how his brain operates.

The task map exists because Nic's brain can't hold the whole project graph. He needs an external representation that does the cognitive work his working memory can't: showing what connects to what, where work is stuck, and where effort would have the most impact across the network.

## ADHD Design Principles

These constrain all design decisions for the task map:

- **Scannable, not studyable.** The graph must communicate at a glance. If the user has to zoom in and read individual labels to get oriented, it's failed. Structure, color, size, and spatial grouping should carry meaning before any text is read.
- **Active work dominates.** Completed and stale nodes must not compete for visual attention with work that needs action. The reachable-leaf filter handles this at the data level; the visual encoding must reinforce it.
- **No flat displays at scale.** 500 same-sized circles is noise, not information. Visual hierarchy (size, shape, emphasis) must create entry points and scannable structure.
- **Support focus transitions.** The hardest ADHD moment is shifting from "seeing everything" to "working on one thing." The graph should support both modes: full overview for orientation, and single-project focus for commitment.

## Current Implementation

### Filtering: `filter_reachable` (in `scripts/task_graph.py`)

The default view runs the `filter_reachable` algorithm:

1. Identifies **leaves**: incomplete work-item nodes with no incomplete children (types: task, project, epic, bug, feature, review)
2. Walks **upstream** from each leaf through parent, `depends_on`, and `soft_depends_on` edges
3. Keeps all reachable nodes; completed nodes in the reachable set become **structural** (displayed differently)
4. Everything else is pruned

This means the graph shows: every actionable task, plus its full ancestor chain and dependency chain. Completed tasks appear only when they're structural ancestors of active work.

### Two Rendering Tabs

| Feature | SVG Tab (Graphviz sfdp) | Interactive Tab (force-graph Canvas) |
|---------|------------------------|--------------------------------------|
| Node shape | Per type (ellipse, box3d, octagon, box, diamond, hexagon, etc.) | All circles |
| Node size | Uniform | Uniform (default 6px) |
| Fill color | Per status | Per status |
| Border color | Per assignee (purple=nic, cyan=bot, orange=worker) | None |
| Edge style | Per type (blue solid=parent, red bold=depends_on, gray dashed=soft, dotted=wikilink) | All identical gray |
| Weight label | `downstream_weight` shown as text | Not shown |
| Interactivity | Pan/zoom only | Pan/zoom, click (posts message but no visible effect), layout switching, filtering |
| Generation | Requires running `/task-viz` skill; can go stale | Real-time from graph.json |

### Controls (Interactive Tab)

| Control | Options |
|---------|---------|
| **View** | Tasks, Knowledge Base |
| **Layout** | ↓ Top-Down, → Left-Right, ◎ Radial, ⚛ Force |

**Visual Settings** (in collapsible expander):

| Setting | Range | Default | Purpose |
|---------|-------|---------|---------|
| Node Size | 1-20 | 6 | Size of node circles |
| Link Width | 0.5-5.0 | 1.0 | Thickness of edges |
| Text Size | 6-24 | 12 | Base font size for labels |
| Link Opacity | 0.1-1.0 | 0.6 | Edge transparency |
| Repulsion | -500 to -10 | -100 | Node repulsion strength |
| Show Labels | checkbox | On | Toggle label visibility |
| Hide Orphans | checkbox | Off | Remove nodes with no connections |

**Filter** (in collapsible expander):

| Setting | Type | Purpose |
|---------|------|---------|
| Show Types | multiselect | Filter nodes by frontmatter type |

Default type filtering for Tasks view: `goal`, `project`, `epic`, `task`, `action`, `bug`, `feature`, `learn`. Knowledge Base view defaults to all types.

### Data Sources

- Tasks view: `$ACA_DATA/outputs/graph.json` (produced by fast-indexer)
- Knowledge Base view: `$ACA_DATA/outputs/knowledge-graph.json`

### Node Colors

**Tasks view** (by status):

| Color | Status |
|-------|--------|
| Blue (#3b82f6) | active |
| Green (#22c55e) | done (structural only in reachable view) |
| Red (#ef4444) | blocked |
| Yellow (#eab308) | waiting |
| Purple (#a855f7) | review |
| Gray (#94a3b8) | cancelled |

**Knowledge Base view** (by type):

| Color | Type |
|-------|------|
| Red | goal |
| Purple | project |
| Blue | task |
| Cyan | action |
| Orange | bug |

## User Stories

### US-TM1: I can see the forest, not just the trees

**As** Nic returning to work after time away,
**I want** the task map to show me the *structure* of my work at a glance — which projects are tangled, which are linear, where clusters form,
**So that** I get oriented in seconds, not minutes.

**What this means for the graph:**

- Nodes representing higher-level structure (goals, projects, epics) must be visually larger than leaf tasks. The data exists — `downstream_weight` is computed by fast-indexer and displayed as a text label in the SVG view. The interactive graph should map it to node radius.
- Node type needs a visual channel beyond color. The SVG view uses Graphviz shapes (ellipse for goal, box3d for project, octagon for epic, etc.). The interactive view should approximate these — even simple differences (circles for leaves, squares for epics, larger circles for projects) would massively improve scanability.
- Related nodes should visually cluster. A project and its children should form a recognizable spatial group, not scatter randomly across the canvas.

**Acceptance test:** Nic can identify which project a cluster belongs to without reading any labels, just from spatial grouping and the visual weight of the project node anchoring the cluster.

### US-TM2: I can see where work is alive

**As** Nic trying to figure out what's happening across my workstreams,
**I want** recently-modified nodes to stand out from stale ones,
**So that** I can immediately see where effort is concentrated and where things have gone quiet.

**What this means for the graph:**

- Nodes touched in the last 24–48 hours should have visual emphasis — a glow, brighter color, pulsing border — something that draws the eye before any text is read.
- Nodes untouched for 2+ weeks should visually recede — reduced opacity, desaturated color. They're still in the graph (the filter already decided they're relevant), but they shouldn't compete for attention with active work.
- This is a recency heatmap overlaid on the structural graph. The structure stays stable; the heat shifts to show where life is.

**Acceptance test:** Without reading a single label, Nic can point to the 2–3 areas of the graph where work happened today.

### US-TM3: I can see what's stuck and what it's blocking

**As** Nic scanning for bottlenecks,
**I want** blocked nodes and their downstream impact to be immediately visible,
**So that** I can spot high-impact blockers without tracing edges manually.

**What this means for the graph:**

- A blocked node with 15 downstream tasks should look *alarming*. A blocked node with 1 downstream task is less urgent. The combination of blocked status + high `downstream_weight` should create a visually distinctive danger signal (size + red is a start).
- When clicking or hovering a blocked node, the user should see what it's blocking — highlight the downstream subgraph, or at minimum show a count: "Blocking 12 tasks across 3 projects."
- Dependency edges (`depends_on`) should be visually distinct from parent edges. The SVG view does this (blue solid = parent, red bold = dependency, gray dashed = soft dependency). The interactive view currently renders all edges as identical gray lines.

**Acceptance test:** Nic can identify the highest-impact blocker in the graph within 5 seconds, without clicking anything.

### US-TM4: I can drill into a node and understand its context

**As** Nic who has spotted something interesting in the graph,
**I want** to click a node and immediately see its title, status, parent chain, children, and dependencies,
**So that** I can understand what it is and where it fits without leaving the dashboard.

**What this means for the graph:**

- Clicking a node should show a detail panel with: full title (not truncated ID), status, priority, assignee, breadcrumb (Goal → Project → Epic → This Task), children with their status, dependencies (what this blocks / what blocks this), and a link to open the file directly (Obsidian URI).
- Clicking a node should visually highlight its neighborhood — dim unrelated nodes, brighten direct connections. This makes the graph a navigation tool.
- Clicking empty space clears the selection.

**Acceptance test:** Nic clicks a node and within 1 second has enough context to decide "this needs attention" or "this is fine" without opening any other tool.

### US-TM5: I can read the graph without a manual

**As** Nic (or eventually, a colleague looking at my dashboard),
**I want** the visual encoding to be self-explanatory,
**So that** I don't have to remember what colors and sizes mean.

**What this means for the graph:**

- A compact legend strip near the graph (not buried in an expander). One or two lines max.
- The legend must match what's actually rendered. The SVG tab has an extensive legend; the interactive tab has nothing.
- If node size encodes downstream weight, the legend should explain: "Larger nodes = more downstream work."

**Acceptance test:** Someone who has never seen the dashboard before can explain what the colors and sizes mean after looking at the graph for 10 seconds.

### US-TM6: I can focus on one project without the rest distracting me

**As** Nic who has decided to work on one specific project,
**I want** to filter the graph to show only that project's subgraph,
**So that** I can see its full structure without visual noise from everything else.

**What this means for the graph:**

- A project selector (dropdown or clickable project nodes) that filters to one project's subtree plus any cross-project dependencies.
- In single-project mode, the node count is small enough to show all labels and the full hierarchy without overlap.
- This is a filter on the existing graph, not a separate tool. "All projects" returns to the default view.

**Why this matters for ADHD:** The hardest part of starting work isn't finding the task — it's getting your brain to stop seeing everything else. A visual "blinders" mode reduces the cognitive cost of focusing.

**Acceptance test:** Nic selects "overwhelm-dashboard" from the filter and sees only dashboard-related nodes, clearly laid out, with enough detail to pick his next task.

### US-TM7: Labels tell me what things are, not what they're called in the database

**As** Nic trying to read the graph,
**I want** node labels to show human-readable titles, not task IDs,
**So that** I can identify what each node represents.

**What this means for the graph:**

- Current code uses `n.get("label", n["id"])[:30]` — many nodes display their ID (e.g., `overwhelm-dashboard-e993b43b`) because `label` isn't populated or falls back to `id`. The graph should use the `title` field from the task data.
- Truncation to 30 chars often destroys meaning. Better: show labels only above an importance threshold at zoomed-out view (goals + projects always labeled), progressively revealing more labels as the user zooms in.
- At default zoom, high-level structure is labeled. At any zoom level, no labels overlap to the point of illegibility.

**Acceptance test:** At default zoom, Nic can read every project name. At any zoom level, no labels overlap to the point of illegibility.

### US-TM8: Edge types tell me about the nature of relationships

**As** Nic trying to understand why things are connected,
**I want** to distinguish between hierarchy edges, hard dependencies, and soft links,
**So that** I can trace parent chains and blocker chains through the graph.

**What this means for the graph:**

- The SVG view differentiates: blue solid (parent), red bold (depends_on), gray dashed (soft_depends_on), light gray dotted (wikilink). The interactive force-graph renders all edges as identical gray lines with opacity 0.6.
- At minimum: parent edges visually heavier/darker, dependency edges a distinct color (red/orange), soft/wiki links lighter.
- Dependency edges are the most important for understanding blockers — they should be the most visible.

**Acceptance test:** Nic can visually trace a dependency chain through the graph without confusing it with the parent hierarchy.

## Known Bugs

### Completed tasks leaking through the reachable filter

Some completed (green) nodes appear in the reachable view that shouldn't be there. The `filter_reachable` logic keeps completed nodes that are upstream ancestors of leaves, but some green nodes appear without an obvious active leaf downstream. Possible causes: wikilinks creating unexpected upstream paths, edges being traversed bidirectionally in ways the algorithm doesn't intend, or stale graph data from a previous indexing run.

**User expectation:** A completed task should never appear in the reachable view unless you can trace exactly why it's there — i.e., which active leaf it's ancestral to. If a user can't tell why a green node exists, the filter has a bug.

## Scope Boundary

The task map handles the **structural overview**. These adjacent needs belong to other dashboard sections:

| Need | Handled by |
|------|-----------|
| "What was I doing in that terminal?" | Session cards / Where You Left Off |
| "What got done today?" | Daily synthesis / accomplishments |
| "What's my single next action?" | Project boxes / UP NEXT |
| "How do I recover my dropped threads?" | Your Path / dropped threads |

## Acceptance Criteria

### Rendering

- [ ] Task graph renders without freezing browser
- [ ] Knowledge Base graph view displays notes and wikilinks
- [ ] Graph loads within 2 seconds for typical data size (~500 nodes after filtering)
- [ ] Node selection shows task/note details

### Visual Encoding (Interactive Tab)

- [ ] Node size varies by `downstream_weight` — structural nodes (goals, projects) visually larger than leaf tasks
- [ ] Node shape or outline varies by type — at least goals, projects, epics, and leaf tasks are visually distinguishable
- [ ] Edge style varies by relationship type — parent, depends_on, and soft_depends_on are visually distinct
- [ ] Recency emphasis: recently-modified nodes visually brighter/highlighted; stale nodes recede
- [ ] Blocked nodes with high downstream weight create a distinctive visual signal
- [ ] Labels use `title` field, not task ID; progressive reveal by zoom level
- [ ] Compact legend strip visible without opening an expander

### Interaction

- [ ] Clicking a node shows detail panel (title, status, breadcrumb, children, dependencies)
- [ ] Clicking a node highlights its neighborhood; dims unrelated nodes
- [ ] Project filter dropdown restricts graph to single project subgraph
- [ ] Clicking empty space clears selection

### Filtering

- [ ] `filter_reachable` produces no false positives: every completed node in the view has a traceable path to an active leaf
- [ ] Default view shows only reachable nodes; completed-only subtrees are pruned

## Related

- [[Overwhelm Dashboard]] — Parent spec; the task map is one section of this dashboard
- [[task-viz]] — Standalone graph visualization skill
- [[fast-indexer]] — Produces graph.json consumed by both SVG and interactive renderers
- [[pkb-server-spec]] — PKB data model and MCP tools
- [[effectual-planning-agent]] — Strategic planning vision that the task map supports
- [[work-management]] — Task lifecycle and graph insertion rules
