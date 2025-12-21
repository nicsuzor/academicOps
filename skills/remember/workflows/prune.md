---
title: Prune Workflow
type: workflow
permalink: prune-workflow
tags:
  - memory
  - workflow
  - maintenance
---

# Prune Workflow

Aggressively clean knowledge base by removing low-value files. Extract facts before deletion.

**Philosophy**: Email archive is the backup. Knowledge base should contain ONLY things worth searching for.

## When to Use

- "clean up", "declutter", "prune"
- Knowledge base feels bloated
- Too many low-value files cluttering search

## Classification Criteria

### DELETE (No extraction)

Files with zero lasting value:

- Raw email transcripts ("Thank you!", "See attached")
- Pure scheduling (meeting times, locations)
- Auto-generated noise (confirmations, password resets)
- Orphaned coordination ("Let me know if that works")
- Duplicates where content exists elsewhere

**Test**: Would you ever search for this? If "no way" → DELETE

### EXTRACT_DELETE

Files with mostly noise but some facts worth keeping:

- Contact files with scheduling noise → extract role/affiliation
- Project coordination → extract decisions/outcomes
- Event logistics → extract what happened/who attended

**Process**:
1. Identify target file (existing contact/project)
2. Extract facts as observations
3. Append to target file
4. Delete source via `git rm`

**Test**: Is there ONE fact worth adding to another file? Extract it, then DELETE.

### KEEP

Files with lasting value:

- Substantive prose (notes, reflections, analysis)
- Research content (literature notes, findings)
- Strategic context (why decisions were made)
- Relationship substance (collaboration history)

**Test**: Is this actual prose or substantive content? → KEEP

## Workflow

### Phase 1: Discovery

```bash
# Count files
find $ACA_DATA/<target> -name "*.md" -type f | wc -l

# Sample types
grep -roh "^type: .*" $ACA_DATA/<target> --include="*.md" | sort | uniq -c
```

### Phase 2: Classification

For each file:
1. Read completely
2. Classify: DELETE | EXTRACT_DELETE | KEEP
3. For EXTRACT_DELETE: identify facts and target

### Phase 3: User Decisions

For unclear extractions, ask user:
- Where should facts go?
- Create new file or add to existing?
- Skip extraction and just delete?

### Phase 4: Execute

**DELETE**:
```bash
git rm "<file_path>"
```

**EXTRACT_DELETE**:
1. Append facts to target file
2. Delete source: `git rm "<file_path>"`

### Phase 5: Commit

```bash
git add -A
git commit -m "cleanup(kb): remove N files, extract M facts

Deleted: [count] files
Extracted to: [list]
Kept: [count] files"
```

## Fact Extraction Format

```markdown
- [fact] Person's role at Organization #affiliation
- [collaboration] Worked together on X in 2013 #history
- [event] Attended conference Y #professional
- [decision] Chose approach A because B #strategic
```

**DO NOT extract**:
- Scheduling logistics
- Ephemeral coordination
- Pleasantries

## Decision Tree

```
Is it substantive prose/notes?
├─ Yes → KEEP
└─ No → Is there any fact worth saving?
         ├─ Yes → EXTRACT_DELETE
         └─ No → DELETE
```

## Safety

- All deletions via `git rm` (recoverable)
- Commit after each batch
- Can always `git checkout` to recover
