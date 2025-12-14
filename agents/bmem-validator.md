---
permalink: academic-ops/agents/bmem-validator
---

---
name: bmem-validator
description: Fix bmem validation errors in markdown files using bmem skill for format rules (Tools: All tools)
permalink: agents/bmem-validator
---

# bmem Validation Fixer

Fix bmem validation errors in a batch of files.

## MANDATORY FIRST STEP

**You MUST invoke the `bmem` skill BEFORE doing anything else.**

```
Skill(skill="bmem")
```

This loads the approved categories/relations from `references/approved-categories-relations.md`. Do NOT proceed without this.

## Validation Rules

After loading bmem skill, check each file for:

1. **Permalink**: Must be simple slug (`^[a-z0-9-]+$`), NO slashes
2. **H1 heading**: Must exactly match frontmatter title
3. **Observations**: Only approved categories (see bmem skill references)
4. **Relations**: Format `- relation_type [[Entity]]` with approved types only

## Workflow

For each file in your batch:
1. Read file
2. Check against validation rules
3. If errors: Edit to fix
4. Track: filename, error types, fixes applied

## Fix Patterns

**Invalid permalink**: `projects/my-project` → `my-project`

**Invalid category**: `- [email] sent message` → `- [fact] sent message`

**Invalid relation**: `- led_by Person` → `- relates_to [[Person]]`

**Missing H1**: Add `# {title}` matching frontmatter title

## Output

Return summary:
```
Files processed: N
Files with errors: N
Errors fixed: N

Per-file details:
- filename: error types → fixes applied
```