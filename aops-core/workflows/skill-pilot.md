---
id: skill-pilot
category: meta
bases: [base-task-tracking]
---

# Skill Pilot

<!-- NS: merge into 'dogfooding', covers same ground. -->
<!-- @claude 2026-02-07: Reviewed both. skill-pilot focuses on building NEW skills from capability gaps; dogfooding is about TESTING existing skills. Different purposes. Recommend keeping separate but clarifying scope in each. Task created: aops-99925a89. -->

Build new skills when [[decompose]] reveals capability gaps.

## Routing Signals

- Decomposition reaches task with no matching skill
- Recurring pattern without standardized approach
- First-time task worth capturing

## NOT This Workflow

- Task maps to existing skill → use it
- One-off unlikely to recur → just do it
- Task unclear → [[decompose]] first

## Unique Steps

1. Articulate gap: What? Why no existing skill?
2. Pilot with user: Interactive, supervised learning
3. Reflect: Essential vs incidental steps
4. Draft SKILL.md: when-to-use, steps, quality gates
5. Test: Apply to similar task without guidance
6. Index: Add to plugin.json

## Anti-Patterns

- Premature abstraction (skill after one use)
- Kitchen sink (too much in one skill)
- Orphan skill (not indexed = doesn't exist)
