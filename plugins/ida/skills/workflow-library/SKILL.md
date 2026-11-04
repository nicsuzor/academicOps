---
name: workflow-library
description: List, read, add, edit, and retire workflow templates across project, PKB, and universal tiers, or preview composition without minting tasks. Exclude when tracking running jobs (use harness progress tools).
---

# Workflow Library

Manage composable workflow templates (`type: template`) across three resolution tiers.

## Foundational Structural Invariants

Every workflow composed across all tiers must adhere to two universal invariants:

1. **Decision Step on Design Research Invariant:** Every research task investigating an open design question, architectural pattern, technology evaluation, or implementation trade-off must, by default, include a dependent decision task assigned to the user (`assignee: user`) that depends on the research artifact. In this decision task, the user selects the implementation route. Downstream implementation tasks are strictly blocked on this decision task.
2. **Review and Follow-Up Structural Placement Invariant:** Every task requiring a review, verification, or subsequent follow-up step must be structured in exactly one of two valid topological patterns:
   - **Single Task with Internal Subtasks:** If all steps (e.g. build, local verification, documentation) can be executed by the same agent in one continuous session, they must remain internal subtasks (checklist items) within a single task body.
   - **Dedicated Epic with Child Tasks:** If the steps require independent sessions, clean execution context, distinct reviewer personas (`pauli`, `rbg`, `marsha`), different tool boundaries, or human decision gates, the work must be structured as a dedicated epic containing separate child tasks (e.g. Child 1: Primary Task, Child 2: Review / Decision / Follow-up), with dependencies explicitly wired between children (`Child 2` `needs: [Child 1]`).
   - **Prohibition:** A task and its subsequent follow-up or review step must never be created as loose siblings under an external parent.

## Tiers and Resolution

Resolution order is **Project > PKB > Universal**. Higher tiers shadow lower tiers completely; never merge text across tiers.

| Tier | Location | Enumeration |
| - | - | - |
| 1. Project | PKB templates whose `project` is the task's project | Query PKB templates (`type: "template"`, `project: "<project>"`, including completed nodes) |
| 2. PKB | PKB templates with no `project` | Query PKB templates (`type: "template"`, including completed nodes), keep `project: null` |
| 3. Universal | `${CLAUDE_SKILL_DIR}/workflows/` | `Glob ${CLAUDE_SKILL_DIR}/workflows/*.md` |

The project is the `project` field of the task being composed for, or the project the caller names. With neither, the project tier is empty for composition. Templates scoped to any other project are out of scope for composition, but visible in list mode.

A project template's id is `<project>-<slug>`, so the same slug can exist in several projects. Strip the `<project>-` prefix to get the slug that shadows lower tiers.

Both PKB tiers resolve from the graph alone, so a session needs no checkout of the project's repository. A repository's `.agents/templates/` directory is not a tier.

Enumerate and read universal templates using file tools (`Glob`, `Read`) rather than `Bash`, so resolution succeeds under non-interactive and `dontAsk` permission modes.

## Modes

### list

Enumerate every template across all three tiers live. Return a unified table: **slug \| tier \| coverage \| status**.

- Include every universal template file (`${CLAUDE_SKILL_DIR}/workflows/*.md`) and every PKB template from the graph (`type: "template"`).
- For PKB templates with a `project` field, indicate their project scope in the tier column (e.g. `Project (brain)`). Foreign-project templates are displayed with their project prefix or formatted as `Project (<name>)` in the tier column without altering composition scoping.
- Extract coverage from `description` in frontmatter, or, if that is missing, from the first sentence of `## What this step does`. Read universal template files directly via `Read`; do not run `Bash` loops.
- Filter out dated instances (`-*-\d{8}-*`) and `status: cancelled`. Do not filter out foreign-project templates.
- Flag shadowed slugs and templates missing coverage lines.

### view

Resolve the template slug across tiers in precedence order. Output the winning content, identify winning and shadowed tiers, or list near-misses if missing.

### new

1. Check existing library to avoid duplicating covered workflows.
2. Select destination tier:
   - **Project**: Specific to one project. Write it to the PKB with `project: <project>` and id `<project>-<slug>`.
   - **PKB**: Portable personal workflow. Write it to the PKB with no `project`.
   - **Universal**: Core baseline standard across projects (`${CLAUDE_SKILL_DIR}/workflows/`).
3. Author the template following `ida:craft` (`## Workflow Templates`), which is the authoritative style, schema, and authoring standard across all tiers. Compliance with its contract separation, headless worker execution, approval boundary, and deliverable rules is mandatory.

### edit

Update existing templates in place. Authoring changes must comply with `ida:craft` (`## Workflow Templates`).

- **Universal**: Edit the file directly.
- **PKB**: Update only the markdown body below the closing `---` in the PKB node to prevent frontmatter duplication.

### preview

Simulate composition for a stated objective at one of two depths. Never write tasks or mutate the graph; mark the output as a non-minted preview.

- **stage depth** (what `/decompose` asks for): return the composite that covers this class of work as its ordered stages, each with its input and output contract, unresolved. A stage whose filling is a choice among methods, frames or venues stays a named slot; do not pick for it or expand it into steps.
- **step depth** (what `/reify` asks for): resolve each stage to the templates and skills that fill it across the tiers and combine their steps into one logical sequence (e.g. test-first where the change modifies code that executes, build, then QA). Show the assembled steps and the resulting task brief shape.

Do not ad lib extra requirements or guess at scope; pass any ambiguity in the prompt through to the preview.

### retire

1. Search the PKB for tasks governing retirement. Halt if unfulfilled dependencies exist.
2. Delete the artifact (`rm` for universal files, or delete the PKB node).
3. Name the superseding workflow in the release message or commit.

## Constraints

- Query tiers dynamically; do not rely on static indices or memory.
- Query PKB templates at metadata/summary detail when enumerating lists, and read full bodies only for the target template under view, preview, or edit.
- Keep templates focused on obligations and exit criteria; leave operational method to skills.
- Do not mint tasks or dispatch work during library management operations.
