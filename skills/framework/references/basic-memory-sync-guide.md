---
title: Basic Memory Database Sync & Maintenance Guide
type: reference
permalink: basic-memory-sync-guide
description: Guide for Basic Memory synchronization, database maintenance, and troubleshooting
tags:
  - reference
  - basic-memory
  - database
  - maintenance
  - sync
---

# Basic Memory Database Sync & Maintenance Guide

**Source**: https://docs.basicmemory.com/ (Retrieved 2025-11-18)
**Version**: 0.16.1

## Overview

Basic Memory uses a **file-first design** where all knowledge is represented in standard Markdown files and the database serves as a secondary index.

## Real-Time Synchronization

**Default behavior**: Basic Memory automatically syncs file changes in real-time. No manual sync needed.

**Sync process**:
1. **Detects Changes** - identifies modifications to files in the knowledge directory
2. **Parses Files** - extracts structured data from modified files
3. **Updates Database** - applies changes to the SQLite database
4. **Resolves References** - handles forward references when new entities are created
5. **Updates Search Index** - maintains the full-text search capability

## Configuration

**Sync settings** (configurable via config file or environment variables):

- `sync_changes`: Boolean toggle (default: true) - controls whether modifications propagate automatically
- `sync_delay`: Milliseconds to pause after edits before syncing (default: 1000ms) - prevents excessive operations during rapid changes
- `sync_thread_pool_size`: Thread pool size for I/O operations (default: 4)

**Environment variables** override config file settings:
```bash
BASIC_MEMORY_SYNC_DELAY=2000 basic-memory mcp
```

## File Filtering

**`.gitignore` support**: Basic Memory respects `.gitignore` patterns to exclude:
- Sensitive files (credentials, keys)
- Build artifacts
- OS-specific files (`.DS_Store`, etc.)
- Dependencies (`node_modules/`, `.venv/`, etc.)

**CRITICAL**: `.gitignore` filtering only applies during initial indexing and ongoing file watching. **Files already in the database are NOT removed when added to `.gitignore`.**

## Database Status & Health

**Check sync status**:
```bash
basic-memory status
```
Shows current synchronization state for all projects. See [[basic-memory-mcp-tools]] for MCP tool reference.

**Check project details**:
```bash
basic-memory project info <project_name>
```
Displays:
- Entity counts by type
- Observation counts
- Relations (resolved and unresolved)
- Most connected entities
- Recent activity

## Handling Deleted Files

**PROBLEM**: Basic Memory does **not** automatically detect when files are deleted from the file system. The database retains entries even after files are removed.

**SOLUTION**: Two approaches:

### 1. Database Reset (Nuclear Option)

```bash
basic-memory reset
```

**What it does**:
- Drops all database tables
- Recreates the schema
- Re-indexes only files that currently exist on disk

**Warning**: Destructive - any bmem-specific metadata stored only in the database will be lost.

### 2. MCP Tool: delete_note (Selective Cleanup)

Using the `delete_note` MCP tool:
- Removes note from database AND file system
- Updates search index and relations
- Parameters: `identifier`, `project`

**Note**: This removes the file itself, so it's not suitable for cleaning up stale database entries for already-deleted files.

## MCP Tools for Database Management

**sync_status**
- Check file synchronization status
- Shows sync progress and background operations across all projects
- Identifies sync issues or conflicts
- No parameters required

**delete_note**
- Removes notes from knowledge base
- Deletes from both database and file system
- Updates search index and relations

**move_note**
- Reorganizes and renames notes
- Maintains database consistency
- Updates search index during operations

## Troubleshooting Sync Issues

When synchronization problems occur:

1. **Check sync status**: `basic-memory status`
2. **Verify file permissions**: Ensure bmem can read/write files
3. **Reset database**: `basic-memory reset` if necessary
4. See [[basic-memory-mcp-tools]] for tool reference and troubleshooting

## Best Practices

1. **Add garbage to `.gitignore` BEFORE indexing**: Once files are indexed, adding them to `.gitignore` won't remove them from the database

2. **Periodic database resets**: If accumulating stale entries, schedule periodic resets as maintenance

3. **Use project-specific data directories**: Keep different projects in separate directories to isolate databases

4. **Monitor entity counts**: Use `basic-memory project info` to watch for unexpected growth

## Current Limitation

**No incremental garbage collection**: Basic Memory lacks a built-in mechanism to:
- Detect files deleted outside of bmem
- Remove stale database entries without full reset
- Incrementally clean up orphaned relations

**Workaround**: Full database reset is currently the only way to remove stale entries from deleted files.

## Configuration File Location

Basic Memory stores configuration in:
- Project-specific: `<project_path>/.bmem/config.yaml` (if exists)
- Global: Platform-dependent user config directory

## References

See [[basic-memory-ai-guide]] for AI assistant guide and [[basic-memory-mcp-tools]] for tool reference.

- **Main Docs**: https://docs.basicmemory.com/
- **User Guide**: https://docs.basicmemory.com/user-guide/
- **Technical Info**: https://docs.basicmemory.com/technical/technical-information/
- **MCP Tools**: https://docs.basicmemory.com/guides/mcp-tools-reference/
- **CLI Reference**: https://docs.basicmemory.com/guides/cli-reference/
- **GitHub**: https://github.com/basicmachines-co/basic-memory
