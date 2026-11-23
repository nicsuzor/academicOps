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
| 1. Project | PKB templates with `frontmatter.project: "<project>"` | Query PKB `type: "template"` via batched summary reads; keep `frontmatter.project == "<project>"` |
| 2. PKB | PKB templates with no `project` (absent or `null`) | Same batched summary read; keep `frontmatter.project` absent or `null` |
| 3. Universal | `workflows/*.md` inside this skill directory | Enumerate `workflows/*.md` via native file tools |

- **PKB retrieval**: Both PKB tiers resolve from the graph alone without requiring a repository checkout. List all `type: "template"` IDs via `pkb_list_documents` (`limit >= 200`), then batch-read `pkb_get_document(..., detail: "summary")` to inspect `frontmatter.project`, `frontmatter.description`, and opening step summaries in one pass (reading `detail: "full"` only in `view` or `edit` mode).
- **Tier classification & shadowing**: Classify Tier 1 vs. Tier 2 strictly by `frontmatter.project`. Determine a project template's shadowed slug by stripping an optional `<project>-` or `<project>_` prefix from `id` when present; otherwise use `id` directly.
- **Scope**: Foreign-project templates stay out of scope for composition and appear in `list` mode.

## Modes

- **list**: Enumerate all templates live across all three tiers and emit **slug | tier | coverage | status**. Show project scope as `Project (<name>)`; extract coverage from `frontmatter.description` or the first sentence of `## What this step does`; exclude dated instances (`-*-\d{8}-*`) and `status: cancelled`; flag shadowed slugs and missing coverage lines.
- **view**: Resolve a template slug in precedence order and output the winning content, shadowed tiers, or near-misses.
- **new**: Check existing coverage first, select destination tier (Project PKB with `project: <project>`, PKB with `project: null`, or Universal under `workflows/`), and author per `ida:craft` workflow-template standards.
- **edit**: Update templates in place per `ida:craft` workflow-template standards. Edit Universal files directly; for PKB nodes, update only the markdown body below the closing `---` to avoid frontmatter duplication.
- **retire**: Verify no unfulfilled governing tasks remain on the PKB, delete the file or PKB node, and name the superseding workflow in the commit or release message.

## Constraints

- Query tiers dynamically using metadata/summary detail for lists and full bodies only for `view`/`edit`; read universal templates with native file tools rather than shell loops.
- Keep templates focused on stage contracts, obligations, and exit criteria without naming neighbour templates; leave operational method to skills.
- Never mint tasks or dispatch work during library maintenance.
