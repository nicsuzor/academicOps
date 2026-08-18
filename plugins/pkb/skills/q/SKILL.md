---
name: q
type: command
description: Stage 1 Intake & Capture — place an ask, fragment, or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake, leaving status at inbox with NO acceptance criteria.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search, mcp__services__pkb__pkb_context]
---

# /q — Quick Queue (Stage 1: Intake & Capture)

Invoke `pauli` to silently capture, place, and densify the user's intent on the task graph by creating or updating one or more tasks in the `inbox` state.

`/q` executes **Stage 1 (Intake, Placement & Densification)** of the task pipeline:

- **Place under an appropriate parent node**: Identify the right parent (epic, target, or active task). Do not insert new tasks under complete or stale parent nodes.
- **Never park tasks in a catch-all, and never leave them unparented.** Everything belongs somewhere real on the graph. A node with no parent is an orphan the next sweep has to chase, and a junk-drawer parent is an orphan that does not show up as one — which is worse.
- **Wire graph relationships**:
  - Add a `contributes_to` edge to the target or goal this work actually serves, with a verbal weight and one sentence of justification.
  - Wire `depends_on` for known hard blockers and `soft_depends_on` for context/informational relationships.
- **Densify with wikilinks**: Include `[[wikilinks]]` in the body to related nodes, prior attempts, and relevant documentation. The graph should come out denser, not just longer. A task whose only edge is its parent has been dumped, not placed.
- **Strategic Valuation at intake**: Record initial estimates across strategic dimensions:
  - **Marginal career benefit**: The specific publication, grant, credential, or career milestone advanced.
  - **Synergies**: Cross-project or cross-workstream reuse of methods, datasets, or findings.
  - **Value of Information (VoI)**: How much this reduces uncertainty on critical downstream assumptions (`uncertainty` / `classification: spike`).
  - **Effort & downstream unblocking**: High-level initial calibration without fabricating precision.
- **NO ACCEPTANCE CRITERIA**: Stage 1 leaves the task at `inbox` with **NO acceptance criteria (AC)** and no process composition. Acceptance criteria, review nodes, and process checklists belong strictly to Stage 2 (`brief`). An `inbox` task without AC is non-dispatchable by design.
- **Fast capture path**: Very fast, hastily jotted fragments or raw notes can be captured minimally first via the incoming capture path, then situated and densified under `/q`.

**RETURN Task ID and title** in the following format:

```
- Queued [TASK-ID] - [TASK-TITLE] (under [PARENT TASK-ID]) [inbox]
... [ Repeat if necessary ]
```
