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

<!-- @nic: general rule: self-documenting files are good, but documentation should NOT be in template text that goes to a LLM. We EITHER have to delineate this markdown or move it into the frontmatter or spec file.  -->
<!-- @claude 2026-01-24: This file is type:index - it's for human reference and hydrator routing, not direct LLM injection. Individual workflow files (e.g., workflows/design.md) are what get loaded. Those should stay lean. This index can remain self-documenting. -->
<!-- @nic 2026-01-26: bullshit. this file is directly injected. reconsider. -->
<!-- @claude 2026-02-07: You're right - this file IS loaded by user_prompt_submit.py via load_workflows_index(). Task created: aops-25545fb8. Options: (1) Move explanatory content to a separate docs file, keeping only the routing table here, or (2) use frontmatter-only format like other indices. Recommend option 1. -->

Workflows are **hydrator hints**, not complete instructions. They tell the hydrator:

1. When this workflow applies (routing signals)
2. What's unique to this workflow
3. Which base workflows to compose

> **Design note (2026-01-25)**: The former `minor-edit` workflow was removed. Any file-modifying work requires full hydration planning—there is no "minor edit" category. Pure information requests route to `simple-question`; all file modifications route to `design` or more specific workflows.

## Base Workflows (Composable Patterns)

**Always consider these.** Most workflows compose one or more base patterns.

| Base                   | Pattern                                      | Skip When                             |
| ---------------------- | -------------------------------------------- | ------------------------------------- |
| [[base-task-tracking]] | Claim/create task, update progress, complete | [[simple-question]], [[direct-skill]] |
| [[base-tdd]]           | Red-green-refactor cycle                     | Non-code changes                      |
| [[base-verification]]  | Checkpoint before completion                 | Trivial changes                       |
| [[base-commit]]        | Stage, commit (why not what), push           | No file modifications                 |

## Decision Tree

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
    ├─ Investigating/debugging? ───────────────> [[debugging]]
    │
    ├─ Planning/designing known work? ─────────> [[design]]
    │   (know what to build, designing how)
    │
    ├─ Need QA verification? ──────────────────> [[qa-demo]]
    │
    └─ Framework governance change? ───────────> [[framework-change]]
```

## Scope-Based Routing

| Signal                                         | Route to             |
| ---------------------------------------------- | -------------------- |
| "Write a paper", "Build X", "Plan the project" | [[decompose]]        |
| "Add feature X", "Fix bug Y" (clear steps)     | [[design]]           |
| "How do I..." (information only)               | [[simple-question]]  |
| "Process all X", "batch update"                | [[batch-processing]] |
| "/commit", "/email" (skill name)               | [[direct-skill]]     |

## Available Workflows

### Development

| Workflow        | When to Use                           | Bases                       |
| --------------- | ------------------------------------- | --------------------------- |
| [[collaborate]] | Interactive exploration/brainstorming | task-tracking               |
| [[tdd-cycle]]   | Any testable code change              | tdd                         |
| [[debugging]]   | Cause unknown, investigating          | task-tracking, verification |

### Planning

| Workflow      | When to Use                   | Bases         |
| ------------- | ----------------------------- | ------------- |
| [[decompose]] | Multi-month, uncertain path   | task-tracking |
| [[design]]    | Known work, need architecture | task-tracking |

### Quality Assurance

| Workflow            | When to Use                     | Bases |
| ------------------- | ------------------------------- | ----- |
| [[critic-fast]]     | Quick sanity check (default)    | -     |
| [[critic-detailed]] | Framework/architectural changes | -     |
| [[qa-demo]]         | Pre-completion verification     | -     |
| [[qa-test]]         | User acceptance testing         | -     |
| [[prove-feature]]   | Integration validation          | -     |

### Operations

| Workflow                 | When to Use                                  | Bases             |
| ------------------------ | -------------------------------------------- | ----------------- |
| [[batch-processing]]     | Multiple independent items                   | task-tracking     |
| [[classify-task]]        | Complexity + graph positioning for new tasks | -                 |
| [[triage-email]]         | Email classification                         | -                 |
| [[email-reply]]          | Drafting replies                             | task-tracking     |
| [[interactive-triage]]   | Backlog grooming                             | -                 |
| [[interactive-followup]] | Simple session continuations                 | base-verification |
| [[peer-review]]          | Grant/fellowship reviews                     | task-tracking     |

### Information & Routing

| Workflow            | When to Use                        | Bases |
| ------------------- | ---------------------------------- | ----- |
| [[simple-question]] | Pure information, no modifications | -     |
| [[direct-skill]]    | 1:1 skill mapping                  | -     |

### Meta

| Workflow        | When to Use                   | Bases         |
| --------------- | ----------------------------- | ------------- |
| [[skill-pilot]] | Building new skills from gaps | task-tracking |
| [[dogfooding]]  | Framework self-improvement    | -             |

### Governance

| Workflow             | When to Use                   | Bases         |
| -------------------- | ----------------------------- | ------------- |
| [[framework-change]] | AXIOMS/HEURISTICS/enforcement | task-tracking |

### Hydration (Internal)

These workflows support prompt hydration. Used internally by the hydrator agent.

| Workflow | When to Use | Bases |
| -------- | ----------- | ----- |

| [[framework-gate]] | First check - detect framework modifications | - |
| [[constraint-check]] | Verify plan satisfies workflow constraints | - |

## Project-Specific Workflows

Projects can extend the global workflow catalog by defining local workflows in the project root:

1. **Local Index**: `.agent/WORKFLOWS.md`
   - If present, its content is injected into the hydration context.
   - Use this for project-wide workflow routing and definitions.

2. **Workflow Directory**: `.agent/workflows/*.md`
   - Individual workflow files.
   - **Content Injection**: The hydrator selectively injects the content of these files if the prompt matches the filename (e.g., "manual-qa" matches `manual-qa.md`).
   - Use these for specific, repetitive procedures unique to the project.

## Key Distinctions

| If you're unsure between...          | Ask...                                              |
| ------------------------------------ | --------------------------------------------------- |
| [[decompose]] vs [[design]]          | "Figure out what to do" vs "design how to do it"    |
| [[qa-demo]] vs [[prove-feature]]     | "Does it run?" vs "Does it integrate correctly?"    |
| [[simple-question]] vs [[design]]    | Pure info (no file mods) vs any file-modifying work |
| [[simple-question]] vs [[debugging]] | Pure info vs leads to investigation                 |
