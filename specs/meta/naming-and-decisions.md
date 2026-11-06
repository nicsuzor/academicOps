---
id: naming-and-decisions
title: Task Naming, Filename Standards, and Graph-Relationship Decision Representation
type: spec
status: ready
tier: core
tags: [taxonomy, naming, graph-relationships, decisions, task-contract]
---

# Task Naming, Filename Standards, and Graph-Relationship Decision Representation

Authoritative specification for task names, filenames, and the structural representation of decisions on the strategic task graph.

- **Stated Purpose:** Establishes unambiguous, enforceable standards for naming tasks and files, resolves the root causes of the historical `<name>: decision: xyz` anti-pattern, and defines how decisions and questions emerge from graph relationships rather than static decision tasks.
- **Primary Audience:** Framework architects, planning agents (`pauli`, `ida`), dispatch engines, and human developers authoring or reviewing tasks, notes, and specs.
- **Current Truth / SSoT:** For task execution boundaries, see [`../enforcement/task-contract.md`](../enforcement/task-contract.md); for document classification, see [`doc-taxonomy.md`](doc-taxonomy.md).

## 1. Task Naming Standard

Tasks are actionable units of work. Their titles must communicate clear operational intent at a glance:

1. **Verb-Led Imperative:** Every task title begins with an active imperative verb describing the concrete outcome to achieve (e.g., `Implement X`, `Refactor Y`, `Verify Z`, `Extract A from B`).
2. **Brief and Descriptive:** Titles must be concise (typically 4–10 words) yet sufficiently descriptive that an executor or supervisor understands the objective without reading the body.
3. **No Person's Name in Titles or Filenames:** A task title, note title, or filename must **never** contain a person's name or moniker (e.g., `<name>: decision: ...`, `<name>-task-...`, `for-<name>.md`). Assignment and human involvement belong exclusively in frontmatter metadata fields (`assigned_to:`, `assignee:`).
4. **No Artificial Type Prefixes:** Do not encode categories into titles (e.g., avoid `DECISION: ...`, `PROBE: ...`, `TASK: ...`). Node taxonomy and classification are expressed through frontmatter (`type:`, `classification:`) and graph topology.

## 2. Filename Standard

Filenames identify files within repositories and knowledge bases:

1. **Kebab-Case:** All lowercase alphanumeric characters separated by hyphens (e.g., `doc-taxonomy.md`, `task-contract.md`).
2. **Purpose-Driven and Descriptive:** Names reflect what the file contains or accomplishes, not historical circumstance or author identity.
3. **No Person's Name:** Filenames never include individual names or personal prefixes.
4. **Appropriate Directory Placement:** Files reside in directories defined by [`doc-taxonomy.md`](doc-taxonomy.md) (`specs/`, `plugins/`, `lib/`, `.agents/`).

## 3. Root-Cause Analysis & Resolution of "<name>: decision: xyz"

### Forensic Root Cause

Historical forensic evidence from the PKB establishes that titles shaped like `<name>: decision: xyz` emerged from three compounding systemic factors:

1. **Legacy Prompt Doctrine:** An early rule in `.agents/CORE.md` (recorded 2026-08-13) explicitly instructed agents: that every question to the user must be filed as a decision node assigned to the user, with the chat sentence as the notification and the node as the record. Agents took this instruction literally and began prefixing task titles with the user's name followed by `decision: ...`, or with `DECISION (<name>): ...`.
2. **Capability Grant & Suppression Gap:** When interactive asking tools (`AskUserQuestion`) were temporarily omitted from agent tool grants or suppressed by agent heuristics against interrupting, agents fell back to dumping questions onto the graph as static tasks.
3. **Absence of a Drain Mechanism:** Decision tasks accumulated indefinitely on the graph (~25 stale open nodes), stalling workflows and creating noise without ever driving execution.

### Resolution at the Source

1. **Abolition of Un-actionable Decision Tickets & Preservation of Design Decision Gates:** Standalone "decision" tasks filed as holding bins for open conversational questions are strictly prohibited across all prompts, skills, and documentation. In contrast, structured decision tasks assigned to the user that resolve an explicit design research fork and unblock downstream implementation are authorized and mandatory for design research workflows, operating in harmony with option-node branching (§4).
2. **Proper Field Separation:** Identity and assignment are strictly confined to `assigned_to:` / `assignee:`.
3. **Direct Interactive Resolution:** Interactive, in-session questions are asked immediately via `AskUserQuestion` rather than converted into backlog items.

## 4. Graph-Relationship Decision Representation

Decisions and open questions are structural properties of the graph, not static todo-list items. In accordance with ADR [[spec_e6d668b0]] (Unified Three-Relation Graph Model and Value Propagation):

```mermaid
flowchart TD
    Scoping["Scoping Task / ADR\n(Candidate options in body)"] --> Decision{"Option Chosen"}
    Probe["Empirical Probe\n(classification: probe)"] -.->|needs| Scoping
    Decision --> Chosen["Adopted Task\n(parent: scoping_id)"]
    Chosen --> Downstream["Downstream Implementation\n(needs: chosen_id)"]
```

### Representation Principles

1. **Candidate Options Remain in Task Bodies (Retirement of Option Nodes & `alternative`):**
   - Competing candidate options stay inside the body of the scoping task or ADR until chosen (retiring separate unchosen option nodes and `alternative` edges).
   - A task that has options to choose between is created as a single task with the candidate choices and evaluation criteria inside the task body.
   - When a choice is made, only the selected option is reified into an actionable task under `parent: <scoping_task_id>`. This prevents speculative unassigned task proliferation and prevents unchosen option nodes from cluttering the graph or blocking parent completion.
2. **Dynamic Emergence of Decisions:**
   - Architectural decisions are surfaced dynamically by agents inspecting scoping tasks with open options on the critical path rather than by querying a bucket of stale "decision" tickets.
3. **Empirical Unknowns as Probes Valued via `needs`:**
   - Where a decision depends on missing runtime benchmarks, data, or empirical findings, mint an empirical probe task (`classification: probe`, e.g. `Benchmark SQLite vs DuckDB query latency`). Wire the probe directly into the waiting task via standard execution prerequisite `needs: [<probe_task_id>]`.
   - The probe receives worth directly through prerequisite backward induction via `needs` with Target-level $\max$ deduplication. Dedicated `settles` edges and `decision_value` EVPI calculations are retired.
4. **Resolution by Reification:**
   - Deciding an option consists of recording the decision in the scoping task/ADR and reifying the winning implementation task under `parent: <scoping_task_id>`. Downstream tasks depend on the reified implementation task via `needs`.

## 5. Task Body Brevity, Structure, and Canonical Template

Task bodies are executable instructions for cold executors, not project diaries, architectural essays, or discussion forums.

### Rules of Task Body Authoring

1. **Strictly Concise:** Task bodies are 50–150 words for atomic tasks (up to ~300 words for complex multi-outcome briefed units).
2. **No Extraneous Sections:** Never add sections such as `Background`, `Narrative`, `References`, `Contextual Analysis`, `Task History`, or `Implementation Plan`.
3. **No Prose Task Links:** Never link other tasks from within the body (e.g. no "blocks #123" or "relates to task X"). Task relationships live exclusively as upward graph edges (`parent`, `needs`, `serves`, `supersedes`).
4. **Pointers Point to Knowledge, Not Tasks:** `[[wikilinks]]` in a task body point solely to durable knowledge (specs, notes, references) that the executor must consult, with a ≤1-clause statement of purpose.

### Canonical Task Template

```markdown
## Goal

1. Concrete outcome 1
2. Concrete outcome 2

## Deliverable

`path/to/artifact`

## Scope

- In: Concrete inclusion
- Out: Adjacent exclusion (no rationale)

## Acceptance criteria

- [ ] Observable end-state condition 1
- [ ] Observable end-state condition 2

## Pointers

- [[spec_or_note_id]] -- purpose (e.g. "schema contract", "precedent")
```

### Concrete Example

```markdown
## Goal

1. Migrate configuration loader to Pydantic v2 settings model.
2. Deprecate legacy dict-based config parser.

## Deliverable

`lib/config/loader.py`

## Scope

- In: `Settings` class validation and env var mapping.
- Out: CLI flag parsing (handled in `cli.py`).

## Acceptance criteria

- [ ] `Settings.from_env()` loads valid config from environment variables.
- [ ] Invalid config raises structured `ValidationError`.
- [ ] All existing config unit tests pass.

## Pointers

- [[spec_or_note_id]] -- schema contract
```

## 6. Graph Edge Economy & Hierarchy Invariant

Graph density means meaningful semantic and causal connectivity, not redundant combinatorial wiring:

1. **Parent/Child is Already an Edge:** Setting `parent_id` on a node automatically places and connects it within the parent's hierarchy.
2. **No Redundant Descendant Wiring:** Do **not** wire edges between siblings or descendants under the same parent unless there is a specific, verifiable interaction (such as an explicit causal prerequisite `needs`, `supersedes`, or cross-branch data flow).
3. **Density Means Causal and Strategic Edges:** Densify the graph by wiring edges carrying the three-relation contract (`parent`, `needs`, `serves`; with `quantum`, `probability`, `effect`, `justification`, `set_by: agent-proposed`). Contextual references are plain markdown `[[wikilinks]]` in `## Pointers`.
4. **Review and Follow-Up Placement Invariant:** Every task requiring review or follow-up must be structured either as a single task with internal subtasks (if executable by the same agent in one session) or as a dedicated epic with separate child tasks (if multi-session or independent context is required); never as loose siblings under an external parent.
