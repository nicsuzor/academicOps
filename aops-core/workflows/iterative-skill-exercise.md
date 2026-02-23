---
id: iterative-skill-exercise
category: quality
bases: [base-task-tracking, base-verification, base-commit]
status: draft
---

# Iterative Skill Exercise

**DRAFT** — Anti-shortcut workflow for long-running tasks that require the agent to exercise skills thoroughly rather than cutting corners.

## Purpose

When a task involves processing many items (papers to read, applications to review, data to annotate), agents tend to summarize or batch-process rather than engaging deeply with each item. This workflow enforces iterative, thorough skill exercise.

## When to Apply

- Reading and annotating a corpus (don't summarize — read each one)
- Reviewing multiple applications (don't template — assess each individually)
- Data annotation or coding tasks (don't infer — examine each case)
- Any task where depth per item matters more than throughput

## Procedural Requirements

### 1. Enumerate

- List all items to be processed
- Estimate per-item effort
- Human approval: confirm scope and approach

### 2. Iterate

For each item:
- Exercise the relevant skill on THIS item fully
- Record findings/output for THIS item
- Checkpoint: item-level verification before moving to next
- No batching, no summarizing across items during processing

### 3. Checkpoint

After every N items (configurable, default 5):
- Present progress summary to user
- Quality check: are outputs maintaining depth?
- Adjust approach if quality is degrading

### 4. Synthesize

Only after all items are individually processed:
- Cross-item analysis is now appropriate
- Patterns, themes, summary — built from per-item evidence

## Anti-Patterns

- "I'll summarize these 50 papers" — NO, read and annotate each
- "These applications are similar, so I'll use a template response" — NO, assess individually
- Skipping items that seem redundant — every item gets full attention
- Front-loading synthesis before completing individual processing

## Key Principle

Depth per item, then synthesis. Never synthesis instead of depth.
