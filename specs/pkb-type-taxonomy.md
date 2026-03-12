---
title: "PKB Type Taxonomy: Unified Node Classification"
type: spec
status: draft
created: 2026-03-11
tags:
  - pkb
  - type-system
  - graph
  - architecture
---

# PKB Type Taxonomy: Unified Node Classification

## Problem

The PKB type system has diverged across four layers, creating invisible work items, inconsistent filtering, and semantic confusion.

### Current state: four definitions, no agreement

| Layer              | Location             | Types treated as "actionable"                                                 |
| ------------------ | -------------------- | ----------------------------------------------------------------------------- |
| `VALID_NODE_TYPES` | `graph.rs:273`       | 24 types (validation only, no filtering)                                      |
| `ACTIONABLE_TYPES` | `graph_store.rs:83`  | task, bug, feature, project, goal, epic, learn, subproject                    |
| MCP `task_search`  | `mcp_server.rs:215`  | **task, project, goal** (hardcoded)                                           |
| MCP `list_tasks`   | `mcp_server.rs:1826` | Everything with an `id` field (`all_tasks()`)                                 |
| `is_treemap_type`  | `layout.rs:608`      | task, project, epic, goal, bug, action, subproject, feature, learn, milestone |
| Python `TaskType`  | `task_model.py:55`   | goal, project, epic, task, action, bug, feature, learn                        |

### Impact

**352 real work items are invisible to `task_search`:**

| Type      | Count | In `ACTIONABLE_TYPES` | In MCP `task_search` |
| --------- | ----- | --------------------- | -------------------- |
| `bug`     | 127   | yes                   | **no**               |
| `epic`    | 97    | yes                   | **no**               |
| `feature` | 52    | yes                   | **no**               |
| `action`  | 45    | yes                   | **no**               |
| `learn`   | 31    | yes                   | **no**               |

Meanwhile, `list_tasks` returns **everything with an `id` field** — including notes, contacts, and knowledge entries — because `all_tasks()` checks `task_id.is_some()` and `task_id` is populated from the `id` frontmatter field on every document.

### Root cause

The `type` field conflates two things:

1. **Graph role** — how the node participates in hierarchy, filtering, and task operations
2. **Content classification** — what the work item is about (bug vs feature vs action)

`bug`, `feature`, and `action` are classifications of work, not structural graph roles. A bug is a task. A feature is a task. An action is a task. They all behave identically in the graph — they have parents, statuses, dependencies, and appear in ready queues. The only type with genuinely different behaviour is `learn`, which is excluded from `ready_tasks()`.

## Design

### Principle: type encodes graph behaviour, not content

The `type` field answers: **"How does this node participate in the graph?"** — not "what is this about?" Content classification moves to a separate `classification` field and/or tags.

### Canonical type taxonomy

Three categories, exhaustive and mutually exclusive:

#### Category 1: Actionable (work items)

These appear in task operations (`list_tasks`, `task_search`, ready/blocked queues, task trees, treemap layouts).

| Type      | Graph role             | Parent requirement |
| --------- | ---------------------- | ------------------ |
| `goal`    | Top of hierarchy       | None (root-level)  |
| `project` | Body of work           | Goal or project    |
| `epic`    | Milestone group        | Project or epic    |
| `task`    | Discrete deliverable   | Epic or project    |
| `learn`   | Observational tracking | Epic or project    |

**Removed from type, moved to `classification`:** `bug`, `feature`, `action`, `subproject`, `milestone`.

- `bug` → `type: task, classification: bug`
- `feature` → `type: task, classification: feature`
- `action` → `type: task, classification: action`
- `subproject` → `type: project` (it IS a project, nested under another project)
- `milestone` → `type: epic, classification: milestone` (a checkpoint grouping tasks)

**`learn` stays as its own type** because it has distinct graph behaviour: excluded from `ready_tasks()` (not actionable work, but tracked observational items).

#### Category 2: Reference (knowledge items)

These never appear in task operations. They are knowledge artifacts, not work to be done.

| Type        | Content                                   |
| ----------- | ----------------------------------------- |
| `note`      | General knowledge, observations, insights |
| `memory`    | Agent/system memories                     |
| `contact`   | People                                    |
| `document`  | Generic documents                         |
| `reference` | External reference material               |
| `review`    | Review notes, reading notes               |
| `case`      | Case studies, legal cases                 |
| `spec`      | Specifications                            |
| `knowledge` | Synthesised knowledge articles            |

**Alias resolution** (linter auto-fixes):

- `observation`, `insight`, `exploration` → `note`
- `article`, `reading-guide`, `talk` → `reference`
- `review-notes`, `peer-review` → `review`
- `instructions`, `role`, `agent`, `bundle` → `document`
- `audit` → `audit-report`
- `design` → `spec`

#### Category 3: Structural (infrastructure)

Navigation and logging infrastructure. Never in task operations.

| Type           | Content              |
| -------------- | -------------------- |
| `index`        | Map of Content files |
| `daily`        | Daily notes          |
| `session-log`  | Session transcripts  |
| `audit-report` | Audit output         |

### The `classification` field

Optional frontmatter field for content classification of work items. Free-form string, but common values:

- `bug` — defect to fix
- `feature` — new functionality
- `action` — single work session
- `milestone` — checkpoint
- `spike` — time-boxed exploration
- `decision` — requires a choice
- `review` — review task (distinct from `type: review` which is review _notes_)

This field is for display and filtering only. It has no effect on graph behaviour.

### Single source of truth: `ACTIONABLE_TYPES`

All layers must use the same constant for determining what is a work item:

```rust
pub const ACTIONABLE_TYPES: &[&str] = &[
    "goal", "project", "epic", "task", "learn",
];
```

Every place that currently has its own hardcoded type filter must reference this constant:

| Location                                         | Current filter        | Change                                             |
| ------------------------------------------------ | --------------------- | -------------------------------------------------- |
| `mcp_server.rs:215` (`task_search`)              | `task\|project\|goal` | Use `ACTIONABLE_TYPES`                             |
| `mcp_server.rs` (`all_tasks()` via `list_tasks`) | `task_id.is_some()`   | Add `ACTIONABLE_TYPES` check                       |
| `layout.rs:608` (`is_treemap_type`)              | 10 hardcoded types    | Use `ACTIONABLE_TYPES`                             |
| `task_index.rs:234`                              | Inline `!= "learn"`   | Keep (behavioural exception within actionable set) |
| `task_model.py:55` (`TaskType`)                  | 8 values              | Reduce to 5: goal, project, epic, task, learn      |

### `all_tasks()` must filter by type

Currently:

```rust
pub fn all_tasks(&self) -> Vec<&GraphNode> {
    self.nodes.values()
        .filter(|n| n.task_id.is_some())  // Too broad — includes notes, contacts
        .collect();
```

After:

```rust
pub fn all_tasks(&self) -> Vec<&GraphNode> {
    self.nodes.values()
        .filter(|n| {
            n.task_id.is_some()
                && n.node_type.as_deref()
                    .map(|t| ACTIONABLE_TYPES.contains(&t))
                    .unwrap_or(false)  // Untyped nodes with task_id: exclude for safety; migrate via Phase 2
        })
        .collect();
```

## Migration

### Phase 1: Code changes (mem repo)

1. Update `ACTIONABLE_TYPES` to the 5-type list: `goal, project, epic, task, learn`
2. Fix `task_search` to use `ACTIONABLE_TYPES.contains()` instead of hardcoded filter
3. Fix `all_tasks()` to filter by `ACTIONABLE_TYPES`
4. Fix `is_treemap_type()` to use `ACTIONABLE_TYPES`
5. Update Python `TaskType` enum to match
6. Add `classification` field to `GraphNode` struct (optional string, read from frontmatter)

### Phase 2: Data migration (PKB)

Reclassify existing non-canonical types to `type: task` + `classification`:

| Current            | Count | Migration                                 |
| ------------------ | ----- | ----------------------------------------- |
| `type: bug`        | 127   | → `type: task, classification: bug`       |
| `type: feature`    | 52    | → `type: task, classification: feature`   |
| `type: action`     | 45    | → `type: task, classification: action`    |
| `type: subproject` | ~0    | → `type: project`                         |
| `type: milestone`  | ~0    | → `type: epic, classification: milestone` |

This can be done via `aops lint --fix` after updating the linter's type alias resolution.

### Phase 3: Linter enforcement

Add lint rule: if `type` is not in `VALID_NODE_TYPES` (the reduced canonical set), emit error.

Update `resolve_type_alias` to handle the retired actionable types:

```rust
fn resolve_type_alias(t: &str) -> (&'static str, Option<&'static str>) {
    // Returns (canonical_type, optional_classification)
    match t {
        "bug" => ("task", Some("bug")),
        "feature" => ("task", Some("feature")),
        "action" => ("task", Some("action")),
        "subproject" => ("project", None),
        "milestone" => ("epic", Some("milestone")),
        // ... existing reference aliases unchanged
    }
}
```

## User Expectations

### Work Item Management

- **Unified Visibility**: Users expect `task_search` and `list_tasks` to return ALL work items, including bugs, features, and learning tracks, without needing to guess which specific type a work item was filed under.
- **Clean Task Lists**: Users expect task management tools to show only work to be done, never cluttering results with research notes, meeting transcripts, or contact information.
- **Hierarchical Clarity**: While the canonical hierarchy is slightly flattened (Action/Bug/Feature absorbed into Task), users expect to still see a clear relationship from Goal → Project → Epic → Task, with `classification` (e.g., `action`) providing the necessary granularity for session-sized work.

### Knowledge Organization

- **Canonical Consistency**: Users expect the system to automatically suggest or fix non-canonical types (e.g., `insight` -> `note`) to keep the knowledge base organized and searchable.
- **Clear Boundaries**: Users expect a sharp distinction between _reference_ material (knowledge artifacts) and _actionable_ material (work to be done), ensuring that a research note never accidentally appears as a blocked task.

### Implementation Status (Audit Assessment)

- **What Works**: Basic hierarchical task graph and searching for the core `task`, `project`, and `goal` types. The foundational infrastructure for `ACTIONABLE_TYPES` exists in the Rust layer.
- **Missing**:
  - **Cross-Layer Sync**: Python `TaskType` and Rust `ACTIONABLE_TYPES` are out of sync; the Python side still maintains retired types as top-level enums.
  - **Visibility Gaps**: Many work items (`bug`, `feature`, `action`) are currently invisible to search or buried in noise because they aren't yet unified under the `ACTIONABLE_TYPES` constant in all search/list operations.
  - **Metadata Standardization**: The `classification` field is not yet universally parsed or displayed across the dashboard, TUI, and CLI.
- **Aspirational**: Full automated migration of existing data using `aops lint --fix` and a unified single-source-of-truth for types across the entire Rust/Python stack.

## Acceptance criteria

1. `task_search("anything")` returns results with type `bug`, `feature`, `action`, `epic`, `learn` — not just `task|project|goal`
2. `list_tasks()` does NOT return notes, contacts, or knowledge entries
3. All five layers use the same `ACTIONABLE_TYPES` constant (no hardcoded filters)
4. Existing `type: bug` files still work correctly (either via migration or alias resolution at query time)
5. `ready_tasks()` still excludes `learn` type
6. TUI task tree and treemap show all actionable types
7. No regressions in existing tests

## Risks

- **Data migration blast radius**: 224 files changed (bug + feature + action). Mitigated by: linter `--fix` with dry-run, git diff review before commit.
- **Downstream consumers**: Dashboard, TUI, and CLI may filter on specific type strings. Mitigated by: Phase 1 code changes use the constant, not string literals.
- **Semantic loss**: If `type: bug` becomes `type: task`, agents lose the ability to filter by type alone. Mitigated by: `classification` field preserves the distinction; `list_tasks` could gain a `classification` filter parameter.

## Out of scope

- Reclassifying the 55 `knowledge` items (they may be correctly typed)
- Reclassifying the 52 `review` items (need human judgment: are they review tasks or review notes?)
- Adding `classification` as a filter parameter to MCP tools (nice-to-have, separate PR)
