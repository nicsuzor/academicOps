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

Workflows are **hydrator hints**, not complete instructions. They tell the hydrator:

1. When this workflow applies (routing signals)
2. What's unique to this workflow
3. Which base workflows to compose

## Base Workflows (Composable Patterns)

**Always consider these.** Most workflows compose one or more base patterns.

| Base                    | Pattern                                         | Skip When                            |
| ----------------------- | ----------------------------------------------- | ------------------------------------ |
| [[base-task-tracking]]  | Claim/create task, update progress, complete    | [[simple-question]], direct skill    |
| [[base-tdd]]            | Red-green-refactor cycle                        | Non-code changes                     |
| [[base-verification]]   | Checkpoint before completion                    | Trivial changes                      |
| [[base-commit]]         | Stage, commit (why not what), push              | No file modifications                |
| [[base-handover]]       | Session end: task, git push, reflection         | [[simple-question]]                  |
| [[base-memory-capture]] | Store findings to memory MCP via /remember      | No discoveries, [[simple-question]]  |
| [[base-qa]]             | QA checkpoint: lock criteria, gather, judge     | Trivial changes, user waives         |
| [[base-batch]]          | Batch processing: chunk, parallelize, aggregate | Single item, items have dependencies |
| [[base-investigation]]  | Investigation: hypothesis -> probe -> conclude  | Cause known, just executing          |

## Decision Tree

**Multiple intents?** If your prompt contains two or more distinct goals (e.g., "process emails AND fix that bug"), split and route each independently. One workflow per intent.

```
User request
    |
    +-- Explicit skill mentioned? ------------------> Use [[simple-question]] + invoke skill directly
    |
    +-- Simple question only? ----------------------> [[simple-question]]
    |
    +-- Continuation of session work? --------------> [[interactive-followup]]
    |
    +-- Goal-level / multi-month work? -------------> [[decompose]]
    |   (uncertain path, need to figure out steps)
    |
    +-- Multiple similar items? --------------------> [[base-batch]]
    |
    +-- Email/communications? ----------------------> [[email-triage]]
    |       +-- Extracting tasks from email? -------> [[email-capture]]
    |       +-- Drafting replies? ------------------> [[email-reply]]
    |
    +-- Academic/research task? --------------------> (see below)
    |       +-- Review submission? -----------------> [[peer-review]]
    |       +-- Reference letter? ------------------> [[reference-letter]]
    |
    +-- Bug or issue?
    |       +-- Cause unknown (investigating)? -----> [[base-investigation]] + task-tracking
    |       +-- Cause known (clear fix)? -----------> [[feature-dev]]
    |
    +-- Planning/designing known work? -------------> [[feature-dev]]
    |   (know what to build, designing how)
    |
    +-- Need QA verification? ----------------------> [[qa]]
    |
    +-- Framework governance change? ---------------> [[framework-gate]]
    |
    +-- No branch matched? -------------------------> Ask user to clarify
```

## Scope-Based Routing

| Signal                                         | Route to                                    |
| ---------------------------------------------- | ------------------------------------------- |
| "Write a paper", "Build X", "Plan the project" | [[decompose]]                               |
| "Add feature X", "Fix bug Y" (clear steps)     | [[feature-dev]]                             |
| "Bug broken", "not working" (cause unknown)    | [[base-investigation]] + task-tracking      |
| "How do I..." (information only)               | [[simple-question]]                         |
| "Process all X", "batch update"                | [[base-batch]]                              |
| "Process emails", "check inbox"                | [[email-triage]]                            |
| "Review grant", "reference letter"             | [[peer-review]] / [[reference-letter]]      |
| "/pdf", "/daily" (skill name)                  | [[simple-question]] + invoke skill directly |

## Available Workflows

### Planning & Discovery

These workflows help figure out what to do and how to do it.

| Workflow      | When to Use                                 | Bases                   |
| ------------- | ------------------------------------------- | ----------------------- |
| [[decompose]] | Multi-month, uncertain path, goals to epics | task-tracking, handover |

### Development

Core workflows for building and fixing software.

| Workflow        | When to Use                          | Bases                                      |
| --------------- | ------------------------------------ | ------------------------------------------ |
| [[feature-dev]] | Test-first feature from idea to ship | task-tracking, tdd, verification, handover |

### Quality Assurance

| Workflow | When to Use                                                          | Bases                       |
| -------- | -------------------------------------------------------------------- | --------------------------- |
| [[qa]]   | Pre-completion verification, acceptance testing, integration testing | task-tracking, qa, handover |

### Operations & Batch

Workflows for handling multiple items or operational tasks.

| Workflow                      | When to Use                              | Bases                       |
| ----------------------------- | ---------------------------------------- | --------------------------- |
| [[base-batch]]                | Multiple independent items               | (base pattern)              |
| [[external-batch-submission]] | Submit prediction/inference jobs to APIs | task-tracking, verification |
| [[interactive-followup]]      | Simple session continuations             | verification                |

### Email & Communications

Workflows for email processing and correspondence.

| Workflow          | When to Use               | Bases                   |
| ----------------- | ------------------------- | ----------------------- |
| [[email-triage]]  | Email classification      | task-tracking, handover |
| [[email-capture]] | Extract tasks from emails | task-tracking, handover |
| [[email-reply]]   | Drafting replies          | task-tracking, handover |

### Academic

Workflows for academic and research activities.

| Workflow             | When to Use               | Bases                   |
| -------------------- | ------------------------- | ----------------------- |
| [[peer-review]]      | Grant/fellowship reviews  | task-tracking, handover |
| [[reference-letter]] | Reference letter workflow | task-tracking, handover |

### Routing & Information

Simple routing workflows with minimal ceremony.

| Workflow            | When to Use                        | Bases |
| ------------------- | ---------------------------------- | ----- |
| [[simple-question]] | Pure information, no modifications | -     |

### Session & Handover

Workflows for session management and state persistence.

| Workflow          | When to Use                              | Bases  |
| ----------------- | ---------------------------------------- | ------ |
| [[base-handover]] | Session completion and state persistence | commit |

### Meta & Framework

Workflows about the framework itself.

| Workflow           | When to Use                              | Bases    |
| ------------------ | ---------------------------------------- | -------- |
| [[framework-gate]] | Detect and route framework modifications | -        |
| [[dogfooding]]     | Framework self-improvement               | -        |
| [[audit]]          | Framework governance audit               | handover |

### Git Operations

Workflows for version control operations.

| Workflow           | When to Use             | Bases    |
| ------------------ | ----------------------- | -------- |
| [[worktree-merge]] | Merge worktree branches | handover |

### Hydration (Internal)

Internal workflows supporting prompt hydration.

| Workflow             | When to Use                                | Bases |
| -------------------- | ------------------------------------------ | ----- |
| [[framework-gate]]   | First check - detect framework intent      | -     |
| [[constraint-check]] | Verify plan satisfies workflow constraints | -     |

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

| If you're unsure between...            | Ask...                                              |
| -------------------------------------- | --------------------------------------------------- |
| [[decompose]] vs [[feature-dev]]       | "Figure out what to do" vs "design how to do it"    |
| [[simple-question]] vs [[feature-dev]] | Pure info (no file mods) vs any file-modifying work |
| [[qa]] modes                           | Quick verification vs acceptance vs integration     |
