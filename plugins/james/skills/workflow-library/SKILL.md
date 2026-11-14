---
name: workflow-library
description: Manage, inspect, author, edit, and retire composable workflow templates across Project, PKB, and Universal tiers. Use for workflow template library maintenance, authoring, and lifecycle operations. Exclude for runtime workflow composition during task execution (use james:supervise) or tracking running jobs.
---

# Workflow Library

Manage composable workflow templates (`type: template`) across three resolution tiers.

## Workflow Composition Redirect

Runtime workflow composition is handled inline by `james:supervise`. To assemble workflow templates and skills dynamically during task execution, invoke `/james:supervise`. This skill (`james:workflow-library`) manages template library artifacts and PKB template nodes.

## Tiers and Resolution

Resolution order is **Project > PKB > Universal**. Higher tiers shadow lower tiers completely; never merge text across tiers.

| Tier | Location | Enumeration |
| - | - | - |
| 1. Project | PKB templates whose `project` is the task's project | Query PKB templates (`type: "template"`, `project: "<project>"`, including completed nodes) |
| 2. PKB | PKB templates with no `project` | Query PKB templates (`type: "template"`, including completed nodes), keep `project: null` |
| 3. Universal | `workflows/*.md` inside this skill directory | Enumerate `workflows/*.md` via native file tools |

The project is the `project` field of the task or the project the caller names. Templates scoped to any other project are out of scope for composition, but visible in list mode. When a target repository has no project-tier templates or local `.agents/rules/`, resolution proceeds cleanly from PKB and Universal tiers.

A project template's id is `<project>-<slug>`, so the same slug can exist in several projects. Strip the `<project>-` prefix to get the slug that shadows lower tiers.

Both PKB tiers resolve from the graph alone, so a session needs no checkout of the project's repository. A repository's `.agents/templates/` directory is not a tier.

Enumerate and read universal templates using native file tools rather than shell commands, so resolution succeeds under non-interactive permission modes.

## Modes

### list

Enumerate every template across all three tiers live. Return a unified table: **slug | tier | coverage | status**.

- Include every universal template file (`workflows/*.md` in this skill directory) and every PKB template from the graph (`type: "template"`).
- For PKB templates with a `project` field, indicate their project scope in the tier column (e.g. `Project (<name>)`). Foreign-project templates are displayed with their project prefix or formatted as `Project (<name>)` in the tier column without altering composition scoping.
- Extract coverage from `description` in frontmatter, or, if that is missing, from the first sentence of `## What this step does`. Read universal template files directly via file tools; do not run shell loops.
- Filter out dated instances (`-*-\d{8}-*`) and `status: cancelled`. Do not filter out foreign-project templates.
- Flag shadowed slugs and templates missing coverage lines.

### view

Resolve the template slug across tiers in precedence order. Output the winning content, identify winning and shadowed tiers, or list near-misses if missing.

### new

1. Check existing library to avoid duplicating covered workflows.
2. Select destination tier:
   - **Project**: Specific to one project. Write it to the PKB with `project: <project>` and id `<project>-<slug>`.
   - **PKB**: Portable personal workflow. Write it to the PKB with no `project`.
   - **Universal**: Core baseline standard across projects (`workflows/` inside this skill directory).
3. Author the template (`type: template`) following the workflow-template authoring contract across all tiers:
   - Frontmatter: `title`, `type: template`, `description` (one line describing coverage for runtime selection), and `tags`.
   - **Contract over neighbour**: Define input and output contracts per stage; never name or chain to another template slug in frontmatter or body.
   - **Headless execution & approval boundaries**: Never pause or prompt mid-task; end approval boundaries cleanly as `partial` with dependent work blocked until approval is recorded.
   - **Deliverables & naming**: List only artifacts and state the executing agent produces; prefix acceptance-blocking obligation templates with `wf-`; keep current-state only and target 30-60 lines (100-line ceiling).

### edit

Update existing templates in place following the workflow-template authoring contract above.

- **Universal**: Edit the file directly.
- **PKB**: Update only the markdown body below the closing `---` in the PKB node to prevent frontmatter duplication.

### retire

1. Search the PKB for tasks governing retirement. Halt if unfulfilled dependencies exist.
2. Delete the artifact (`rm` for universal files, or delete the PKB node).
3. Name the superseding workflow in the release message or commit.

## Constraints

- Query tiers dynamically; do not rely on static indices or memory.
- Query PKB templates at metadata/summary detail when enumerating lists, and read full bodies only for the target template under view or edit.
- Keep templates focused on obligations and exit criteria; leave operational method to skills.
- Do not mint tasks or dispatch work during library management operations. Runtime workflow composition belongs to `james:supervise`.
