---
name: audit
category: instruction
description: Comprehensive framework governance audit - structure, justification, and index updates
---

Use the Skill tool to invoke the `audit` skill: `Skill(skill="audit")` - this will load instructions for comprehensive framework auditing.

This performs:
1. **Structure audit**: Compare filesystem to INDEX.md/README.md
2. **Justification audit**: Check each file traces to a spec or core doc
3. **Updates**: Fix missing entries, report orphans

**Output**: Structured report with actions taken and items requiring human review.
