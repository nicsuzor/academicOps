---
title: "Skill Design"
type: guidance
description: "Best practices for creating effective Claude Code skills, including structure requirements, required components for skill-first architecture, and script-enhanced workflows."
tags:
  - skill
  - skill-design
  - best-practices
  - skill-first
relations:
  - "[[docs/bots/BEST-PRACTICES]]"
  - "[[docs/bots/SUBAGENT-DESIGN]]"
  - "[[docs/bots/COMMAND-DESIGN]]"
---

# Skill Design

Best practices for creating effective Claude Code skills.

**Source**: [Claude Code Plugins, Anthropic](https://www.anthropic.com/news/claude-code-plugins)

---

## Skills vs Commands

**Skills**: Richer context, validation scripts, organized reference material
**Commands**: Simple prompt expansion

Use skills when:
- Complex workflows require structured guidance
- Scripts or validation logic needed
- Multiple reference documents required
- Reusable across projects

---

## Skill Structure

```
skills/
  skill-name/
    skill.md          # Main prompt (YAML frontmatter + instructions)
    scripts/          # Automation/validation scripts
    references/       # Supporting documentation
```

---

## Design Principles

### 1. Self-Contained Guidance

Skills should provide complete, actionable instructions without requiring external knowledge.

### 2. Reference Over Inline

```markdown
❌ BAD: Include 200 lines of inline instructions

✅ GOOD: Include 50 lines of core instructions + @reference to detailed docs
```

### 3. Script-Enhanced Workflows

Use scripts for:
- Validation (checking code quality, test patterns)
- Automation (running tools, gathering context)
- Complex logic (parsing, analysis)

### 4. Focused Expertise

Each skill should represent deep expertise in one domain, not shallow coverage of many.

### 5. Required Components for Skill-First Architecture

To support the mandatory skill-first pattern, ALL skills must include:

**a) Documentation Index** - Clear references to all relevant docs:
```markdown
## References
- Core instructions: `@$ACADEMICOPS/core/_CORE.md`
- Best practices: `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`
- Detailed guide: `@$ACADEMICOPS/references/specific-guide.md`
```

**b) Workflow Checklist** - Step-by-step process:
```markdown
## Workflow
1. [Step 1 with specifics]
2. [Step 2 with specifics]
3. [Step 3 with specifics]
```

**c) Critical Rules** - Key principles and constraints:
```markdown
## Critical Rules
**NEVER**: [List of prohibited actions]
**ALWAYS**: [List of required actions]
```

**d) Quick Reference** - Condensed lookup for experienced users:
```markdown
## Quick Reference
- Pattern A: [Brief description]
- Pattern B: [Brief description]
```

**Why Required**: These components ensure skills serve as comprehensive entry points, preventing agents from searching for context independently.
