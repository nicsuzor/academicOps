# Analyst Skill Draft Instructions

This directory holds informal notes and draft instructions that may eventually be promoted to formal documentation in `_CHUNKS/`.

## Purpose

Capture ideas, patterns, and insights during research work that might become formalized instructions later. This is a holding area for:

- Emerging patterns from real research work
- Documentation ideas that need refinement
- Process insights before we know if they're universal
- Experimental instruction concepts

## Workflow

### Adding Notes

Simply say: **"analyst draft:"** followed by your notes.

Example:
```
analyst draft:
I noticed we always create an archive before major data changes.
Maybe we need formal guidance on this...
```

The agent will:
1. Read your notes
2. Determine the topic/category
3. Add them to an appropriate draft file with timestamp
4. Organize similar notes together

### Draft Files

Files are organized by topic (e.g., `experiment_archival.md`, `documentation_patterns.md`). Each file contains timestamped notes that can be reviewed and refined later.

### Promoting to Formal Instructions

When patterns are validated:
1. Review the draft file
2. Extract proven patterns
3. Formalize into proper instructions
4. Add to `_CHUNKS/` or update existing chunks
5. Archive or remove the draft notes

## Current Draft Files

- `experiment_archival.md` - Notes on archiving analysis before data changes
- (More files will be added as patterns emerge)

## Guidelines

**DO add here:**
- ✅ Emerging patterns you're noticing
- ✅ Ideas that might become instructions
- ✅ Process insights from real work
- ✅ "Maybe we should..." thoughts

**DON'T add here:**
- ❌ One-off project-specific notes (those go in project docs)
- ❌ Temporary TODOs (use GitHub issues)
- ❌ Personal reminders (use scribe/personal data)

## Maintenance

Review drafts periodically (monthly) to:
- Promote validated patterns to formal instructions
- Remove notes that didn't pan out
- Consolidate similar observations
- Archive outdated thinking
