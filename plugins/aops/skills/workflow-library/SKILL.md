---
name: workflow-library
description: List, read, add, edit, and retire workflow templates across project, PKB, and universal tiers, or preview composition without minting tasks. Exclude when tracking running jobs (use harness progress tools).
---

# Workflow Library

Manage composable workflow templates (`type: template`) across three resolution tiers.

## Tiers and Resolution

Resolution order is **Project > PKB > Universal**. Higher tiers shadow lower tiers completely; never merge text across tiers.

| Tier         | Location                      | Enumeration Command                    |
| ------------ | ----------------------------- | -------------------------------------- |
| 1. Project   | `$CWD/.agents/templates/*.md` | `ls $CWD/.agents/templates/*.md`       |
| 2. PKB       | PKB graph                     | `pkb__list_documents(type="template")` |
| 3. Universal | `../../workflows/*.md`        | `ls ../../workflows/*.md`              |

## Modes

### list

Enumerate all three tiers live. Return a unified table: **slug \| tier \| coverage \| status**.

- Extract coverage from `description` in frontmatter (filesystem) or the initial sentence of `## What this step does` (PKB).
- Filter out dated instances (`-*-\d{8}-*`), foreign-project templates, and `status: cancelled`.
- Flag shadowed slugs and templates missing coverage lines.

### view

Resolve the template slug across tiers in precedence order. Output the winning content, identify winning and shadowed tiers, or list near-misses if missing.

### preview

Simulate how `brief` would assemble workflow templates for a stated objective:

1. Enumerate and read relevant candidate templates across tiers.
2. Show the assembled structure (slots, gates, and fragments) and resulting task brief shape.
3. Plainly mark output as a non-minted preview. Never write tasks or mutate the graph.

### new

1. Check existing library to avoid duplicating covered workflows.
2. Select destination tier:
   - **Project**: Local repository specific.
   - **PKB**: Portable personal workflow.
   - **Universal**: Core baseline standard across projects.
3. Write template using the template schema (<100 lines).

### edit

Update existing templates in place.

- **Filesystem**: Edit file directly.
- **PKB**: Pass only the markdown body below the closing `---` to `pkb__update_body` to prevent frontmatter duplication.

### retire

1. Check for tasks governing retirement (`pkb__task_search`). Halt if unfulfilled dependencies exist.
2. Delete the artifact (`rm` for files, `pkb__delete` for PKB nodes).
3. Name the superseding workflow in the release message or commit.

## Template Schema

```yaml
---
title: <human name>
type: template
category: process | gate
description: <selection criteria and explicit exclusions>
tags: [...]
---
```

## Constraints

- Query tiers dynamically; do not rely on static indices or memory.
- Keep templates focused on obligations and exit criteria; leave operational method to skills.
- Do not mint tasks or dispatch work during library management operations.
