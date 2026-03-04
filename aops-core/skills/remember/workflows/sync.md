---
id: sync
title: Memory Sync Workflow
category: maintenance
---

# Memory Sync Workflow

Reconcile markdown files with PKB to ensure semantic search stays current.

**When to Run**: After direct markdown edits, periodically as part of `/garden` maintenance, or when semantic search seems stale.

## Sync Modes

### Full Rebuild

Process all markdown files in `$ACA_DATA`. Read content, extract frontmatter, and store to PKB with source path.

### Incremental Sync

Process only files changed since the last sync (e.g., using `git diff` to find recent changes).

## Implementation Steps

1. **Discovery**: Get all markdown files in `$ACA_DATA` (excluding sessions and files with `sync: false`).
2. **Read and Extract**: For each file, read the content and extract the title, body summary, and tags.
3. **PKB Update**: Use `mcp__pkb__create_memory` to sync the extracted content to the PKB.
4. **Report**: Summarize the number of files successfully synced.

## File Filtering

- **Include**: `$ACA_DATA/projects/**/*.md`, `goals/*.md`, `context/*.md`, `knowledge/**/*.md`.
- **Exclude**: Daily notes outside `$ACA_DATA`, files with `sync: false` in frontmatter, and empty files.

## Deduplication

PKB handles deduplication via content hashing. Re-syncing the same content is safe - it updates the existing entry rather than creating duplicates.

## Integration

### With /garden

The garden skill includes memory sync as part of its periodic maintenance (orphan detection, link repair, prune stale content).

### With Remember Skill

This workflow is the **repair path** for when the dual-write pattern is bypassed. Normal flow is atomic (markdown + PKB). Direct edits cause drift, which this workflow reconciles.

## Success Criteria

- [ ] All markdown files in scope have corresponding PKB entries.
- [ ] PKB entries have correct source metadata (path to markdown file).
- [ ] No orphaned PKB entries (entries without corresponding markdown).
- [ ] Semantic search returns results for content in `$ACA_DATA`.
