---
name: workflows
title: Workflow Index
type: index
category: framework
description: Index of all available workflows
permalink: workflows
tags: [framework, routing, workflows, index]
---

# Workflow Index

> **Curated by audit skill** — Regenerate with `Skill(skill="audit")`
> Last reconciled: 2026-02-23

Workflows define procedural requirements for how work gets done. They constrain how skills are exercised — they don't contain the work itself. See hydrator instructions for the full architecture.

## Base Workflows (Composable Patterns)

| Base                    | Procedural requirement                           | Skip when              |
| ----------------------- | ------------------------------------------------ | ---------------------- |
| [[base-task-tracking]]  | Claim task, assess scope, track progress, complete | [[simple-question]]   |
| [[base-tdd]]            | Red-green-refactor cycle                         | Non-code changes       |
| [[base-verification]]   | Checkpoint before completion                     | Trivial changes        |
| [[base-commit]]         | Stage, commit (why not what), push               | No file modifications  |
| [[base-handover]]       | Session end: task, git push, reflection          | [[simple-question]]    |
| [[base-memory-capture]] | Store findings to memory via /remember           | No discoveries         |
| [[base-qa]]             | Lock criteria, gather evidence, judge            | Trivial, user waives   |
| [[base-batch]]          | Chunk, parallelize, aggregate                    | Single item            |
| [[base-investigation]]  | Hypothesis → probe → conclude                    | Cause known            |
| [[base-dogfood]]        | Observe friction, capture learnings, codify      | Routine, not exercising framework |

## Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ──────────> Invoke skill directly
    │
    ├─ Simple question only? ──────────────> [[simple-question]]
    │
    ├─ Continuation of session work? ──────> [[interactive-followup]]
    │
    ├─ Building a feature (code)? ─────────> [[feature-dev]]
    │
    ├─ Costly external API submission? ────> [[external-batch-submission]]
    │
    ├─ Framework modification? ────────────> [[framework-gate]]
    │
    ├─ Merge polecat worktrees? ───────────> [[worktree-merge]]
    │
    ├─ Research project (end-to-end)? ─────> [[research-project-lifecycle]] (draft)
    │
    ├─ Deep work requiring thoroughness? ──> [[iterative-skill-exercise]] (draft)
    │
    └─ Everything else ────────────────────> Compose base workflows + relevant skill
```

## Leaf Workflows

### Development

| Workflow        | Procedural requirement                              |
| --------------- | --------------------------------------------------- |
| [[feature-dev]] | Phase sequencing, TDD mandate, commit gates for code |

### Quality & Safety

| Workflow                        | Procedural requirement                         |
| ------------------------------- | ---------------------------------------------- |
| [[external-batch-submission]]   | Safety gates for irreversible costly operations |
| [[iterative-skill-exercise]]    | Anti-shortcut: thorough per-item processing (draft) |

### Session & Routing

| Workflow                 | Procedural requirement                    |
| ------------------------ | ----------------------------------------- |
| [[simple-question]]      | Answer and halt — no modifications        |
| [[interactive-followup]] | Session continuation detection, escalation |

### Integration

| Workflow           | Procedural requirement                     |
| ------------------ | ------------------------------------------ |
| [[worktree-merge]] | Merge safety ordering, verify before cleanup |

### Academic

| Workflow                         | Procedural requirement                          |
| -------------------------------- | ----------------------------------------------- |
| [[research-project-lifecycle]]   | End-to-end research integrity gates (draft)     |

### Hydration (Internal)

| Workflow             | Procedural requirement                                |
| -------------------- | ----------------------------------------------------- |
| [[framework-gate]]   | Detect framework modification intent, route accordingly |
| [[constraint-check]] | Verify plan satisfies workflow constraints             |

## Skill-Scoped Workflows

Some skills define internal workflows for their own procedures. Not routed by the hydrator — invoked within skill execution.

| Skill     | Workflows                                                                                           |
| --------- | --------------------------------------------------------------------------------------------------- |
| framework | design-new-component, debug-framework-issue, experiment-design, monitor-prevent-bloat, feature-development, develop-specification, learning-log, decision-briefing, session-hook-forensics |
| hdr       | reference-letter                                                                                    |
| remember  | capture, prune, validate, sync                                                                      |
| audit     | session-effectiveness                                                                               |

## Project-Specific Workflows

Projects can extend the workflow catalog:

1. **Local Index**: `.agent/WORKFLOWS.md` — included in hydration context
2. **Workflow Directory**: `.agent/workflows/*.md` — injected when prompt matches filename
