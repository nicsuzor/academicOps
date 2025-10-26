---
name: agent-initialization
description: This skill should be automatically invoked when initializing a workspace to create/update an AGENT.md file that instructs agents to search for and use existing skills before attempting tasks. The skill scans available skills and maintains an up-to-date index with descriptions of when to invoke each skill.
---

# Agent Initialization

## Overview

This skill automatically creates or updates an `AGENT.md` file in the workspace root that instructs agents to use existing skills before attempting to solve tasks from scratch. It ensures agents leverage documented patterns, workflows, best practices, and reusable resources from the workspace's skill library.

## When to Use This Skill

This skill should be automatically invoked when:
- An agent initializes in a workspace for the first time
- A new skill is added to the workspace skill library
- Skills are updated and the index needs refreshing
- The user explicitly requests updating the agent initialization file

**Automatic invocation recommended** - This skill should run proactively to ensure agents are always aware of available skills.

## What This Skill Does

Creates or updates `AGENT.md` in the workspace root (typically `.claude/` or project root) with:

1. **Skills-first directive**: Clear instruction to search for relevant skills before implementing solutions
2. **Skills index**: Comprehensive list of all available skills with descriptions organized by category
3. **Usage guidance**: Instructions on how to identify and invoke relevant skills
4. **Maintenance note**: Indication that the file is auto-generated and should be kept current

**Important**: If `AGENT.md` already exists, this skill intelligently updates it by:
- Refreshing the skills index section with current skills
- Preserving any custom instructions or modifications
- Maintaining the essential skills-first directives

## Implementation Process

### Step 1: Scan Available Skills

Discover all skills in the workspace by:
1. Searching for `SKILL.md` files in the skills directory (typically `.claude/skills/`)
2. Extracting metadata from YAML frontmatter (name, description)
3. Organizing skills into logical categories based on their descriptions

Example code to scan skills:

```python
import yaml
from pathlib import Path

skills_dir = Path('.claude/skills')
skills = []

for skill_file in sorted(skills_dir.glob('*/SKILL.md')):
    content = skill_file.read_text()
    if content.startswith('---'):
        yaml_end = content.find('---', 3)
        if yaml_end > 0:
            frontmatter = yaml.safe_load(content[3:yaml_end])
            skills.append({
                'name': frontmatter.get('name'),
                'description': frontmatter.get('description')
            })
```

### Step 2: Categorize Skills

Organize discovered skills into categories based on their purpose:

- **Development & Code Quality**: python-dev, test-writing, git-commit, etc.
- **Project & Task Management**: task-management, github-issue, etc.
- **Framework & Skills**: skill-creator, skill-migration, aops-bug, aops-trainer, etc.
- **Domain-Specific**: analyst, strategic-partner, etc.

Categorization helps agents quickly identify relevant skills for their current task.

### Step 3: Generate or Update AGENT.md

**If `AGENT.md` does not exist:**
- Use the complete template from `references/AGENT.md` as the base
- Update the skills index section with discovered skills
- Write the file to the workspace root

**If `AGENT.md` already exists:**
- Read the existing file
- Identify the skills index section (typically between "## Available Skills Index" and the next section)
- Replace only the skills index with updated content
- Preserve all other sections and custom instructions
- Write the updated file back

### Step 4: Verify and Report

After creating or updating the file:
1. Confirm the file exists and is readable
2. Verify the skills index is complete and current
3. Report the action taken (created or updated) and the number of skills indexed

## Reference Template

The complete reference template for the `AGENT.md` file is available in `references/AGENT.md`. This template includes:

- Clear skills-first directive
- Placeholder for the skills index (to be populated with actual skills)
- Usage guidance for agents
- Maintenance note

When implementing this skill, use the reference template as the base and populate it with the actual skills discovered in the workspace.

## Benefits

By maintaining an up-to-date `AGENT.md` file, this skill ensures:

- **Consistency**: Agents always follow the same skills-first approach
- **Discoverability**: All available skills are visible to agents at session start
- **Efficiency**: Agents can quickly identify relevant skills without searching
- **Quality**: Solutions leverage vetted patterns and best practices from skills
- **Maintainability**: The skills index stays current as skills are added or updated

## Example Usage

When invoked, this skill might produce output like:

```
Scanning skills in .claude/skills/...
Found 12 skills:
  - analyst
  - aops-bug
  - aops-trainer
  - git-commit
  - github-issue
  - no-throwaway-code
  - python-dev
  - skill-creator
  - skill-migration
  - strategic-partner
  - task-management
  - test-writing

Updating AGENT.md with current skills index...
✓ AGENT.md updated successfully with 12 skills across 4 categories
```

## Notes

- This skill should be run whenever the skills directory changes
- The skills index in `AGENT.md` should always reflect the current state of the workspace
- Custom sections in an existing `AGENT.md` should be preserved during updates
- Consider running this skill as part of workspace initialization or CI/CD processes
