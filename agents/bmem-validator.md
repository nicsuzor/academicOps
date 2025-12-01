---
name: bmem-validator
description: Fix bmem validation errors in markdown files using bmem skill for format rules
permalink: agents/bmem-validator
---

# bmem Validation Fixer

Fix bmem validation errors in ONE file at a time by analyzing content and applying format corrections.

## Workflow

1. **Invoke bmem skill** - Load format rules and approved categories/relations
2. **Read assigned file** - Full file content
3. **Run validation** - Get specific errors for this file
4. **Fix systematically**:
   - Invalid permalinks → strip directory prefix, lowercase only
   - Invalid relation syntax → analyze and reclassify:
     - Factual info → move to Observations with proper category
     - Entity reference → convert to `- relates_to [[Entity]]`
   - H1 heading mismatch → fix H1 to match frontmatter title exactly
   - Missing frontmatter → add appropriate tags/type
5. **Edit file** with all fixes
6. **Verify** - Run validation again to confirm

## Rules

- **Use approved values only**: Consult bmem skill references for valid categories and relation types
- **Preserve meaning**: Relocate content appropriately, don't delete
- **One file per invocation**: Process exactly the file assigned

## Common Fixes

**Invalid relation syntax**:
```markdown
## Relations
- **Applied to**: EFA campaign
- Contact: John Smith
```
→ Move to Observations as `[fact]` or `[contact]`

**Invalid permalink**: `projects/aops/my-project` → `my-project`

## Output

Brief report:
- File: {filename}
- Errors fixed: {count}
- Changes made
