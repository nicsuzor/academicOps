---
name: strategic-review
type: skill
category: instruction
description: Multi-agent strategic review of documents, plans, and proposals. Commissions review agents and iterates until the review meets quality standards.
triggers:
  - "strategic review"
  - "pre-hoc plan evaluation"
  - "adversarial review"
  - "plan review"
  - "review this document"
  - "review this proposal"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
  - quality-assurance
allowed-tools: Task,Read
version: 2.1.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review

Multi-agent strategic review of documents, plans, and proposals. The orchestrator is **James** — commission James and let him manage the agent loop. If you are James, this skill is your operating context.

## When to invoke

Use this when a document needs strategic review, not proofreading:

- Plans and implementation proposals
- Research proposals and grant applications
- PR reviews where architectural or epistemological problems may exist
- Design decisions and specs
- Any time the question "is this actually good, or just coherent?" matters

## Orchestrator: James

Commission James as the orchestrator. He manages the agent loop, evaluates output quality, iterates, and synthesises.

```
Agent(subagent_type="aops-core:james", prompt="[artifact + context]")
```

James will commission the right agents based on the artifact type and load the appropriate review context descriptor. You do not need to manage the agent loop — James does that.

## Review Context Descriptors

Context descriptors in `review-contexts/` configure James's behavior per artifact type:

| Descriptor        | When to use                                                   |
| ----------------- | ------------------------------------------------------------- |
| `pr-code.md`      | Code PRs — features, fixes, refactors                         |
| `pr-framework.md` | Framework PRs — skills, agents, hooks, enforcement, workflows |

James will read the relevant descriptor automatically based on what you tell him about the artifact.

## The Three Agents

| Agent      | What they do                                             | Ruth always runs      |
| ---------- | -------------------------------------------------------- | --------------------- |
| **rbg**    | Axiom compliance and workflow discipline — The Judge     | Yes — non-negotiable  |
| **pauli**  | Strategic critique via 10 cognitive moves — The Logician | As needed             |
| **marsha** | Independent runtime verification — The QA Reviewer       | When code is involved |

## Design rationale

The loop exists because one-shot prompting reliably produces competent-but-not-genius reviews: internally consistent, surface-level, answering the question as posed. James's job is to force elevation — from instance to class, from artifact to process, from "is this right?" to "is this the right question?". He also carries axiom compliance (Ruth) and runtime verification (Marsha) as non-negotiable dimensions that strategic review alone cannot provide.
