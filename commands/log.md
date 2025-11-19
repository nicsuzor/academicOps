---
description: Log agent performance (successes and failures) to framework learning system
permalink: commands/log
---

**IMMEDIATELY** invoke the `log-agent` with the user's observation description.

**Purpose**: Build institutional knowledge by logging patterns with investigation and knowledge linking.

The log-agent will autonomously:

1. **Load framework context** (via framework skill) - understand what should be happening
2. **Investigate failures** (via framework-debug skill) - diagnose root causes when applicable
3. **Link knowledge** (via bmem skill) - cross-reference related framework concepts
4. **Categorize** - classify as Meta-Framework, Component-Level, or Behavioral Pattern
5. **Format** - structure entry per LOG.md specification
6. **Validate** - ensure LOG.md frontmatter is bmem-compliant
7. **Append** - add entry to $ACA_DATA/projects/aops/experiments/LOG.md

**What the agent does NOT do**:

- Fix the reported issue (logs only, doesn't implement solutions)
- Ask for user confirmation (operates autonomously)
- Create new experiment files (appends to LOG.md only)

**User provides**: Brief description of observation (success or failure)

**Agent delivers**: Structured log entry with investigation context and knowledge graph cross-references

See agents/log-agent.md for complete workflow specification.
