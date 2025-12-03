---
name: bmem
description: Invoke bmem skill to capture session information and update knowledge base
permalink: commands/bmem
---

Use the Skill tool to invoke the `bmem` skill: `Skill(skill="bmem")` - this will load instructions for extracting information from the current session and updating the knowledge base in `data/`.

# Bmem: Knowledge Base Update

Use this command to explicitly trigger knowledge base capture and updates.

**What it does**:

1. Mines current conversation for extractable information
2. Updates relevant files in `data/` (projects, goals, context)
3. Creates or updates bmem-formatted markdown files
4. Maintains knowledge graph with WikiLinks and relations
5. Commits and pushes changes to git

**Example triggers**:

- "capture this for the knowledge base"
- "save this to the project file"
- "update the knowledge graph"
- "document this decision"

**Note**: The bmem skill runs silently in the background during sessions. Use this command when you want to explicitly trigger capture or ensure information is saved.

**Full documentation**: [[skills/bmem/SKILL.md]]
