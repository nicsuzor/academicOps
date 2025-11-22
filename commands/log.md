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
4. **Categorize** - assign pattern tags (#verify-first, #instruction-following, #git-safety, etc.)
5. **Select target file** - route to appropriate thematic learning file based on pattern tags
6. **Format** - structure entry per learning file specification
7. **Validate** - ensure target file exists with valid bmem frontmatter
8. **Append** - add entry to thematic file at `$ACA_DATA/projects/aops/learning/`

**Thematic files**:
- `verification-discipline.md` - verify-first violations, overconfidence
- `instruction-following.md` - ignoring explicit instructions
- `git-and-validation.md` - --no-verify usage, validation bypass
- `skill-and-tool-usage.md` - skill invocation failures
- `test-and-tdd.md` - TDD violations, test discipline
- `technical-wins.md` - successful patterns to reinforce

**What the agent does NOT do**:

- Fix the reported issue (logs only, doesn't implement solutions)
- Ask for user confirmation (operates autonomously)
- Append to monolithic LOG.md (uses thematic files instead)

**User provides**: Brief description of observation (success or failure)

**Agent delivers**: Structured log entry with investigation context and knowledge graph cross-references

See agents/log-agent.md for complete workflow specification.
