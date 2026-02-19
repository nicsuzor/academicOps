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

| Base                    | Pattern                                      | Skip When                             |
| ----------------------- | -------------------------------------------- | ------------------------------------- |
| [[base-task-tracking]]  | Claim/create task, update progress, complete | [[simple-question]], [[direct-skill]] |
| [[base-tdd]]            | Red-green-refactor cycle                     | Non-code changes                      |
| [[base-verification]]   | Checkpoint before completion                 | Trivial changes                       |
| [[base-commit]]         | Stage, commit (why not what), push           | No file modifications                 |
| [[base-handover]]       | Session end: task, git push, reflection      | [[simple-question]]                   |
| [[base-memory-capture]] | Store findings to memory MCP via /remember   | No discoveries, [[simple-question]]   |
| [[base-qa]]             | QA checkpoint: lock criteria, gather, judge  | Trivial changes, user waives          |
| [[base-batch]]          | Batch processing: chunk, parallelize, aggregate | Single item, items have dependencies |
| [[base-investigation]]  | Investigation: hypothesis → probe → conclude | Cause known, just executing           |

## Decision Tree

**Multiple intents?** If your prompt contains two or more distinct goals (e.g., "process emails AND fix that bug"), split and route each independently. One workflow per intent.

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────> [[direct-skill]]
    │
    ├─ Simple question only? ──────────────────> [[simple-question]]
    │
    ├─ Continuation of session work? ──────────> [[interactive-followup]]
    │
    ├─ Goal-level / multi-month work? ─────────> [[decompose]]
    │   (uncertain path, need to figure out steps)
    │       └─ Task doesn't map to any skill? ─> [[skill-pilot]]
    │
    ├─ Multiple similar items? ────────────────> [[batch-processing]]
    │
    ├─ Email/communications? ──────────────────> [[triage-email]]
    │       ├─ Classifying emails? ────────────> [[email-classify]]
    │       ├─ Extracting tasks from email? ───> [[email-capture]]
    │       └─ Drafting replies? ──────────────> [[email-reply]]
    │
    ├─ Academic/research task? ────────────────> (see below)
    │       ├─ Review submission? ─────────────> [[peer-review]]
    │       ├─ Reference letter? ──────────────> [[reference-letter]]
    │       └─ HDR supervision? ───────────────> [[hdr-supervision]]
    │
    ├─ Bug or issue?
    │       ├─ Cause unknown (investigating)? ─> [[debugging]]
    │       └─ Cause known (clear fix)? ───────> [[design]]
    │
    ├─ Planning/designing known work? ─────────> [[design]]
    │   (know what to build, designing how)
    │
    ├─ Need QA verification? ──────────────────> [[qa-demo]]
    │
    ├─ Framework governance change? ───────────> [[framework-change]]
    │
    └─ No branch matched? ─────────────────────> Ask user to clarify
```

## Scope-Based Routing

| Signal                                         | Route to             |
| ---------------------------------------------- | -------------------- |
| "Write a paper", "Build X", "Plan the project" | [[decompose]]        |
| "Add feature X", "Fix bug Y" (clear steps)     | [[design]]           |
| "Bug broken", "not working" (cause unknown)    | [[debugging]]        |
| "How do I..." (information only)               | [[simple-question]]  |
| "Process all X", "batch update"                | [[batch-processing]] |
| "Process emails", "check inbox"                | [[triage-email]]     |
| "Review grant", "reference letter"             | [[peer-review]] / [[reference-letter]] |
| "/commit", "/email" (skill name)               | [[direct-skill]]     |

## Available Workflows

### Planning & Discovery

These workflows help figure out what to do and how to do it.

| Workflow        | When to Use                                 | Bases         |
| --------------- | ------------------------------------------- | ------------- |
| [[decompose]]   | Multi-month, uncertain path, goals to epics | task-tracking |
| [[design]]      | Known work, need architecture               | task-tracking |
| [[collaborate]] | Open-ended exploration, brainstorming       | task-tracking |
| [[strategy]]    | Strategic thinking partner (no execution)   | -             |

### Development

Core workflows for building and fixing software.

| Workflow               | When to Use                          | Bases                                    |
| ---------------------- | ------------------------------------ | ---------------------------------------- |
| [[tdd-cycle]]          | Any testable code change             | task-tracking, tdd, verification, commit |
| [[feature-dev]]        | Test-first feature from idea to ship | task-tracking, tdd, verification, commit |
| [[debugging]]          | Cause unknown, investigating         | task-tracking, verification              |

### Quality Assurance

Verification workflows for different scopes.

| Workflow            | When to Use                     | Bases         |
| ------------------- | ------------------------------- | ------------- |
| [[qa-demo]]         | Pre-completion verification     | -             |
| [[qa-test]]         | User acceptance testing         | -             |
| [[prove-feature]]   | Integration validation          | -             |
| [[qa-design]]       | Design QA test plans            | task-tracking |

### Operations & Batch

Workflows for handling multiple items or operational tasks.

| Workflow                  | When to Use                                  | Bases         |
| ------------------------- | -------------------------------------------- | ------------- |
| [[batch-processing]]      | Multiple independent items                   | task-tracking |
| [[batch-task-processing]] | Batch task management operations             | task-tracking |
| [[task-triage]]           | Backlog grooming and cleanup                 | task-tracking |
| [[classify-task]]         | Complexity + graph positioning for new tasks | -             |
| [[interactive-followup]]  | Simple session continuations                 | verification  |

### Email & Communications

Workflows for email processing and correspondence.

| Workflow           | When to Use               | Bases         |
| ------------------ | ------------------------- | ------------- |
| [[triage-email]]   | Email classification      | task-tracking |
| [[email-capture]]  | Extract tasks from emails | task-tracking |
| [[email-classify]] | Classify email content    | -             |
| [[email-reply]]    | Drafting replies          | task-tracking |

### Academic

Workflows for academic and research activities.

| Workflow             | When to Use               | Bases         |
| -------------------- | ------------------------- | ------------- |
| [[peer-review]]      | Grant/fellowship reviews  | task-tracking |
| [[reference-letter]] | Reference letter workflow | task-tracking |
| [[hdr-supervision]]  | HDR student supervision   | task-tracking |

### Routing & Information

Simple routing workflows with minimal ceremony.

| Workflow            | When to Use                        | Bases |
| ------------------- | ---------------------------------- | ----- |
| [[simple-question]] | Pure information, no modifications | -     |
| [[direct-skill]]    | 1:1 skill mapping                  | -     |

### Session & Handover

Workflows for session management and state persistence.

| Workflow          | When to Use                              | Bases  |
| ----------------- | ---------------------------------------- | ------ |
| [[base-handover]] | Session completion and state persistence | commit |

### Meta & Framework

Workflows about the framework itself.

| Workflow             | When to Use                   | Bases                               |
| -------------------- | ----------------------------- | ----------------------------------- |
| [[framework-change]] | AXIOMS/HEURISTICS/enforcement | task-tracking, verification, commit |
| [[dogfooding]]       | Framework self-improvement    | -                                   |
| [[skill-pilot]]      | Building new skills from gaps | task-tracking                       |
| [[audit]]            | Framework governance audit    | -                                   |

### Git Operations

Workflows for version control operations.

| Workflow           | When to Use                | Bases  |
| ------------------ | -------------------------- | ------ |
| [[merge-conflict]] | Resolve merge conflicts    | commit |
| [[worktree-merge]] | Merge worktree branches    | commit |
| [[version-bump]]   | Version bumping automation | -      |

### Hydration (Internal)

Internal workflows supporting prompt hydration.

| Workflow             | When to Use                                  | Bases |
| -------------------- | -------------------------------------------- | ----- |
| [[framework-gate]]   | First check - detect framework modifications | -     |
| [[constraint-check]] | Verify plan satisfies workflow constraints   | -     |

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

| If you're unsure between...          | Ask...                                              |
| ------------------------------------ | --------------------------------------------------- |
| [[decompose]] vs [[design]]          | "Figure out what to do" vs "design how to do it"    |
| [[qa-demo]] vs [[prove-feature]]     | "Does it run?" vs "Does it integrate correctly?"    |
| [[simple-question]] vs [[design]]    | Pure info (no file mods) vs any file-modifying work |
| [[simple-question]] vs [[debugging]] | Pure info vs leads to investigation                 |
