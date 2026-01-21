---
id: simple-question
category: information
---

# Simple Question Workflow

Minimal workflow for answering informational questions that don't require modifications.

## When to Use

ONLY when ALL true:
- Question can be answered directly
- No file modifications needed
- No data changes needed
- No actions required
- Pure information request

## When NOT to Use

- Question leads to action (use appropriate workflow)
- Files need to be read/modified (use feature-dev or minor-edit)
- Question is exploratory (might need Explore agent)

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| "What is...", "How does...", "Where is..." | Simple question |
| "Can you...", "Please...", "Fix..." | Action request (different workflow) |

## Steps

1. Answer the question clearly and concisely
2. **HALT** - await further instructions

## Critical Rule

**Do NOT take unsolicited actions.** Answer the question, then stop. Let user decide next steps.

## Quality Gates

- Question answered clearly and correctly
- No unsolicited actions taken
- No file modifications made
- Awaiting user's next instruction
