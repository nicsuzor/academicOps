---
title: Planning Web — Svelte Web Application Spec
type: spec
status: draft
tier: ux
depends_on: [overwhelm-dashboard, task-focus-scoring]
tags: [spec, planning-web, svelte, dashboard, visualization, graph, adhd]
created: 2026-03-07
---

# Planning Web — Svelte Web Application

## Giving Effect

- Replaces: `aops-tui-spec-v0.1-a190d899` (ratatui TUI), `specs/overwhelm-dashboard.md` (Streamlit dashboard)
- Consumes: `aops graph` CLI output (`graph.json`, `knowledge-graph.json`), PKB MCP server, `synthesis.json`
- Related: `specs/task-focus-scoring.md`, `specs/task-map.md`, `specs/effectual-planning-agent.md`, `specs/batch-graph-operations-spec.md`

---

## Vision

Most task managers are flat lists with priorities bolted on. They treat tasks as independent atoms to be triaged. This is wrong for academic work, where everything connects: a peer review decision shapes a collaboration, which feeds a research paper, which advances a strategic goal, which rests on assumptions you haven't tested yet.

**The Planning Web makes the graph the interface.** Instead of staring at a list of 35 tasks wondering what to do next, you see the _shape_ of your work: what enables what, what blocks what, what assumptions are load-bearing, and which threads are converging on the same goal. The PKB (Personal Knowledge Base) provides the connective tissue — surfacing relevant knowledge, sources, and context alongside actionable work.

The organising metaphor is not a todo list. It's a **planning web** — a directed graph of goals, projects, and tasks connected by `enables` and `blocks` relationships, annotated with assumptions and uncertainty, and enriched by your knowledge base.

### Alignment with academicOps Vision

The Planning Web is the human-facing surface of the academicOps framework (see `VISION.md`). It provides:

- **Visibility into baseline capabilities** — the task graph, memory, and knowledge architecture become navigable and actionable through a visual interface
- **Context recovery for fragmented schedules** — reconstructs what was happening, what got dropped, and what needs attention, accommodating solo academic schedules and ADHD
- **Zero-friction capture** — ideas flow from the interface into the PKB without mode-switching
- **Nothing lost** — every task, assumption, and knowledge node is searchable and surfaced when relevant

### Design Principles

1. **Effectuation over causation.** The UI doesn't demand top-down planning. It supports bottom-up emergence: fragments arrive, get placed, and structure reveals itself.
2. **Progressive disclosure.** Default view shows 3-5 actionable items. Complexity is available but never forced.
3. **Graph-native.** Every view is a projection of the underlying graph.
4. **Knowledge-enriched.** Tasks don't exist in a vacuum. The interface surfaces related PKB nodes alongside work items.
5. **Uncertainty-aware.** The effectual lifecycle and assumption tracking are first-class UI citizens.
6. **ADHD-accommodating.** Zero-friction, clear boundaries, scannable not studyable, directive framing, collapsible density.

---

## Target Platform

**Svelte** web application (SvelteKit). Runs locally or on a private server. Communicates with the PKB backend via MCP or a thin REST/WebSocket API layer.

### Why Svelte

- Reactive by default — graph state changes propagate naturally
- Small bundle size and fast rendering for data-dense views
- Component model suits the view-based architecture
- SvelteKit provides routing, SSR, and API routes out of the box

### Architecture

```
+--------------------------------------------------+
|              Planning Web (Svelte)                |
|         SvelteKit + D3/LayerCake graphs           |
+--------------------------------------------------+
|              View / Component Layer               |
|  Focus | Graph | Epic Tree | Node Detail | Dash   |
+--------------------------------------------------+
|           State / Store Layer (Svelte stores)     |
|  Graph state, selections, filters, preferences    |
+--------------------------------------------------+
|              Data / API Layer                     |
|  PKB MCP client, graph.json loader, WebSocket     |
+--------------------------------------------------+
|              Backend Services                     |
|  PKB MCP server, aops CLI, synthesis pipeline     |
+--------------------------------------------------+
```

### Data Sources

| Source                 | Content                                                    | Update Frequency                    |
| ---------------------- | ---------------------------------------------------------- | ----------------------------------- |
| `graph.json`           | Task graph with hierarchy, dependencies, downstream_weight | On `aops graph` run                 |
| `knowledge-graph.json` | PKB notes, wikilinks, tags                                 | On `aops graph` run                 |
| PKB MCP server         | Task CRUD, search, graph metrics                           | Real-time via API                   |
| `synthesis.json`       | LLM-generated narrative summary                            | Pre-computed, checked for staleness |
| Session state files    | Active/paused agent sessions                               | Polled or pushed via WebSocket      |
| Daily notes            | Today's accomplishments and context                        | File watch or poll                  |

---

## Data Model

### Status Lifecycle

```
seed --> growing --> active --> blocked --> complete
                      |                      ^
                    dormant -----------------+
                      |
                     dead
```

### Focus Scoring

Tasks are ranked by a continuous focus score (see `task-focus-scoring.md`):

```
focus_score = (
    w_downstream  * downstream_signal   +
    w_priority    * priority_signal      +
    w_project     * project_activity     +
    w_recency     * recency_signal       +
    w_blocking    * blocking_urgency     +
    w_user        * user_boost
)
```

- **Hot** (score >= 0.3): shown in default views
- **Cold** (score < 0.3): searchable but hidden from focus views
- Scores are computed at query time, never stored
- The score breakdown is available on demand for transparency

### Node Types & Visual Hierarchy

| Type        | Visual Treatment              | Role                           |
| ----------- | ----------------------------- | ------------------------------ |
| Goal        | Largest, gold/amber accent    | Desired future states          |
| Project     | Large, blue accent            | Bounded efforts toward goals   |
| Epic        | Medium, distinct shape        | PR-sized verifiable work units |
| Task        | Standard size, white/neutral  | Single-session deliverables    |
| Action      | Small                         | Atomic steps within tasks      |
| Bug/Feature | Standard, distinct icon       | Typed work items               |
| PKB Note    | Green accent                  | Knowledge nodes                |
| Source      | Green with bibliographic info | Citation nodes                 |

### Edge Types

| Relationship      | Visual Treatment                   | Semantics                                |
| ----------------- | ---------------------------------- | ---------------------------------------- |
| Parent-child      | Solid, heavier weight              | Hierarchy (goal > project > epic > task) |
| `depends_on`      | Distinct colour (red/orange), bold | Hard blocking dependency                 |
| `soft_depends_on` | Dashed, lighter                    | Enabling/unlocking relationship          |
| Wikilink          | Dotted, subtle                     | Knowledge reference                      |

---

## Views

### 1. Focus View (Default Landing)

**Question answered:** "What should I do right now?"

Shows top 5 actionable items selected by the focus scoring algorithm:

1. P1 tasks first
2. Approaching deadlines
3. Oldest P2 tasks (staleness)
4. Tasks that unblock the most (graph centrality / downstream_weight)
5. Cap at 5

**Sections:**

- **Top picks** — 5 task cards with title, project, priority badge, staleness indicator, and a one-line description. Each card links to Node Detail.
- **Untested assumptions** — Load-bearing assumptions grouped by downstream impact. Visual treatment: untested = yellow warning, confirmed = green check, invalidated = red cross.
- **Blocked summary** — Count of blocked tasks, grouped by blocker. "3 tasks waiting on [blocker title]" with link to unblock.

**Empty state usage:** Below the 5 picks, show recent completions and a "what got done" summary to provide momentum feedback.

### 2. Graph View

**Question answered:** "How does my work connect?"

Interactive force-directed graph of the planning web. This is the signature view — the planning web made visible.

**Node encoding:**

- **Size** varies by `downstream_weight` — structural nodes (goals, projects) visually larger than leaf tasks
- **Shape/outline** varies by type — goals, projects, epics, and leaf tasks are visually distinguishable (circles, rounded squares, hexagons, etc.)
- **Fill colour** by status (blue=active, green=done, red=blocked, yellow=waiting, purple=review, grey=cancelled)
- **Recency emphasis** — recently-modified nodes are brighter/saturated; stale nodes (>14 days) desaturate; very stale (>30 days) fade further
- **Blocked + high downstream_weight** creates a distinctive danger signal (size + red)

**Edge encoding:**

- Parent edges: solid, heavier
- `depends_on`: distinct colour (red/orange), bold
- `soft_depends_on`: dashed, lighter
- Wikilinks: dotted, subtle

**Layout options:** Top-Down, Left-Right, Radial, Force-directed (ForceAtlas2)

**Interactions:**

- Click node: opens detail panel, highlights neighbourhood, dims unrelated nodes
- Click empty space: clears selection
- Project filter: dropdown restricts to single project subgraph + cross-project dependencies
- Zoom: progressive label reveal (goals/projects always labelled; tasks visible on zoom)
- Hover: tooltip with title, status, downstream_weight

**Legend:** Compact strip near the graph (not buried in settings). One or two lines. Must match what's rendered.

**Visual settings** (collapsible panel):

| Setting      | Range       | Default | Purpose                   |
| ------------ | ----------- | ------- | ------------------------- |
| Node Size    | 1-20        | 6       | Base size of nodes        |
| Link Width   | 0.5-5.0     | 1.0     | Edge thickness            |
| Text Size    | 6-24        | 12      | Base font size            |
| Link Opacity | 0.1-1.0     | 0.6     | Edge transparency         |
| Repulsion    | -500 to -10 | -100    | Force layout spacing      |
| Show Labels  | toggle      | On      | Label visibility          |
| Hide Orphans | toggle      | Off     | Remove disconnected nodes |

**Type filter:** Multiselect for node types. Default for task view: goal, project, epic, task, action, bug, feature, learn.

**Reachable filter:** Default on — shows only actionable leaves + their ancestor chains. Completed nodes appear only as structural ancestors. Toggle off for full graph.

### 3. Node Detail View

**Question answered:** "What is this thing and where does it fit?"

Split-panel layout:

**Left panel — Content:**

- Status, priority, assignee, dates (created, modified)
- **Description** (markdown body) — promoted to top, immediately below metadata
- Subtask checklist with status indicators
- Assumptions with status (untested/confirmed/invalidated)
- Activity timeline (git-based modification history)

**Right panel — Context:**

- **Breadcrumb:** Goal > Project > Epic > This Task
- **Graph neighbourhood:** Direct parents, children, dependencies (blocks/blocked-by) with status badges
- **PKB connections:** Related notes surfaced by wikilink resolution, tag overlap, fuzzy title matching, citation backlinks
- **Downstream impact:** "Completing this unblocks N tasks across M projects"

**Actions available from detail:**

- Change status, priority
- Edit title, body (inline)
- Add/edit assumptions
- Add links (wikilinks, dependencies)
- Complete task
- Navigate to parent/child/dependency

### 4. Epic Tree View

**Question answered:** "What's the structure of my work?"

Hierarchical tree of goal > project > epic > task with:

- Task counts per node (done / total)
- Progress bars for epics
- Priority badges (P0 red, P1 orange, P2 default, P3 dim)
- Staleness badges (yellow >14d, red >30d)
- Type icons (Bootstrap Icons per node type)
- Expand/collapse with progressive depth
- Status colour-coding on each row

**Interactions:**

- Click to expand/collapse subtrees
- Click task to open Node Detail
- Multi-select mode for batch operations (see Batch Operations section)

**Sorting:** Within each level, sort by priority then by focus score.

### 5. Dashboard View

**Question answered:** "What's the health of my work and where's my attention going?"

Strategic overview with sections ordered by ADHD priority — most actionable information first:

#### 5.1 Current Activity

Agent count and active session indicator. "N agents running, M need your attention."

#### 5.2 Where You Left Off

Session cards for context recovery:

- **Active sessions** (<4h): Rich cards with project name, timestamp, initial prompt (what you asked), progress bar, current step, next step, status badge (Running / Needs You)
- **Paused sessions** (4-24h): Collapsed cards with outcome, accomplishment summary, reentry point. Subdued styling.
- **Stale sessions** (>24h): Archive prompt with count. "N stale sessions — [Archive All] [Review] [Dismiss]"

**Critical rule:** Sessions must show the user's initial prompt, not agent-generated descriptions. If a session can't answer "what was I doing?", it's filtered out.

#### 5.3 Your Path (Dropped Threads)

Reconstructed user path across sessions:

- **Dropped threads first** (most actionable for ADHD context recovery): tasks created/claimed but not completed, grouped by project with coloured borders
- **Timeline threads:** Horizontal-scroll cards per project with initial goal, git branch, and coloured-dot event timeline (prompts, task creates, completions, updates)

#### 5.4 Spotlight Epic

Progress bar for the most active open epic. Title, percentage, done/in-progress/blocked card grid. Clickable — drills into epic's task list.

#### 5.5 Focus Synthesis

Pre-computed LLM narrative (from `synthesis.json`):

- 3-5 bullet summary of today's story
- Status cards: accomplishments, alignment, blockers
- Session insights: skill compliance, corrections, context gaps
- Staleness indicator (STALE badge if >60 minutes)
- Graceful fallback when missing: message + regeneration hint

#### 5.6 Project Grid

Responsive grid of project cards (CSS grid, min 350px per card):

| Section   | Content                                                   |
| --------- | --------------------------------------------------------- |
| Header    | Project name, colour-coded border                         |
| Epics     | Active epic titles + progress bars (max 3)                |
| Completed | Recently completed tasks with time_ago (max 3 + "X more") |
| Up Next   | Top 3 priority tasks with priority AND status badges      |
| Recent    | Accomplishments from daily notes (max 3)                  |

Sorted by activity score. Empty projects hidden. Sub-projects roll up.

#### 5.7 Quick Capture

Text input + optional tags + submit. Creates a task in PKB inbox. Minimal friction: no project/priority required, just a title.

**Design target:** Idea to captured in under 5 seconds.

### 6. Assumption Tracker View

**Question answered:** "What am I betting on, and how risky are those bets?"

- Assumption registry extracted from node frontmatter `assumptions:` field
- Status tracking: untested / confirmed / invalidated
- Sorted by downstream impact (how much work depends on this assumption?)
- Inline status editing
- Visual treatment: untested = yellow, confirmed = green, invalidated = red
- When invalidated, highlights all at-risk downstream tasks

### 7. Duplicate Finder View

**Question answered:** "Am I tracking the same thing twice?"

- Shows duplicate clusters detected by title similarity and/or semantic embedding
- Each cluster: confidence score, canonical candidate, list of duplicates
- Actions: select canonical, merge others, archive
- Filters: scope by project, adjust similarity threshold

---

## Batch Operations

Multi-select mode available in Epic Tree View and Graph View:

- Select multiple tasks via shift-click, ctrl-click, or lasso (graph)
- Batch action bar appears when items selected:

```
N selected | Reparent | Archive | Update | Create Epic | Reclassify | Merge
```

### Available Batch Operations

| Operation   | Description                                       | Safety                  |
| ----------- | ------------------------------------------------- | ----------------------- |
| Reparent    | Move tasks to a new parent                        | Preview before apply    |
| Archive     | Set status to archived with optional reason       | Dry-run default         |
| Update      | Change priority, status, tags, or other fields    | Preview for >5 tasks    |
| Create Epic | Create new epic, reparent selected tasks under it | Confirm                 |
| Reclassify  | Change document type (task > epic, etc.)          | Preview                 |
| Merge       | Merge duplicates into canonical task              | Confirm, archive others |

All batch operations use the shared filter DSL from `batch-graph-operations-spec.md` and support dry-run preview.

---

## PKB Integration

### How Knowledge Surfaces

1. **Explicit wikilinks** — `[[reference]]` resolution against both task and knowledge corpora
2. **Tag overlap** — shared YAML `tags:` values create associations
3. **Title similarity** — fuzzy matching surfaces related content
4. **Citation backlinks** — `type: source` notes tracked and surfaced in citation neighbourhood

### Semantic Queries

The interface supports natural-language-style queries through the PKB search:

- "What do I know about [topic]?" — PKB notes + tasks + goals
- "What are the dependencies?" — graph traversal
- "What's converging?" — multiple links to same concept/goal
- "What's orphaned?" — no goal-path tasks, unreferenced PKB notes

### Unified Search

Global search (triggered by `/` or search bar) searches across both task graph and PKB knowledge base. Results show:

- Icon for type (task, note, source, etc.)
- Title
- Status and priority (for tasks)
- Snippet of matching content
- Project/parent context

---

## Agent Integration

### MCP Server Interface

The planning web exposes graph queries to AI agents via MCP:

- Node lookup and traversal
- Search across graph and PKB
- Task CRUD operations
- Graph metrics (centrality, PageRank, downstream weight)

### Agent-Suggested Actions

- **Next action suggestions** — information-value ranking from graph structure
- **Probe suggestions** — "You're assuming X. A cheap test might be: [action]"
- **Synergy detection** — multiple tasks/projects linking to same concept surfaced as cross-project opportunities
- **Structure proposals** — agent can propose graph amendments (reparenting, new epics, dependency additions)

---

## Visual Design

### Typography

Per STYLE.md:

| Context                | Font                               | Notes                           |
| ---------------------- | ---------------------------------- | ------------------------------- |
| Body text              | Space Grotesk or Host Grotesk      | Distinctive sans-serif          |
| Code/IDs               | BlexMono Nerd Font / IBM Plex Mono | Monospace for technical content |
| Accessibility fallback | Atkinson Hyperlegible              | When legibility is paramount    |

**Never use:** Inter, Roboto, Arial, system-ui, Helvetica (generic AI defaults).

### Icons

**Bootstrap Icons exclusively.** No emoji as interface icons. Consistent visual language across all views.

### Colour Palette

Muted academic palette with sharp accents. Must work in both light and dark themes.

**Status colours:**

| Status    | Colour        | Hex     |
| --------- | ------------- | ------- |
| Active    | Blue          | #3b82f6 |
| Done      | Green         | #22c55e |
| Blocked   | Red           | #ef4444 |
| Waiting   | Yellow        | #eab308 |
| Review    | Purple        | #a855f7 |
| Cancelled | Grey          | #94a3b8 |
| Seed      | Dim italic    | —       |
| Growing   | Yellow        | —       |
| Dormant   | Dim blue      | —       |
| Dead      | Strikethrough | —       |

**Priority colours:**

| Priority      | Treatment       |
| ------------- | --------------- |
| P0 (critical) | Bold red badge  |
| P1            | Orange badge    |
| P2            | Default/neutral |
| P3            | Dim grey        |

**Node type accents:**

| Type     | Accent                        |
| -------- | ----------------------------- |
| Goal     | Gold/amber                    |
| Project  | Blue                          |
| Task     | White/neutral                 |
| PKB Note | Green                         |
| Source   | Green + bibliographic styling |

**Staleness indicators:**

- 14 days: yellow
- 30 days: red / desaturated

**Assumption status:**

- Untested: yellow
- Confirmed: green
- Invalidated: red

### Backgrounds & Atmosphere

Per STYLE.md: create atmosphere and depth. Use CSS gradients, geometric patterns, or contextual effects rather than flat solid colours. The graph view especially benefits from a subtle dark background that makes node colours pop.

### Motion & Transitions

- Page transitions: subtle, fast
- Graph interactions: smooth zoom, pan, node highlight transitions
- Node selection: neighbourhood highlight with fade on unrelated nodes
- Staggered reveals on initial load for visual delight
- Prefer CSS transitions; use Svelte `transition:` directives
- No gratuitous animation — every motion should communicate state change

### Responsive Design

- Minimum viewport: 1024px wide (desktop-first; this is a planning tool)
- Sidebar collapses on narrower viewports
- Graph view takes full available width
- Project grid uses CSS grid with `minmax(350px, 1fr)`
- Detail panels use slide-over or modal on smaller screens

---

## Navigation & Interaction

### Global Navigation

Sidebar with page navigation:

- Focus (default landing)
- Graph
- Epic Tree
- Dashboard
- Assumptions
- Duplicates

### Global Controls

| Control           | Location                   | Purpose                                      |
| ----------------- | -------------------------- | -------------------------------------------- |
| Search            | Top bar                    | Unified fuzzy search across tasks + PKB      |
| Quick Capture     | Top bar or floating action | Zero-friction task creation                  |
| Theme toggle      | Settings                   | Light/dark mode                              |
| Time range filter | Sidebar                    | Filter completed tasks display (4H, 24H, 7D) |

### Keyboard Shortcuts

| Key             | Action                        | Context            |
| --------------- | ----------------------------- | ------------------ |
| `/`             | Open search                   | Global             |
| `n`             | Quick capture                 | Global             |
| `?`             | Help / shortcut reference     | Global             |
| `1-6`           | Navigate to view by number    | Global             |
| `j/k` or arrows | Navigate items                | Lists, tree        |
| `Enter`         | Open detail                   | Lists, tree, graph |
| `Escape`        | Close panel / clear selection | Global             |
| `Space`         | Toggle expand/collapse        | Tree view          |
| `f`             | Toggle reachable filter       | Graph view         |
| `s`             | Change status                 | Detail view        |
| `p`             | Change priority               | Detail view        |
| `a`             | Edit assumptions              | Detail view        |

Keyboard shortcuts should be discoverable — show a hint bar at the bottom of each view with context-relevant shortcuts.

---

## Task Management CRUD

Direct task manipulation from the interface:

| Operation | UI Element                                     | Backend                 |
| --------- | ---------------------------------------------- | ----------------------- |
| Create    | Quick capture (top bar) + full form in sidebar | PKB MCP `create_task`   |
| Read      | Node detail panel on click                     | PKB MCP `get_task`      |
| Update    | Inline edit on detail panel                    | PKB MCP `update_task`   |
| Delete    | Delete button with confirmation dialog         | PKB MCP `delete`        |
| Complete  | Single-click checkbox/button                   | PKB MCP `complete_task` |

### Inline Task Editor

Triggered by clicking edit on a task detail:

- Title (editable text)
- Status (dropdown)
- Priority (dropdown)
- Project (dropdown)
- Due date (date picker)
- Tags (tag input with autocomplete)
- Body (markdown editor with preview)
- Save / Cancel / Complete / Delete actions

**Principles:**

- Non-blocking: edits don't freeze the UI
- Optimistic updates: show changes immediately, sync in background
- Minimal clicks: common operations (complete, status change) in 1-2 clicks
- Context preservation: editing shouldn't lose graph position or scroll state

---

## ADHD Design Principles

These constrain all design decisions:

### Scannable, Not Studyable

The interface must communicate at a glance. Structure, colour, size, and spatial grouping carry meaning before any text is read. One-line items, coloured indicators, no paragraph-level reading required in overview modes.

### Dropped Threads First

The most actionable information for context recovery. Things started but not finished appear prominently. Directive framing: "YOUR PATH" not "Session History"; "NEEDS YOU" not "Status: waiting".

### No Flat Displays at Scale

500 same-sized items is noise, not information. Visual hierarchy (size, shape, emphasis) creates entry points. Bucket, group, and summarise — never dump hundreds of items in a list.

### Support Focus Transitions

The hardest moment is shifting from "seeing everything" to "working on one thing." The graph supports both modes: full overview for orientation, single-project filter for commitment.

### Collapsible Density

Important information above the fold. Detail available on demand. Sections collapse. Dense data (project grids, graph settings) is below or collapsed by default.

### Reactive, Not Demanding

Reconstructs context from existing data. No pre-planning required from the user. The system adapts to how you work, not the other way around.

### The Litmus Test

If a user sees a display element and can't answer "what does this mean?" within 3 seconds, the design has failed.

---

## Session Context Model

A session is a **conversation thread**, not an agent process. The user recognises sessions by what they asked, not by agent IDs.

### What Makes a Session Identifiable

1. **Initial prompt** — what the user first asked
2. **Follow-up prompts** — subsequent requests that shaped the work
3. **Working directory/project** — secondary context

### Session Display (Good)

```
[project icon] academicOps (2h ago)
   Started: "Review PR #42 for aops CLI changes"
   Now: Fixing 3 linting errors
   Next: Run tests, mark PR ready
```

### Session Triage

| Bucket     | Definition                | Display                                      |
| ---------- | ------------------------- | -------------------------------------------- |
| Active Now | Activity within 4 hours   | Full session cards with conversation context |
| Paused     | 4-24 hours since activity | Collapsed cards, click to expand             |
| Stale      | >24 hours since activity  | Archive prompt with batch actions            |

### Minimum Viable Context

A session must have initial prompt OR current task status. Sessions without meaningful context are hidden. "unknown: No specific task" is never displayed.

---

## Non-Goals

- External task manager sync (Jira, Asana, etc.)
- Multi-user collaborative editing (single-user system)
- Mobile-first design (desktop planning tool; responsive but not mobile-optimised)
- Calendar integration
- AI-generated content in the interface (agents suggest, humans decide)

---

## Open Questions

1. **Real-time vs polling.** Should the web app use WebSocket for live graph updates, or poll on an interval? WebSocket is better UX but adds server complexity.
2. **Offline support.** Should the app work offline with a cached graph.json? Useful for travel but adds sync complexity.
3. **Graph rendering library.** D3.js force-graph (current), Cytoscape.js, or Svelte-native (LayerCake + custom)? Need to evaluate performance at 500+ nodes.
4. **Authentication.** Local-only (no auth needed) vs. private server deployment (needs auth). Start local-only.
5. **PKB write-back latency.** How fast do task edits need to propagate to the markdown files? Optimistic UI with background sync seems right.
6. **Focus score computation.** Server-side (PKB MCP) or client-side from graph.json data? Server-side is simpler; client-side is more responsive.
7. **Assumption adoption.** Will tracking assumptions change planning behaviour, or is it too much friction? (Core bet — same as original TUI spec.)

## References

- Sarasvathy (2001). Causation and Effectuation.
- McGrath & MacMillan (1995). Discovery-Driven Planning.
- Snowden & Boone (2007). A Leader's Framework for Decision Making.
- academicOps VISION.md — Framework vision and success criteria
- academicOps STYLE.md — Visual design and typography standards
