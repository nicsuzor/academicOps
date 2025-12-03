---
description: Log agent performance (successes and failures) to framework learning system
permalink: commands/log
---

**IMMEDIATELY** invoke the `learning-log` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging patterns to thematic learning files.

The skill will:

1. **Categorize** - assign pattern tags (#verify-first, #instruction-following, #git-safety, etc.)
2. **Link knowledge** (via bmem) - cross-reference related framework concepts
3. **Route** - select target thematic file based on pattern tags
4. **Format** - structure entry per learning file specification
5. **Validate** - ensure target file exists with valid bmem frontmatter
6. **Append** - add entry to thematic file at `$ACA_DATA/projects/aops/learning/`

**Thematic files**:
- `verification-discipline.md` - verify-first violations, overconfidence
- `instruction-following.md` - ignoring explicit instructions
- `git-and-validation.md` - --no-verify usage, validation bypass
- `skill-and-tool-usage.md` - skill invocation failures
- `test-and-tdd.md` - TDD violations, test discipline
- `technical-wins.md` - successful patterns to reinforce

**User provides**: Brief description of observation (success or failure)

**Skill delivers**: Structured log entry with knowledge graph cross-references

See skills/learning-log/SKILL.md for complete workflow specification.
