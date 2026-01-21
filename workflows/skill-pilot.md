---
id: skill-pilot
category: meta
---

# Skill Pilot Workflow

Build new skills through supervised learning when decomposition reveals capability gaps.

**Key insight**: When you can't decompose a task into existing skills, that's a signal the framework needs a new skill.

## When to Use

- Decomposition reaches irreducible task with no matching skill
- Task pattern recurs but has no standardized approach
- First-time task where you want to capture learning

## When NOT to Use

- Task maps to existing skill (just use it)
- One-off task unlikely to recur (just do it)
- Task unclear (use decompose first)

## Prerequisites

- Task well-understood enough to attempt
- User available for interactive guidance
- Clear success criteria

## Key Steps

1. **Articulate gap**: What task? Why no existing skill fits?
2. **Pilot with user**: Execute interactively, user guides decisions
3. **Reflect**: Key insights, essential vs incidental steps
4. **Draft SKILL.md**: Minimal skill file with when-to-use, steps, quality gates
5. **Test**: Apply to similar task without guidance
6. **Index**: Add to plugin.json, verify discoverable

## Quality Gates

- Gap articulated before piloting
- User participated (supervised learning)
- Reflection captured key insights
- SKILL.md created with actionable instructions
- Skill tested on at least one task
- Skill indexed and discoverable

## Anti-Patterns

- Premature abstraction (creating skill after one use)
- Kitchen sink skill (too much in one skill)
- Orphan skill (not indexed → doesn't exist)
- Ivory tower skill (writing without piloting)
