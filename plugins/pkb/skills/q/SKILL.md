---
name: q
type: command
description: Stage 1 Intake & Capture -- place an ask, fragment, or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search, mcp__services__pkb__batch_reparent]
---

# /q -- Situate an ask on the graph, well-connected and weighted

Capture short natural-language prose describing a complex, dense objective, and situate it on the strategic graph: under the right parent, wired to what it serves, weighted by what it is worth, and dense with links to its neighbours.

Capture and placement only. You do not expand an ask into its components, name its forks, compose its process, or release it for dispatch.

## Workflow

1. **Pick the level.**

   | Signal                                       | Level                                          |
   | -------------------------------------------- | ---------------------------------------------- |
   | Desired future state, identity-scale         | Goal -- outside the tree                       |
   | Countable milestone, done or not done        | Target -- outside the tree, carries the stakes |
   | Bounded body of work with real sub-structure | Epic, parented to the epic or area it serves   |
   | One verifiable unit, one session             | Task, parented to the epic it belongs to       |
   | High uncertainty, information needed first   | Task with `classification: spike`, same parent |

2. **Name the task with a verb-led imperative.**
   Task titles must be brief, descriptive, verb-led statements of a thing to achieve (e.g. `Implement X`, `Verify Y`, `Refactor Z`). **Never include a person's name in a title or filename** -- assignment belongs exclusively in the `assigned_to` frontmatter field.

3. **Place it under a real parent.**
   Identify the right parent -- epic, target, or active task -- and never insert new work under a complete or stale parent. **Never park a task in a catch-all, and never leave it unparented.** An unparented node is an orphan the next sweep has to chase; a junk-drawer parent is an orphan that does not show up as one, which is worse.

   `project` comes from the parent; where re-parenting moves a node to a different project, move the slug with it. If the right parent is genuinely ambiguous between two live candidates -- not merely unclear at a glance -- put the choice to the user. Do not flip a coin.

4. **Idempotent capture: Adopt existing work rather than duplicating it.**
   Before creating a new task, always search the graph context to see if a matching task already exists. If you find an existing match, **do not add a new duplicate task**. Instead, check the graph context, update the existing task with any new information from the ask, and place it correctly. Our goal is to clear out tasks eventually, and we certainly don't want duplicate and stale tasks lying around.
   Where unparented, misparented, or pre-existing tasks already cover the idea, adopt them under the parent with `pkb__batch_reparent(ids=[...], new_parent="<parent-id>", dry_run=False)` instead of creating duplicate nodes. Mint slugged, human-readable IDs upfront (`id: "aops_<slug>"`) rather than leaving `id` empty for auto-generation.

   **Handle disorganisation immediately (Keep it DRY):** If you find any disorganisation, duplication, or structural graph issues while placing the task, immediately consolidate. Kick off to another skill (like `reconcile` or a structural cleanup skill) if one is specially adapted to cleaning structural graph issues.

5. **Record** the task:
   The task you produce should be a straightforward edit and translation of your input.
   - This is not the time for investigation; quickly record the user's ask and return.
   - Leave ambiguity in the task; a later stage will resolve it with additional detail. Your role is only to make sure the task is recorded and placed correctly on the graph.

6. **Densify: Wire the edges.**
   - `contributes_to` the target or goal this work actually serves, with a verbal `stated_weight` (`critical`, `high`, `medium`, `low`) and one sentence of justification ([[kb_pauli_prioritisation_doctrine]]).
   - `depends_on` for known hard blockers, `soft_depends_on` for context or informational relations, `supersedes` where this replaces prior work.

   Wire an edge to every neighbour you confirmed by opening -- related work, prior attempts, what this supersedes. **The graph should come out denser, not just longer.** A task whose only edge is its parent has not been placed, it has been dumped.

   - **Parent/child is already an edge:** Setting `parent_id` automatically places the node in the parent tree. Do **not** wire redundant edges to other descendants or siblings under the parent unless there are specific, genuine interactions (such as a sequential dependency `depends_on`, `supersedes`, or cross-branch data flow).
   - **Density is edges, never prose:** A task body never links another task and never describes its relation to one: that structure is the edge, and a prose copy of it goes stale while the edge stays correct. `[[wikilinks]]` in a body point at knowledge the executor must open -- notes, references, documentation.

7. **Value it at intake.**
   Record initial estimates, populating only what you actually established. Do not fabricate precision the ask does not support.
   - **Marginal benefit** -- the specific publication, grant, credential, capability, or career milestone advanced.
   - **Synergies** -- cross-project or cross-workstream reuse of methods, datasets, or findings.
   - **Value of Information** -- how much this reduces uncertainty on critical downstream assumptions (`uncertainty`, `classification: spike`).
   - **Effort and downstream unblocking** -- high-level initial calibration, plus the `consequence` of failure on a target.

   **`focus_score` is computed by the graph engine, and you never write it.** You influence it only by wiring edges.

## Output

```
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT TASK-ID])
... [ Repeat if necessary ]
```

## Must NOT

- Do not create standalone "decision" tasks or file questions as tasks. Decisions between architectural choices are represented as mutually exclusive or mutually blocking option nodes where choosing one branch resolves the conflict, and missing information is modelled as a probe task (`classification: spike`). In-turn questions are put directly via `AskUserQuestion`.
- Do not put a person's name in a title or filename (no `nic: ...`, `nic-task-...`); assignment is expressed solely via `assigned_to` frontmatter.
- Do not write `intent` (or legacy `priority`). Intent is Nic's personally curated ranking, not an agent estimate; new work sits at the uncurated default band unless Nic directed otherwise in this turn ([[kb_ccc17177]]). Express strategic importance by wiring `contributes_to` with `stated_weight`; only `pauli` authors `stated_weight` ([[kb_pauli_prioritisation_doctrine]]).
- Do not set `severity` on anything that is not a `type: target` node -- severity is target-only magnitude.
- Do not manufacture a `due` date to carry urgency. `due` means a real external deadline.
- Do not release work for dispatch at intake. Intake leaves a node at `inbox`.
- Do not expand the ask into components, name its forks, or mint probes. That is the next stage.
