# Skill Pilot Workflow

Build new skills when decompose reveals capability gaps.

Extends: base-task-tracking

## When to Use

Use this workflow when:
- Decomposition reaches a task with no matching skill
- A recurring pattern exists without a standardized approach
- A first-time task is worth capturing for reuse

Do NOT use for:
- Task maps to existing skill (just use it)
- One-off task unlikely to recur (just do it)
- Task is unclear (use decompose first)

## Constraints

### Skill Creation Sequencing

1. **Articulate the gap** before piloting: What capability is missing? Why doesn't an existing skill fit?
2. **Pilot with user** before reflecting: Interactive, supervised learning
3. **Reflect** before drafting: Distinguish essential steps from incidental ones
4. **Draft the skill** before testing: Create SKILL.md with when-to-use, steps, and quality gates
5. **Test the skill** before indexing: Apply to a similar task without guidance
6. **Index the skill** after testing: Add to plugin.json

### Quality Gate

A skill must be indexed in plugin.json to exist. An unindexed skill is an orphan.

### Anti-Patterns (Never Do)

- **Premature abstraction**: Never create a skill after only one use
- **Kitchen sink**: Never put too much into one skill
- **Orphan skill**: Never leave a skill unindexed (not in plugin.json)

## Triggers

- When capability gap is found → articulate the gap
- When gap is articulated → pilot with user
- When pilot is complete → reflect on steps
- When reflection is complete → draft the skill
- When skill is drafted → test the skill
- When skill is tested → index in plugin.json

## How to Check

- Gap articulated: clear statement of what's missing and why no existing skill fits
- Pilot complete: task performed interactively with user supervision
- Reflection complete: essential steps distinguished from incidental ones
- Skill drafted: SKILL.md exists with when-to-use, steps, and quality gates
- Skill tested: skill applied to a similar task successfully without guidance
- Indexed in plugin.json: skill is listed in the plugin.json skills array
- Skill after one use: creating a skill after only one occurrence
- Too much in one skill: skill tries to do multiple distinct things
- Skill not indexed: skill file exists but is not in plugin.json
