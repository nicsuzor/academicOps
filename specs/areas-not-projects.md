---
title: "Areas not Projects: collapsing the work-item hierarchy"
type: spec
status: draft
tier: data
created: 2026-04-27
supersedes_partial:
  - pkb-type-taxonomy.md (Category 1: project as actionable type)
  - work-management.md (Multi-Project Organization, Graph Insertion Responsibility)
depends_on:
  - pkb-type-taxonomy.md
tags:
  - pkb
  - type-system
  - graph
  - hierarchy
  - architecture
---

# Areas not Projects

## Problem

The PKB hierarchy has Project as a structural type (`Project → Epic → Task → Action`) and derives project membership from the parent chain (decision 2026-03-22). In practice this conflates two distinct concerns and forces users to express both through one mechanism:

1. **Tree role** — single-parent, well-typed, used for decomposition, dependency propagation, and `downstream_weight` BFS.
2. **Area-of-life / category** — multi-valued, evolving, used for filtering, dashboards, and "what's this for?" framing.

These have opposite shapes. Tree roles want exactly one parent; areas want many. Tree roles are bounded efforts; areas are stable nouns. Tree roles get completed; areas persist. Forcing both through `type: project` produces the failure modes visible in the dashboard:

- **Project-inside-project nesting** ("Personal" containing "Personal Life") — emerges whenever a task or epic conceptually belongs to multiple "projects" but the tree forces single-parenthood. The user creates an outer container project to hold the redundant inners.
- **Sibling-project duplication** ("Garage Cleanup" vs "Garage Improvements") — the same area of life split across two project nodes because each represents a different bounded effort.
- **Wrong-level orphans** — tasks like "Fix MOSFET gate driver error" that genuinely belong to "Home Automation" but don't fit any of its sub-epics, parented at the project level instead of inside an epic.
- **Borderless dashboard groups** — the treemap renders a frame around any node that has children, including non-project containers; the title is empty when the structural type doesn't match what a layout expected.
- **Filter brittleness** — the `project=X` filter only catches what's in that subtree, not what semantically belongs to area X. Cross-cutting work (e.g. a Home Automation task that's also Garage-relevant) is invisible to either filter.

This is the same failure mode the framework already corrected for **Goals** (decision 2026-03-26: goals removed from tree, linked via `goals: []` metadata). The fix is to apply the same pattern to projects.

## Decision

Drop `project` as an actionable type. Make **Epic** the sole root of the work-item tree, with epics nestable into sub-epics. Replace project membership with **Areas** — a multi-valued metadata field on epics and tasks, used for filtering, dashboards, and area-of-life framing. Goals continue to link via `goals: []` metadata. The tree describes decomposition; metadata describes association.

## New model

### Hierarchy (strict tree, decomposition only)

```
EPIC → TASK
```

- **Epic**: bounded, verb-shaped unit of work. Tree root by default; may have an epic parent for sub-epic nesting. No depth limit, but the existing P#73 anti-star-pattern rule still applies: more than ~5 children means create an intermediate epic.
- **Task**: single-session deliverable. Must have an epic parent. (The `action` classification continues to mark sub-tasks via `classification: action` per pkb-type-taxonomy.md — no separate type.)
- **`learn`**: unchanged from pkb-type-taxonomy.md. Still excluded from `ready_tasks()`.

### Metadata (associations, many-to-many)

| Field   | Type          | On                | Purpose                                                                        |
| ------- | ------------- | ----------------- | ------------------------------------------------------------------------------ |
| `areas` | `Vec<String>` | epic, task, learn | Multi-valued area labels. Stable nouns. Used for filtering and grouping.       |
| `tags`  | `Vec<String>` | any               | Pre-existing free-form tags. Areas are _not_ tags — see "Areas vs tags" below. |

**Goals are out of scope for this spec.** Goal linkage is being reworked under `task-0779b81b` and `multi-parent-edges.md` to use weighted `contributes_to` edges to first-class target/prototype nodes, not metadata. The pilot has already validated the precedent that this spec rests on: _"`contributes_to` edges are independent of `parent` — reparenting did not disturb propagation wiring"_ (task-0779b81b, 2026-04-24). Areas (this spec) and goals (the contributes_to track) are sibling refactors expressing the same insight: structural parent and semantic association are different concerns.

### Areas semantics

- **Open vocabulary**: areas are user-defined strings (e.g. `home-automation`, `garage`, `cyberlaw-research`, `osb`, `personal`). No closed list. The framework does not validate area names against a registry.
- **Area dossier files** (optional): for areas that need durable context, the user can create `$ACA_DATA/areas/<area>.md` — a dossier note linked from epics carrying that area. Like `goals/`, but for area-of-life containers.
- **Inheritance**: when an epic has `areas: [x, y]`, child tasks default to `areas: [x, y]` _unless_ they declare their own. Declared areas on a child **fully replace** the inherited set — explicit beats implicit, no merge. This handles the user's case ("one subtask might be in a different project to its siblings") and forces a deliberate act when overriding rather than letting partial declarations silently inherit context. (Decision 2026-04-27.)
- **No area = no area**: tasks/epics with empty `areas: []` are valid (e.g. one-off scratch work). Sleep flags long-lived empty-area epics, doesn't auto-tag.
- **Default expansion**: when listing tasks for an area, the dashboard returns tasks with the area in their `areas` field _or_ tasks whose nearest ancestor epic has the area in its `areas` field. This makes inheritance visible without requiring a write to every leaf.

### Areas vs tags

`tags` are free-form, polysemic, low-commitment ("ergonomics", "decomposed-by-claude", "spike"). `areas` are first-class areas-of-life with semantic weight, used by the dashboard's primary grouping axis. The distinction is the same one between `goals: []` and `tags: []` — when something is structurally important, it gets its own field.

If a tag has graduated into a stable area-of-life (used as a filter for >30 days, applied to >10 nodes), `/aops-cowork:planner` in `maintain` mode should propose promoting it from `tags` to `areas`.

## Migration: project → epic OR area

Each existing `type: project` node migrates to one of two destinations. The classification heuristic:

| If the project is...                                                                          | Migrate to                          | What happens                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Verb-shaped, bounded, completable (e.g. "Build search API", "Fix Fujitsu AC crash bug")       | **Epic**                            | Reclassify in place: `type: project` → `type: epic`. Existing children remain attached. Inherits `areas` from any prior `project:` parent if present.                                                                                                                                                                            |
| Noun-shaped, persistent, area-of-life (e.g. "Home Automation", "Garage", "Cyberlaw Research") | **Area dossier (replace in place)** | The original project file's frontmatter is rewritten (`type: project` → `type: area`); body is preserved. The file moves from `data/tasks/<id>.md` → `$ACA_DATA/areas/<slug>.md` (the canonical location for area dossiers). Children are detached and become tree-root epics carrying `areas: [<slug>]`. (Decision 2026-04-27.) |
| Ambiguous / both                                                                              | Flag for user review                | Sleep / planner surfaces these; user decides per-case during the proposal phase.                                                                                                                                                                                                                                                 |

The heuristic test the migration script applies:

- **Has a deadline, completion criteria, or clear "done" state** → Epic.
- **Has been active >180d with no plausible end, or contains multiple unrelated bounded efforts** → Area.
- **Title is a noun phrase ("Home Automation"), no verb** → Area.
- **Title is a verb phrase ("Add user authentication") or includes a target outcome** → Epic.
- **Otherwise** → flag for user review.

For the user's screenshot:

- "Personal" → Area `personal`. Children (Personal Life, Garage, etc.) detached and reclassified.
- "Personal Life" → **deleted**. Its children directly carry `areas: [personal]`.
- "Home automation: full house electronics control" → Epic. Carries `areas: [home-automation, personal]`. Sub-epics ("Fix Fujitsu AC", "Path A: ESPHome") become its children — already are. Orphan tasks ("Design flexible multi-PCB", "Fix MOSFET gate driver error", "Fix OwnTone healthcheck") stay parented to the Home Automation epic — currently their position is legal under the new model (epic → task). They're just visible now.
- "Garage Cleanup" + "Garage Improvements" → Two epics, both with `areas: [garage, personal]`. (They stay separate because they describe different bounded efforts — one is a cleanup pass, one is build-out.) The user can also collapse them manually if they're really one effort.
- "Workspace Setup & Ergonomics" → Epic, `areas: [office, personal]`.
- "Kitchen Copper Splashback" → Epic, `areas: [home, personal]`.

## Implementation surface

This change touches three repos. Each line is a candidate epic for decomposition.

### `mem` (Rust) — schema and graph

1. Reduce `ACTIONABLE_TYPES` from `[project, epic, task, learn]` to `[epic, task, learn]`. Add temporary alias resolution: incoming `type: project` → `type: epic` at parse time, with linter warning. Add `area` as a new reference type (Category 2 in pkb-type-taxonomy) for area dossier files.
2. Add `areas: Vec<String>` field to `GraphNode`, parsed from frontmatter on epic/task/learn nodes.
3. Update `pkb_orphans` rules: tasks need an epic parent; epics may have any epic parent or be tree root. Remove project-as-required-root.
4. Update `decompose_task` to permit creating an epic under another epic (sub-epic decomposition).
5. Update treemap layout (`layout.rs:608` `is_treemap_type`) to no longer special-case projects.
6. Update `task_search` and `list_tasks` filters: replace `project=X` with `area=X`, supporting inheritance lookup (a task with `areas: []` and an ancestor epic with `areas: [x]` is matched by `area=x` queries — but the inheritance is read-side only; writes are explicit per the replace semantics).
7. Update `ready_tasks()` if it uses project ancestry — switch to area filter.
8. `graph_stats`: replace `disconnected_epics` (count of epics not attached to a project) with `epics_without_areas` (count of epics with empty areas).

### `academicOps` — skills, workflows, specs

1. **`pkb-type-taxonomy.md`**: rewrite Category 1. `project` removed. Goals link via metadata on epics, not projects. Hierarchy diagram updates.
2. **`work-management.md`**: replace "Multi-Project Organization" with "Areas". Update "Graph Insertion Responsibility" to require an epic parent (not a project lineage). Update mermaid diagram.
3. **`planner` SKILL.md**:
   - Strategic-intake "Classify Level" table loses the Project row; gains an Area row (level: Area, signal: stable area-of-life, action: create dossier file).
   - "Work Hierarchy" section becomes `EPIC → TASK`.
   - decompose mode: drop "goal needs projects/epics first" branch.
   - maintain mode: add area-promotion activity (tag → area when graduated).
4. **`planner/workflows/decompose.md`**: remove project layer from the decomposition shape. Update the example.
5. **`planner/workflows/strategic-intake.md`**: same as above.
6. **`remember` SKILL.md**: storage hierarchy table — "Epics/projects" merges to "Epics". Add `areas/<name>.md` row.
7. **`sleep` SKILL.md**: Phase 5b strategy table — replace `disconnected_epics`, `projects_without_goal_linkage` with `epics_without_areas`, `area_dossier_drift`. Phase 4 dedup unchanged.
8. **`q` command**: capture mode parent resolution simplifies — find or create an epic, no project lookup.
9. **`daily` SKILL.md**: any "current project" surfacing becomes "current areas + active epics."
10. **Dashboard**: add group-by-area as primary grouping axis. Tree view stays but renders epic forests, not project forests. Borderless-group rendering bug goes away because there's no longer a structural type that produces an unnamed container.

### `brain` — data migration

1. One-pass classifier script over `data/tasks/*.md`: for each `type: project`, apply the migration heuristic, produce a proposal file (no writes).
2. User reviews proposals; flips ambiguous cases.
3. Apply: rewrite frontmatter (project → epic, add areas), reparent children, create area dossier files, delete the now-redundant container projects.
4. Re-run `pkb_orphans` and `graph_stats` to verify clean state.
5. Commit with a single migration message linking back to this spec.

## What this does NOT do

- **Does not remove the tree.** Decomposition still produces a strict parent-child tree. Epics and tasks still have exactly one parent.
- **Does not introduce multi-parent edges.** That's `multi-parent-edges.md`'s territory (`contributes_to` for catastrophic obligations). Areas are pure metadata, no edge.
- **Does not specify goal linkage.** Goals are owned by `task-0779b81b` / `multi-parent-edges.md` (target/prototype nodes + `contributes_to` edges). When that work lands, target nodes will live in the tree under whatever epic owns them (per the 2026-04-24 pilot reparenting), and tasks will link to them via `contributes_to` edges. This spec is silent on `goals: []` — that field is being superseded, not migrated.
- **Does not affect `learn` semantics.** `learn` stays in `ACTIONABLE_TYPES`, still excluded from `ready_tasks()`, can carry `areas`.
- **Does not remove tags.** Areas and tags coexist; areas are the structural filter, tags are free-form labels.
- **Does not change priority, status, or assignment.** Those orthogonal axes are untouched.

## Component assessment (BUTLER.md criteria)

| Criterion                | Old model (project as type)                        | New model (areas as metadata)                           |
| ------------------------ | -------------------------------------------------- | ------------------------------------------------------- |
| Used without enforcement | No — agents need lint rules to keep projects clean | Yes — areas are optional, evolve organically            |
| Reduces real friction    | No — forces single-parent on multi-area work       | Yes — multi-membership trivially expressible            |
| Agents understand it     | Partial — 4-level hierarchy is a lot of structure  | Yes — 2-level tree + metadata mirrors the goals pattern |
| Survives neglect         | No — orphan/wrong-type-parent classes accumulate   | Yes — bare epics with no areas are still valid nodes    |

## Open questions (deferred to implementation)

Three foundational decisions resolved 2026-04-27 by user:

1. ~~Area dossier replace vs separate~~ → **Replace in place.** Project file's frontmatter is rewritten and the file moves to `$ACA_DATA/areas/<slug>.md`.
2. ~~Inheritance replace vs merge~~ → **Replace.** Explicit beats implicit; declared areas on a child fully replace inherited.
3. ~~Goals attach to epics or tasks~~ → **Out of scope.** Goals are being reworked under `task-0779b81b` / `multi-parent-edges.md` to use weighted `contributes_to` edges to target/prototype nodes. Areas and goals are sibling refactors, not coupled.

Remaining decisions, deferable to implementation:

4. **Archive vs delete for redundant container projects.** "Personal Life" disappears after migration. Hard delete (git-history-only trace) or move to `data/tasks/archived/`? Recommendation: archive — git is the audit trail but a visible archive folder preserves the "what was this?" context for the first month while the migration is fresh.
5. **Dashboard re-render shape.** GroupBy-area as a separate page, or a toggle on the existing treemap? Recommendation: toggle — minimum new surface area, lets users compare structural and semantic views side by side. Decide during Epic 3.
6. **Linter behaviour on `type: project`.** Hard reject (refuse to parse), warn-and-coerce (parse as epic, log a warning), or accept silently for a transition window. Recommendation: warn-and-coerce for one week post-migration, then hard reject. Decide during Epic 1.
7. **Recovery of historical `project:` frontmatter values.** The 2026-03-22 decision deleted the field; the parent-chain derivation took over. For the migration heuristic to work, we need to know which area each existing epic _should_ carry. Strategy: derive from the existing parent chain at migration time (the project node currently above each epic IS the area-or-epic). No git history dive needed.

## Acceptance criteria

1. `type: project` does not exist in `data/tasks/` after migration.
2. `pkb_orphans` reports zero project-related violations and zero wrong-type-parent for tasks-under-projects.
3. The dashboard treemap groups by `areas[0]` by default and renders no untitled containers.
4. A new task created via `/q` lands under an epic with `areas` inherited from that epic.
5. A task can have `areas: [a, b]` independent of its parent epic's areas.
6. The user's screenshot's structural problems (Personal-inside-Personal, sibling Garage projects, orphan Home Automation tasks at the wrong level) are resolved or explicitly resolved-by-user-decision.
7. Sleep cycle Phase 5b runs successfully against the new metric set without falling back to project-based heuristics.
8. `planner`, `q`, `remember`, `sleep`, `daily`, `decompose`, `strategic-intake` skill files no longer reference `project` as a structural concept.

## Risks

- **Big-bang migration risk**: 200+ project nodes touched in one pass. Mitigated by: dry-run proposal file, user review before apply, keeping the old data on a branch until verified.
- **Skill currency**: existing tasks and instructions across `brain/` will reference "the X project" in prose. These don't break — areas can be named identically — but stale references in spec files should be swept by a follow-up garden pass.
- **Cross-machine sync race**: migration commit must land before any agent on another machine pulls; otherwise an agent could create new project-typed nodes that need re-migration. Mitigated by: pause polecats, do migration on Mac, push, verify cron sync on dev3 before resuming.
- **Hidden project filter consumers**: dashboards, CLI flags, and the `aops` binary may take `--project` arguments. These need an alias period (`--area` accepted, `--project` warns and routes to area).

## Giving Effect

- `mem`: schema in `mem/src/graph_node.rs` (or equivalent), `ACTIONABLE_TYPES` in `mem/src/graph_store.rs`, orphan logic in `mem/src/orphans.rs`, MCP filter handlers in `mem/src/mcp_server.rs`.
- `academicOps`: skill files under `aops-core/skills/{planner,remember,sleep,daily,q}/`, workflows under `aops-core/skills/planner/workflows/`, specs under `specs/`, dashboard under `dashboard/`.
- `brain`: migration script in `scripts/migrate-project-to-area.py` (proposal generator + applier), one-shot run.

## See also

- [[pkb-type-taxonomy]] — type system that this spec evolves
- [[work-management]] — task CRUD spec, hierarchy section needs refresh
- [[multi-parent-edges]] — non-tree edge precedent (`contributes_to`); validates the "structural parent vs semantic association" separation that this spec rests on
- [[task-0779b81b]] — pilot that empirically validated structural/relational separation (2026-04-24: `contributes_to` edges survive reparenting); also owns the future state of goals
- [[VISION]] — design philosophy 5 (minimal), 7 (core vs fungible), 8 (earn their keep), 10 (skills express philosophy not procedures)
- [[BUTLER]] — decision log entries for goals-removed-from-tree (2026-03-26), project-frontmatter-removed (2026-03-22), intentions-removed (2026-03-27)
