---
id: sync
title: Memory Sync Workflow
category: maintenance
---

# Memory Sync Workflow

Reconcile markdown files with PKB to ensure semantic search stays current.

## When to Run

- After direct markdown edits (bypassing remember skill)
- Periodically as part of `/garden` maintenance
- When semantic search seems stale or incomplete
- After PKB recovery/rebuild

## Modes

### Full Rebuild

Process all markdown files in `$ACA_DATA`:

```bash
# Pseudo-workflow (agent executes these steps)
1. Glob: $ACA_DATA/**/*.md
2. For each file:
   - Read content
   - Extract frontmatter (title, type, tags)
   - Store to PKB with source path
3. Report summary
```

### Incremental Sync

Process only files changed since last sync:

```bash
# Use git to find changed files
git diff --name-only HEAD~10 -- $ACA_DATA/**/*.md
```

## Implementation

Agent should execute:

```javascript
// 1. Get all markdown files
Glob(pattern="**/*.md", path="$ACA_DATA")

// 2. For each file, read and sync
for (file of files) {
  content = Read(file_path=file)

  // Extract first 500 chars for embedding (PKB handles chunking)
  summary = extractSummary(content)

  mcp__pkb__create_memory(
    title=extractTitle(content),
    body=summary,
    tags=extractTags(content)
  )
}

// 3. Report
"Synced X files to PKB"
```

## File Filtering

**Include:**

- `$ACA_DATA/projects/**/*.md`
- `$ACA_DATA/goals/*.md`
- `$ACA_DATA/context/*.md`
- `$ACA_DATA/knowledge/**/*.md`

**Exclude:**

- `$ACA_DATA/../sessions/*.md` (daily notes, not semantic knowledge - now outside $ACA_DATA)
- Files with `sync: false` in frontmatter
- Empty files

## Deduplication

PKB handles deduplication via content hashing. Re-syncing the same content is safe - it updates the existing entry rather than creating duplicates.

## Integration

### With /garden

The garden skill should include memory sync as part of periodic maintenance:

```markdown
## Garden Maintenance Includes

- Orphan detection
- Link repair
- **PKB sync** (reconcile markdown → PKB)
- Prune stale content
```

### With Remember Skill

This workflow is the **repair path** for when the dual-write pattern is bypassed. Normal flow:

1. New content → remember skill → markdown + PKB (atomic)
2. Direct edit → PKB drifts → sync workflow → reconciled

## Success Criteria

- [ ] All markdown files in scope have corresponding PKB entries
- [ ] PKB entries have correct source metadata (path to markdown file)
- [ ] No orphaned PKB entries (entries without corresponding markdown)
- [ ] Semantic search returns results for content in `$ACA_DATA`
