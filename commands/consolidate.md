---
name: consolidate
category: instruction
description: Consolidate LOG.md entries into thematic learning files and archive
allowed-tools: Skill
permalink: commands/consolidate
---

**IMMEDIATELY** invoke the `[[skills/learning-log/SKILL.md|learning-log]]` skill with consolidation mode.

**Purpose**: Extract patterns from LOG.md, update thematic learning files, and archive processed entries to maintain bounded log growth.

## Consolidation Workflow

The skill executes:

1. **Read LOG.md** - Load all entries
2. **Group by Related field** - Cluster entries pointing to same learning file
3. **Extract patterns** - For clusters with 2+ entries, identify common factors
4. **Update learning files** - Append consolidated patterns to verification-skip.md, instruction-ignore.md, etc.
5. **Archive entries** - Move processed entries to LOG-ARCHIVE.md
6. **Clean LOG.md** - Remove archived entries, keep header

## Triggers

This command is one of three consolidation triggers:

| Trigger | Condition |
|---------|-----------|
| Manual | User runs `/consolidate` |
| Threshold | LOG.md exceeds 20 entries OR 14 days since last consolidation |
| Pattern | Same error type appears 3+ times |

## Output

After consolidation, reports:
- Entries processed
- Patterns identified
- Learning files updated
- Entries archived
