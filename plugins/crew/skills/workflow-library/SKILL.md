---
name: workflow-library
description: Manage, inspect, author, edit, and retire composable workflow templates across project, PKB, and universal tiers. Use for workflow template library maintenance, authoring, and lifecycle operations. Exclude for assembling or composing workflows onto tasks (use /reify) or tracking running jobs (use harness progress tools).
---

# /workflow-library -- Composable Workflow Template Management

Manage composable workflow templates (`type: template`) across three resolution tiers. Workflow composition onto tasks belongs exclusively to `/reify`.

## Tiers and Resolution

Resolution order is **Project > PKB > Universal**. Higher tiers shadow lower tiers completely; never merge text across tiers.

| Tier | Location | Enumeration |
| - | - | - |
| 1. Project | PKB templates with `project: "<project>"` | Query PKB (`type: "template"`, `project: "<project>"`, including completed nodes) |
| 2. PKB | PKB templates with `project: null` | Query PKB (`type: "template"`, including completed nodes), keep `project: null` |
| 3. Universal | `workflows/*.md` inside this skill directory | Enumerate `workflows/*.md` via native file tools |

A project template ID is `<project>-<slug>`; strip `<project>-` to determine the shadowed slug. Templates scoped to foreign projects are out of scope for composition but shown in `list` mode. Both PKB tiers resolve from the graph alone without requiring a repository checkout.

## Modes

- **list**: Enumerate all templates live across all three tiers and emit **slug | tier | coverage | status**. Show project scope as `Project (<name>)`; extract coverage from frontmatter `description` (or first sentence of `## What this step does`); exclude dated instances (`-*-\d{8}-*`) and `status: cancelled`; flag shadowed slugs and missing coverage lines.
- **view**: Resolve a template slug in precedence order and output the winning content, shadowed tiers, or near-misses.
- **new**: Check existing coverage first, select destination tier (Project PKB with `project: <project>`, PKB with `project: null`, or Universal under `workflows/`), and author per `crew:craft` workflow-template standards.
- **edit**: Update templates in place per `crew:craft` workflow-template standards. Edit Universal files directly; for PKB nodes, update only the markdown body below the closing `---` to avoid frontmatter duplication.
- **retire**: Verify no unfulfilled governing tasks remain on the PKB, delete the file or PKB node, and name the superseding workflow in the commit or release message.

## Constraints

- Query tiers dynamically using metadata/summary detail for lists and full bodies only for `view`/`edit`; read universal templates with native file tools rather than shell loops.
- Keep templates focused on stage contracts, obligations, and exit criteria without naming neighbour templates; leave operational method to skills.
- Never mint tasks or dispatch work during library maintenance.
