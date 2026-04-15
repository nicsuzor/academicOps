---
id: sync
title: Memory Sync Workflow
category: maintenance
---

# Memory Sync Workflow

Reconcile the on-disk markdown tree with the PKB index. **This is a repair path for legacy or externally-authored files**, not a workflow any agent should rely on during normal capture. Normal capture flows through PKB MCP exclusively (see [[capture-workflow]] and `SKILL.md` hard rules); if an agent is tempted to "write then sync", the skill is being used wrong.

**When to Run**: When the on-disk tree is edited by a non-PKB actor (user hand-edit, external import, git merge bringing in new files), or periodically as part of `/planner` maintain mode to catch drift.

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

### With /planner (maintain mode)

The planner skill's maintain mode includes memory sync as part of its periodic maintenance (orphan detection, link repair, prune stale content).

### With Remember Skill

This workflow is the **repair path** for drift introduced by non-PKB actors (user hand-edits, external imports, git merges). The normal capture flow is a single PKB MCP call — there is no "dual write" to reconcile under correct usage. If this workflow runs often in a healthy system, investigate which actor is bypassing PKB.

## Success Criteria

- [ ] All markdown files in scope have corresponding PKB entries.
- [ ] PKB entries have correct source metadata (path to markdown file).
- [ ] No orphaned PKB entries (entries without corresponding markdown).
- [ ] Semantic search returns results for content in `$ACA_DATA`.
