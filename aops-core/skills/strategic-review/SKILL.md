---
name: strategic-review
type: skill
category: instruction
description: Multi-agent strategic review of documents, plans, and proposals. Commissions review agents and iterates until the review meets quality standards. Use --critic for a fast pauli-only pre-hoc critique.
triggers:
  - "strategic review"
  - "pre-hoc plan evaluation"
  - "adversarial review"
  - "plan review"
  - "review this document"
  - "review this proposal"
  - "/strategic-review --critic"
  - "critic review"
  - "critic mode"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
  - quality-assurance
allowed-tools: Task,Read
version: 2.2.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review

Multi-agent strategic review of documents, plans, and proposals. Supports two modes:

| Mode       | Agent                    | Use when                                                               |
| ---------- | ------------------------ | ---------------------------------------------------------------------- |
| default    | James (multi-agent loop) | Full strategic review — architecture, compliance, runtime verification |
| `--critic` | Pauli (solo)             | Fast pre-hoc critique using 10 cognitive moves — plans, proposals      |

## When to invoke

Use this when a document needs strategic review, not proofreading:

- Plans and implementation proposals
- Research proposals and grant applications
- PR reviews where architectural or epistemological problems may exist
- Design decisions and specs
- Any time the question "is this actually good, or just coherent?" matters

## Critic mode (`/strategic-review --critic`)

For a focused, solo pre-hoc critique — invoke Pauli directly, bypassing the full James loop:

```
Agent(subagent_type="aops-core:pauli", prompt="[document or file path]")
```

Pauli applies 10 cognitive moves and returns a structured strategic critique. Use this before implementation when you want adversarial plan review without the overhead of full multi-agent orchestration. Equivalent to the former `/critic` command.

## Orchestrator: James (default mode)

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

## Demand Concrete Proof for Diagnostic Claims

When assessing a claim in a review (e.g. "I checked the logs and couldn't find any errors" or "there is no reason for the failure in the output"), do **not** accept a narrative summary at face value if the claim is load-bearing.

You must demand **concrete proof** of the negative result. The agent must surface primary evidence, not paraphrase.

Follow this exact pattern when rejecting hand-wavy claims:

1. **Name the artifact**: Tell the agent exactly which log, file, or stream to check.
2. **Demand specific lines**: Require them to show the literal failure line (or exit message) plus _N_ lines of context immediately preceding it.
3. **Require all perspectives**: If there are multiple sources (e.g., client + host), demand evidence from both sides.

**Worked Example (Colima early-exit framing):**

> "ok. now, are you absolutely sure that you cannot find any reason, in the client logs or in our colima logs on the host, that would explain the early exit? prove to me by showing the exit log messages and the three messages immediately before them in each case."

## Design rationale

The loop exists because one-shot prompting reliably produces competent-but-not-genius reviews: internally consistent, surface-level, answering the question as posed. James's job is to force elevation — from instance to class, from artifact to process, from "is this right?" to "is this the right question?". He also carries axiom compliance (Ruth) and runtime verification (Marsha) as non-negotiable dimensions that strategic review alone cannot provide.
