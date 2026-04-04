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
version: 2.0.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review

Multi-agent strategic review of documents, plans, and proposals. You are the supervisor — you commission review agents, evaluate their output, coach if needed, and iterate until the review meets quality standards.

## When to invoke

Use this when a document needs strategic review, not proofreading:

- Plans and implementation proposals
- Research proposals and grant applications
- PR reviews where architectural or epistemological problems may exist
- Design decisions and specs
- Any time the question "is this actually good, or just coherent?" matters

## Available agents

| Agent      | What they do                                   | When to use                                      |
| ---------- | ---------------------------------------------- | ------------------------------------------------ |
| **pauli**  | Strategic critique via 10 cognitive moves      | Primary reviewer — always commission first       |
| **rbg**    | Axiom compliance and workflow discipline check | When the review must verify framework compliance |
| **marsha** | Independent end-to-end verification            | When work products need QA before shipping       |

Commission agents via `Agent(subagent_type="aops-core:<name>", ...)`. Choose the model appropriate to the task (opus for depth, haiku for mechanical checks).

## Quality target

A strategic review is not a proofreading session with better vocabulary. It must:

1. **Operate at multiple abstraction levels** — address the specific instance AND the class of problem AND the system it's embedded in.
2. **Question the question** — not just answer what's asked, but assess whether the right question is being asked.
3. **Find the negative space** — identify what's MISSING, not just what's wrong.
4. **Calibrate severity** — distinguish fatal problems (rethink the approach) from fixable ones (revise and improve).
5. **Be grounded** — reference existing knowledge, not just internal consistency.
6. **Be actionable** — specify what to change, not just what's wrong.

## Your job as supervisor

1. **Understand the document.** What type is it? What is it trying to accomplish? What context does the reviewer need?

2. **Commission pauli.** Provide the full document and context. Let pauli work.

3. **Evaluate the output.** Does it meet the quality target above? If the review stayed at the surface level, didn't question the question, or missed the negative space — coach pauli and iterate. Don't accept competent proofreading as strategic review.

4. **Coach if needed.** Be specific about what's missing:
   - Surface-level → "What CLASS OF PROBLEM does this represent? What SYSTEM is it embedded in?"
   - Didn't question the question → "Is the question itself well-formed? Would an expert reframe it?"
   - Missed negative space → "What should be here that isn't? What feedback loop is absent?"

5. **Use rbg and marsha as the task requires.** Not every review needs all three agents. Trust your judgment about what the specific document needs.

6. **Produce the final output.** Include the review itself, your observation log (iterations, coaching, quality assessment), and an honest assessment of where the review falls short.

## Design rationale

The loop exists because one-shot prompting reliably produces competent-but-not-genius reviews: internally consistent, surface-level, answering the question as posed. The supervisor's job is to force elevation — from instance to class, from artifact to process, from "is this right?" to "is this the right question?".
