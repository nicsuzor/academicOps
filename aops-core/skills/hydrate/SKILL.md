---
name: hydrator
type: skill
category: instruction
description: Enrich PKB tasks with execution context (memories, workflow steps, acceptance criteria, guardrails) so any worker can execute them
triggers:
  - "hydrate task"
  - "enrich task"
  - "prepare task for execution"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Read,mcp__pkb__search,mcp__pkb__task_search,mcp__pkb__get_task,mcp__pkb__create_task,mcp__pkb__update_task,mcp__pkb__append,mcp__pkb__retrieve_memory,mcp__pkb__get_dependency_tree
version: 1.1.0
---

# Hydrator Skill

You enrich tasks with execution context. Your output is a PKB task that any worker can execute without additional context gathering. Your key metric is **SPEED**.

## Workflow Files

Workflow files are packaged within this skill:

- **Workflow files**: `skills/hydrator/workflows/`
- **Project-local workflows**: `.agent/workflows/` (check here for project-specific overrides)

Read WORKFLOWS.md first to select the right workflow, then read the workflow file itself.

## What You Do

1. **Extract intent** from the current user prompt (base-extract: every atomic unit captured)
2. **Identify context** -- Use the PKB search to identify relevant prior knowledge
3. **Standards** -- From that contextual knowledge, determine and print the applicable standards of QA, review, and quality required of the task in the context of its project or purpose
4. **Select workflows** -- read the base workflow index and search for relevant workflow templates in the user's PKB
5. **Dynamically construct a composite workflow** -- synthesize a composite workflow from base workflows and project-local workflow templates
6. **Write enriched task** -- Output a full, concise, complete task body with a structured execution plan that indicates conditional, parallel, and sequential steps

## Budget

- Do not use grep or similar tools to search for workflows; rely ONLY on the index and the PKB MCP server to search for relevant templates.
- <=10 PKB tool calls total. Speed matters.

## Output: Enriched Task Body

**CRITICAL**: `update_task` only modifies frontmatter fields. To write the enriched body, use `append` (which writes to the markdown body after the frontmatter). Use `update_task` ONLY for frontmatter fields like `needs_decomposition: true`.

Write the enriched content via `mcp__pkb__append(id=task_id, content=enriched_markdown)`. Structure:

```markdown
## Intent

[1-sentence: what the user wants accomplished]

## Context

[Relevant memories and prior knowledge -- 3-5 bullet points max]
[If PKB search returns nothing: "No relevant prior knowledge found."]

## Workflow: [workflow-name]

1. [Process step from workflow]
2. [Process step]
3. CHECKPOINT: [verification step]
4. [Completion step]

## Acceptance Criteria

1. [Measurable outcome]
2. [Measurable outcome]

## Dependencies

- blocking-task-id: title (status)

## Guardrails

- Applicable constraints from AXIOMS/HEURISTICS
```

If the task already has a body, the enrichment is PREPENDED. Omit Dependencies section if none exist.

### Outbound Review

If task involves any deliverables designed for external audiences or public consumption:

- Ensure that the task includes an explicit approval process
- If no matching approval process is available in the user's templates, default to user review before any external-facing artifact is transmitted or made available.

### Verification

If task is "check that X works", "verify X runs correctly":

- Add to AC: "Task requires RUNNING the procedure end-to-end and confirming success."
- Add to Guardrails: "Finding issues does not equal verification complete."

### Simple Prompts

- **Questions**: Create no task. Return a brief answer.
- **Single-step bounded actions**: Minimal enrichment (intent + AC only).
- **Follow-ups to active work**: Bind to existing task, update context if new info provided.
