---
id: skill-pilot
category: meta
---

# Skill Pilot Workflow

## Overview

Build new skills through supervised learning when decomposition reveals capability gaps. This is a meta-workflow: a workflow for creating workflows/skills.

**Key insight**: When you can't decompose a task into existing skills, that's not a failure—it's a signal that the framework needs a new skill.

## When to Use

- Decomposition reaches an irreducible task that doesn't map to any existing skill
- A task pattern recurs but has no standardized approach
- You're doing something for the first time and want to capture the learning

## When NOT to Use

- Task maps to an existing skill (just use that skill)
- One-off task unlikely to recur (just do it, don't build infrastructure)
- You're unsure what the task even requires (use [[decompose]] first)

## Prerequisites

- Task is well-understood enough to attempt
- User is available for interactive guidance
- Clear sense of what "success" looks like

## Steps

### 1. Articulate the Gap

Document what you're trying to do and why no existing skill covers it.

```markdown
## Skill Gap: [Name]

**Task**: [What needs to be done]
**Why no existing skill**: [Which skills were considered and why they don't fit]
**Expected recurrence**: [Will this pattern come up again?]
```

### 2. Pilot with User

Execute the task interactively, with the user providing guidance at decision points.

**During the pilot**:
- Narrate your reasoning aloud
- Ask when uncertain
- Note what works and what doesn't
- Capture the sequence of actions

**User role**:
- Provide domain knowledge
- Correct missteps early
- Validate approach before committing

### 3. Reflect on the Pilot

After completing the task, synthesize what you learned.

**Reflection prompts**:
- What was the key insight that made this work?
- What would you do differently next time?
- What are the essential steps vs. incidental details?
- What inputs does this need? What outputs does it produce?

### 4. Draft the Skill

Create a minimal SKILL.md in the appropriate location:

```bash
$AOPS/aops-tools/skills/[skill-name]/SKILL.md  # For general tools
$AOPS/aops-core/skills/[skill-name]/SKILL.md   # For framework operations
```

**SKILL.md structure**:
```markdown
---
name: [skill-name]
description: [One-line description for skill index]
---

# [Skill Name]

## When to Use
[Entry conditions - when should an agent invoke this skill?]

## Steps
[The procedure learned from the pilot]

## Quality Gates
[How to verify the skill was applied correctly]

## Examples
[The pilot case, anonymized if needed]
```

### 5. Test the Skill

Apply the new skill to a similar task (or re-run the pilot task) to verify it works without interactive guidance.

**Success criteria**:
- Task completes without user intervention
- Output meets quality expectations
- Skill instructions were sufficient

### 6. Index the Skill

If the skill lives in a plugin, update plugin.json to include it. Verify it appears in skill discovery:

```bash
# Check skill is discoverable
claude "/[skill-name]"  # Should invoke the new skill
```

## Quality Gates

- [ ] Gap clearly articulated before piloting
- [ ] User participated in pilot (supervised learning)
- [ ] Reflection captured key insights
- [ ] SKILL.md created with actionable instructions
- [ ] Skill tested on at least one task
- [ ] Skill indexed and discoverable

## Anti-Patterns

- **Premature abstraction**: Creating a skill after one use. Wait for recurrence.
- **Kitchen sink skill**: Cramming too much into one skill. Keep skills focused.
- **Orphan skill**: Creating a skill but not indexing it. If it's not discoverable, it doesn't exist.
- **Ivory tower skill**: Writing instructions without piloting. The pilot IS the learning.

## Example: Building "transcript-analysis" Skill

**Gap**: Need to analyze agent transcripts for compliance patterns. No existing skill covers this.

**Pilot**: Walked through transcript analysis with user. Learned to:
1. Load transcript JSON
2. Identify tool invocations
3. Check against principle list
4. Calculate compliance rate
5. Flag violations with context

**Reflection**: Key insight was structuring output as violation-list + summary stats. The compliance check needs the principle index loaded.

**Draft**: Created `aops-core/skills/transcript-analysis/SKILL.md` with steps from pilot.

**Test**: Re-ran on a different transcript. Skill instructions were sufficient.

**Index**: Added to plugin.json. `/transcript-analysis` now works.

## Integration with Other Workflows

- **decompose**: Skill-pilot is invoked when decompose hits an irreducible task
- **feature-dev**: If the new skill requires code, hand off implementation to feature-dev
- **remember**: Capture key learnings in semantic memory for future reference
