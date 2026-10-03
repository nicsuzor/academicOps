---
name: workflow-library
description: List, read, add, edit, and retire workflow templates across project, PKB, and universal tiers, or preview composition without minting tasks. Exclude when tracking running jobs (use harness progress tools).
---

# Workflow Library

Manage composable workflow templates (`type: template`) across three resolution tiers. Every `pkb.<op>(...)` call below runs through the `services` MCP server's code-mode interface (`listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode`), not a directly-invocable flat tool.

## Tiers and Resolution

Resolution order is **Project > PKB > Universal**. Higher tiers shadow lower tiers completely; never merge text across tiers.

| Tier         | Location                         | Enumeration                                  |
| ------------ | -------------------------------- | -------------------------------------------- |
| 1. Project   | `$CWD/.agents/templates/*.md`    | `Glob $CWD/.agents/templates/*.md` (or `ls`) |
| 2. PKB       | PKB graph                        | `pkb.list_documents(type="template")`        |
| 3. Universal | `${CLAUDE_SKILL_DIR}/workflows/` | `Glob ${CLAUDE_SKILL_DIR}/workflows/*.md`    |

Enumerate and read filesystem templates using file tools (`Glob`, `Read`) rather than `Bash` so resolution succeeds under non-interactive and `dontAsk` permission modes.

## Modes

### list

Enumerate all three tiers live. Return a unified table: **slug \| tier \| coverage \| status**.

- Extract coverage from `description` in frontmatter (filesystem) or the initial sentence of `## What this step does` (PKB). Read template files directly via `Read`; do not run `Bash` loops.
- Filter out dated instances (`-*-\d{8}-*`), foreign-project templates, and `status: cancelled`.
- Flag shadowed slugs and templates missing coverage lines.

### view

Resolve the template slug across tiers in precedence order. Output the winning content, identify winning and shadowed tiers, or list near-misses if missing.

### new

1. Check existing library to avoid duplicating covered workflows.
2. Select destination tier:
   - **Project**: Local repository specific.
   - **PKB**: Portable personal workflow.
   - **Universal**: Core baseline standard across projects.
3. Write template using the template schema (<100 lines), to these rules:
   - **State the contract, not the neighbour.** Say what the step needs as input and what it hands back. Never name another template, in the body or the frontmatter: the composing agent decides at composition time what fills each slot. A composite lists its stages as contract expectations in order ("an independent review verdict on the spec"), not as slugs.
   - **Write for a headless worker.** The executor runs unattended and asynchronously, with no one to talk to mid-task. A step never pauses, waits, or blocks for a human. Where human judgement is needed, the step ends there: the worker files the artifact for review (in the form the project or user preferences name) and releases the task as `review`. Work that follows the decision belongs in a separate task that `depends_on` this one; say so, so the composer cuts the chain at that point.
   - **Promise only what the executor delivers.** The output contract lists artifacts and state the executing agent itself produces. Another party's act -- a human's approval, a reviewer's verdict -- is never an output-contract term.

### edit

Update existing templates in place.

- **Filesystem**: Edit file directly.
- **PKB**: Pass only the markdown body below the closing `---` to `pkb.update_body` to prevent frontmatter duplication.

### preview

Simulate how `dispatch` would assemble workflow templates for a stated objective:

1. Enumerate and read relevant candidate templates across tiers.
2. Read the templates and combine their steps into a single, logical sequence (e.g., TDD red tests first, then implementation, then QA integration tests at the end).
3. Do not ad lib extra requirements or guess at scope. Pass through any ambiguity in the prompt directly to the workflow.
4. Show the assembled sequence of steps and resulting task brief shape.
5. Plainly mark output as a non-minted preview. Never write tasks or mutate the graph.

### retire

1. Check for tasks governing retirement (`pkb.search`). Halt if unfulfilled dependencies exist.
2. Delete the artifact (`rm` for files, `pkb.delete` for PKB nodes).
3. Name the superseding workflow in the release message or commit.

A template carries only what a composing agent needs to select it and to know
the step is finished -- the same sufficient-and-no-more standard `/dispatch`
composes to ([[aops_brief_workflow_assembly]]). Nothing else is mandatory:
inventing exclusions, contraindications, or gates the work doesn't call for
overshoots it. No fixed kind is required either -- components sit on one flat
spine, not sorted into types ([[aops-composable-workflow-system]] §6); a
template stating an obligation that blocks acceptance rather than a process
that proceeds conventionally carries a `wf-` prefix, no frontmatter field
needed to say so.

## Template Schema

```yaml
---
title: <human name>
type: template
description: <one line: what class of work this covers, so a composer can select it>
tags: [...]
---
```

## Constraints

- Query tiers dynamically; do not rely on static indices or memory.
- Keep templates focused on obligations and exit criteria; leave operational method to skills.
- Do not mint tasks or dispatch work during library management operations.
