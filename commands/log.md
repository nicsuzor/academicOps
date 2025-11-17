---
description: Log agent performance (successes and failures) to framework learning system
permalink: commands/log
---

Pause and **IMMEDIATELY** invoke the `framework` skill. The user is reporting agent behavior worth tracking—either a success to reinforce or a failure to address.

**Purpose**: Build institutional knowledge by logging patterns, not just failures. Track what works to avoid overweighting problems.

**CRITICAL - Documentation-Only Mode**: When invoked via this command, the framework skill operates in DOCUMENTATION-ONLY mode. You MUST:

✅ **DO**:

- Categorize the observation (Meta-Framework, Component-Level, or Behavioral Pattern)
- Determine if positive (✅ Success) or negative (❌ Failure)
- Log to `data/projects/aops/experiments/LOG.md`
- Keep entry brief (3 one-sentence points max)
- Tag with pattern for cross-reference

❌ **DO NOT**:

- Fix the user's original request that triggered the observation
- Implement solutions or attempt workarounds
- Investigate beyond initial pattern identification
- Write lengthy analysis

**Rationale**: This command logs single data points for pattern tracking. Solutions require multiple data points and experiment-driven validation.

**LOG.md must remain Obsidian/bmem compliant** - Fix frontmatter permalink (no slashes, use hyphens) and add required sections before appending entries.

**Log Format**:

```markdown
## [Category]: [Brief Title]

**Date**: YYYY-MM-DD | **Type**: ✅/❌ | **Pattern**: #tag

**What**: [One sentence observation] **Why**: [One sentence significance] **Lesson**: [One sentence action]
```

**Categories**:

- **Meta-Framework**: Framework maintenance process itself
- **Component-Level**: Specific parts (skills, hooks, scripts, tests)
- **Behavioral Pattern**: Agent behavior across components
