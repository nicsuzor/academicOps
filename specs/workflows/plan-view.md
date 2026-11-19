---
title: Plan view for decomposition
status: ready
---

# Plan view for decomposition

A formal visual and tabular overview written to an objective's top-level task during decomposition, enabling readers to inspect and evaluate the planned process--including the balance of research, build, and review--without reading individual task bodies.

## User stories

### US-1 Process inspection at objective altitude

As a task supervisor or reviewer, I want to see a structural map of the planned process on the top-level task, so that I can immediately judge whether the plan strikes the right balance between discovery, implementation, and verification before dispatching work.

- **AC-1.1** Given a top-level task decomposed into child tasks, when decomposition completes, then the top-level task contains a `## Plan` section displaying the planned workflow stages, task dependencies, and composed workflow templates.
- **AC-1.2** Given a plan view on a top-level task, when an observer inspects the plan view, then the plan view displays only structural process and dependency relationships, and contains no task state, execution status, progress metrics, or assignee names.

### US-2 Template selection by preference and default

As a user with a preferred plan visualization style, I want decomposition to use my specified template or fall back to the marked default template without hardcoding template names in instructions, so that visualization formats can be customized or extended without modifying the decomposition skill.

- **AC-2.1** Given an explicit plan-view template specified by the user, when decomposition renders the plan view, then it selects and applies the user-specified template.
- **AC-2.2** Given no plan-view template specified by the user, when decomposition renders the plan view, then it discovers templates tagged `plan-view` and selects the template whose frontmatter specifies `default: true`.
- **AC-2.3** Given decomposition instructions, when inspected, then the instructions identify the template through the `plan-view` tag and `default: true` frontmatter marker rather than hardcoded template names or identifiers.
- **AC-2.4** Given a missing user-specified template, an absence of any `plan-view` templates, or conflicting multiple `default: true` templates, when decomposition runs, then the process halts loudly with an explicit error rather than silently defaulting or guessing.

### US-3 Synchronized redrawing on re-runs

As an iterative planner, I want decomposition to redraw the plan view in place whenever sub-objectives, forks, or dependencies change, so that the top-level task always reflects the latest state of the plan without stale remnants.

- **AC-3.1** Given an existing `## Plan` section on a top-level task, when decomposition is re-run with added detail or modified nodes, then the entire `## Plan` section is replaced with an updated plan reflecting the current graph structure.
- **AC-3.2** Given a re-drawn plan view, when compared to the active task tree, then every current descendant task appears in exactly one box and every active dependency appears as an edge.

## Design

### 1. Conceptual boundary and Single Source of Truth

The plan view is strictly structural:

- It maps the planned stages, step sequence, workflow template compositions, and dependency flow.
- It intentionally excludes dynamic task state (`status`, `assignee`, execution duration, progress). Dynamic state belongs exclusively on individual task records and live dashboards to prevent split-brain state and violations of single source of truth.

### 2. Template discovery and selection contract

Decomposition selects the rendering template through tag and frontmatter metadata:

1. **User override:** If the user specifies a template name or identifier in the decomposition prompt or parameters, that template is used. If the specified template cannot be resolved, execution halts loudly naming the missing template.
2. **Default selection:** If no template is named by the user, decomposition queries templates tagged `plan-view` and selects the one with `default: true` in its frontmatter. If no template carries the tag, or if multiple templates carry `default: true`, execution halts loudly naming the ambiguity or absence.
3. **Decoupled skill:** The decomposition skill contains no hardcoded template identifiers or names, preserving modularity and runtime composition.

### 3. Plan-view components

The default plan view comprises four synchronized elements within the top-level task's `## Plan` section:

1. **Stage strip:** An ordered listing of the backbone workflow stages, indicating which stages are filled by the decomposed steps.
2. **Mermaid dependency flowchart:** A left-to-right directed graph where each node represents a decomposed step (displaying a short slug label and its task identifier) and edges represent hard dependencies (`depends_on`).
3. **Workflow template colour mapping:** Nodes in the diagram are styled or grouped by the primary workflow template they are composed from (with an accompanying legend), highlighting the distribution between research, build, review, and verification.
4. **Summary table:** A structured table itemizing each step's slug, task identifier, stage, composed template, and prerequisite steps.

### 4. Idempotent in-place redrawing

Each run of decomposition treats the `## Plan` section as an atomic, derived projection:

- The section begins with `## Plan` and is completely rewritten on every run.
- When nodes are added, collapsed, merged, or reparented, re-running decomposition walks the current descendant tree and emits a fresh diagram and table.

### 5. Enforcement pyramid and proportionality analysis

Per framework enforcement architecture, the mechanism for steering decomposition to generate plan views was evaluated across the enforcement pyramid options from least-invasive to most-invasive:

1. **`doctrine only`**: Rejected. Broad declarations that plans should be transparent do not provide operational guidance for generating structured sections during decomposition runs.
2. **`instructions` (`imperative`)**: Selected. Adding an imperative procedural step to the decomposition skill (`plugins/ida/skills/decompose/SKILL.md`) directs executing agents to discover the default or requested template and render the plan view. This satisfies the "default to instructions" mandate with zero tooling overhead.
3. **`JIT injection`**: Rejected. Executing agents already load the decomposition skill; injecting duplicate runtime prompts on task creation introduces redundant token cost.
4. **`structural`**: Rejected. Mechanical graph-rendering hooks or deterministic markdown injectors would add rigid, high-maintenance code, violating agentic-first principles and prohibitions against over-engineered builds.
5. **`process`**: Selected for validation. Downstream QA and review lenses verify the presence and fidelity of the rendered plan view without requiring mechanical runtime enforcement.
6. **`post-hoc`**: Maintained. Task version history in the knowledge base and repository records preserve prior plan states.

### 6. Enforcement map extract

The live enforcement register (`specs/ENFORCEMENT-MAP.md`) records the following extract:

```markdown
| [Skill: Decompose](../plugins/ida/skills/decompose/SKILL.md) -- Write and redraw a plan graph on the top-level task via the default or user-named plan-view template, showing planned process only without task status. | instructions | imperative | `plugins/ida/skills/decompose/SKILL.md:37-40`: Each `/decompose` run selects the user-specified or default `plan-view` template (without hardcoded names) and renders the stage strip, dependency graph, legend, and summary table on the top-level task, redrawing in place on re-runs; status is omitted to preserve SSoT (`specs/workflows/plan-view.md`). Instruction-sharpening move on user request to inspect planned process without opening individual task bodies. Observation: Top-level tasks carry structural plan views redrawn on each pass without status duplication. |
```

- **Evidence for the move:** User feedback in iterative planning sessions demonstrated that supervisors could not evaluate whether a decomposition balanced research, build, and review without opening every child task record. Restricting the plan view to static process structure preserves Single Source of Truth while providing immediate objective-level clarity.

## Outcome-level build criteria

When implementing the plan-view step in decomposition instructions (in follow-up build work), the implementation must satisfy the following outcome-level build criteria:

- **BC-1 (Template Selection and Fail-Fast):** Decomposition instructions require selecting the user-named plan-view template if specified, or discovering templates tagged `plan-view` and selecting the one carrying `default: true` in frontmatter; execution halts loudly on missing templates, absent tags, or ambiguous multiple defaults; the skill instructions contain no hardcoded template name or identifier.
- **BC-2 (Rendered Plan View):** Decomposition instructions require rendering a `## Plan` section on the top-level task containing the stage strip, Mermaid dependency graph, workflow color legend, and summary table derived from descendant tasks.
- **BC-3 (Status Exemption):** The rendered plan view contains no task status, assignee, or progress information, maintaining single source of truth on child tasks.
- **BC-4 (In-Place Redraw):** Decomposition instructions require completely replacing any existing `## Plan` section on subsequent runs to reflect added detail and graph revisions.
- **BC-5 (Enforcement Alignment):** `specs/ENFORCEMENT-MAP.md` records the imperative instruction for decomposition plan-view rendering under `## Agent instructions` once the skill modification is completed and verified in Stage 2.
