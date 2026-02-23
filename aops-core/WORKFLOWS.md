---
name: workflows
title: Workflow Index
type: index
category: framework
description: Index of all available workflows for routing and execution
permalink: workflows
tags: [framework, routing, workflows, index]
---

# Workflow Index

> **Curated by audit skill** - Regenerate with Skill(skill="audit")
> Last reconciled: 2026-02-23

Workflows are **hydrator hints**, not complete instructions. They tell the hydrator:

1. When this workflow applies (routing signals)
2. What's unique to this workflow
3. Which base workflows to compose

## Base Workflows (Composable Patterns)

**Always consider these.** Most workflows compose one or more base patterns.

| Base                    | Pattern                                      | Skip When                          |
| ----------------------- | -------------------------------------------- | ---------------------------------- |
| [[base-task-tracking]]  | Claim/create task, update progress, complete | [[simple-question]]                |
| [[base-tdd]]            | Red-green-refactor cycle                     | Non-code changes                   |
| [[base-verification]]   | Checkpoint before completion                 | Trivial changes                    |
| [[base-commit]]         | Stage, commit (why not what), push           | No file modifications              |
| [[base-handover]]       | Session end: task, git push, reflection      | [[simple-question]]                |
| [[base-memory-capture]] | Store findings to memory MCP via /remember   | No discoveries, [[simple-question]]|
| [[base-qa]]             | QA checkpoint: lock criteria, gather, judge  | Trivial changes, user waives       |
| [[base-batch]]          | Batch processing: chunk, parallelize, aggregate | Single item, items have dependencies |
| [[base-investigation]]  | Investigation: hypothesis → probe → conclude | Cause known, just executing        |

## Decision Tree

**Multiple intents?** If your prompt contains two or more distinct goals (e.g., "process emails AND fix that bug"), split and route each independently. One workflow per intent.

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────> Invoke skill directly
    │
    ├─ Simple question only? ──────────────────> [[simple-question]]
    │
    ├─ Continuation of session work? ──────────> [[interactive-followup]]
    │
    ├─ Goal-level / multi-month work? ─────────> [[decompose]]
    │   (uncertain path, need to figure out steps)
    │
    ├─ Multiple similar items? ────────────────> [[base-batch]]
    │
    ├─ Email/communications? ──────────────────> [[email-triage]]
    │       ├─ Extracting tasks from email? ───> [[email-capture]]
    │       └─ Drafting replies? ──────────────> [[email-reply]]
    │
    ├─ Academic/research task?
    │       ├─ Review submission? ─────────────> [[peer-review]]
    │       └─ Reference letter? ──────────────> [[reference-letter]]
    │
    ├─ Building a feature? ────────────────────> [[feature-dev]]
    │
    ├─ Need QA verification? ──────────────────> [[qa]]
    │
    ├─ Framework governance change? ───────────> Compose: base-task-tracking + base-verification + base-commit
    │
    └─ No branch matched? ─────────────────────> Ask user to clarify
```

## Scope-Based Routing

| Signal                                         | Route to             |
| ---------------------------------------------- | -------------------- |
| "Write a paper", "Build X", "Plan the project" | [[decompose]]        |
| "Add feature X" (clear steps)                  | [[feature-dev]]      |
| "How do I..." (information only)               | [[simple-question]]  |
| "Process all X", "batch update"                | [[base-batch]]       |
| "Process emails", "check inbox"                | [[email-triage]]     |
| "Review grant", "reference letter"             | [[peer-review]] / [[reference-letter]] |
| "/commit", "/email" (skill name)               | Invoke skill directly |

## Available Workflows

### Planning & Discovery

| Workflow      | When to Use                                 | Bases         |
| ------------- | ------------------------------------------- | ------------- |
| [[decompose]] | Multi-month, uncertain path, goals to epics | task-tracking |

> **Note:** `strategy` and `planning` are now skills, not workflows. Use `/strategy` and `/planning`.

### Development

| Workflow       | When to Use                          | Bases                                    |
| -------------- | ------------------------------------ | ---------------------------------------- |
| [[feature-dev]]| Test-first feature from idea to ship | task-tracking, tdd, verification, commit |

### Quality Assurance

| Workflow | When to Use                    | Bases |
| -------- | ------------------------------ | ----- |
| [[qa]]   | QA verification and checkpoint | qa    |

### Operations & Batch

| Workflow                    | When to Use                        | Bases        |
| --------------------------- | ---------------------------------- | ------------ |
| [[interactive-followup]]    | Simple session continuations       | verification |
| [[external-batch-submission]] | External batch submission processing | -          |

### Email & Communications

| Workflow          | When to Use               | Bases         |
| ----------------- | ------------------------- | ------------- |
| [[email-triage]]  | Email classification      | task-tracking |
| [[email-capture]] | Extract tasks from emails | task-tracking |
| [[email-reply]]   | Drafting replies          | task-tracking |

### Academic

| Workflow             | When to Use              | Bases         |
| -------------------- | ------------------------ | ------------- |
| [[peer-review]]      | Grant/fellowship reviews | task-tracking |
| [[reference-letter]] | Reference letter workflow | task-tracking |

> **Note:** HDR supervision is handled by the `/hdr` skill.

### Routing & Information

| Workflow            | When to Use                        | Bases |
| ------------------- | ---------------------------------- | ----- |
| [[simple-question]] | Pure information, no modifications | -     |

### Session & Handover

| Workflow          | When to Use                              | Bases  |
| ----------------- | ---------------------------------------- | ------ |
| [[base-handover]] | Session completion and state persistence | commit |
| [[reflect]]       | Session reflection and learning capture  | -      |

### Meta & Framework

| Workflow       | When to Use                | Bases |
| -------------- | -------------------------- | ----- |
| [[dogfooding]] | Framework self-improvement | -     |
| [[audit]]      | Framework governance audit | -     |

### Git Operations

| Workflow           | When to Use             | Bases  |
| ------------------ | ----------------------- | ------ |
| [[worktree-merge]] | Merge worktree branches | commit |

### Hydration (Internal)

| Workflow             | When to Use                                  | Bases |
| -------------------- | -------------------------------------------- | ----- |
| [[framework-gate]]   | First check - detect framework modifications | -     |
| [[constraint-check]] | Verify plan satisfies workflow constraints    | -     |

## Skill-Scoped Workflows

Some skills define internal workflows for their own procedures. These are not routed by the hydrator — they're invoked within skill execution.

| Skill     | Workflows                                                                                           |
| --------- | --------------------------------------------------------------------------------------------------- |
| framework | design-new-component, debug-framework-issue, experiment-design, monitor-prevent-bloat, feature-development, develop-specification, learning-log, decision-briefing, session-hook-forensics |
| hdr       | reference-letter                                                                                    |
| remember  | capture, prune, validate, sync                                                                      |
| audit     | session-effectiveness                                                                               |

## Project-Specific Workflows

Projects can extend the global workflow catalog by defining local workflows in the project root:

1. **Local Index**: `.agent/WORKFLOWS.md`
   - If present, its content can be included in the hydration context during the `UserPromptSubmit` hook.
   - Use this for project-wide workflow routing and definitions.

2. **Workflow Directory**: `.agent/workflows/*.md`
   - Individual workflow files.
   - **Content Injection**: During the `UserPromptSubmit` hook, the orchestration layer may include the content of these files in the hydrator context if the prompt matches the filename (e.g., "manual-qa" matches `manual-qa.md`).
   - Use these for specific, repetitive procedures unique to the project.

## Key Distinctions

| If you're unsure between...              | Ask...                                              |
| ---------------------------------------- | --------------------------------------------------- |
| [[decompose]] vs [[feature-dev]]         | "Figure out what to do" vs "build a known thing"    |
| [[simple-question]] vs [[feature-dev]]   | Pure info (no file mods) vs any file-modifying work |
| [[simple-question]] vs [[base-investigation]] | Pure info vs leads to investigation            |
