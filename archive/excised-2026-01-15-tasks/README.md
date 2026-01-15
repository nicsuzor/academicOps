# Excised Task System (2026-01-15)

**Decision**: Task system v1/v2 deprecated in favor of `bd` (beads) as sole work tracking system.

## What Was Removed

The structured task system that stored markdown files in `$ACA_DATA/tasks/` has been fully excised:

### Skills
- `aops-core/skills/tasks/` - MCP server, task operations, workflows

### Library Functions
- `aops-core/lib/task_storage.py` - Task file I/O
- `aops-core/lib/task_graph.py` - Task hierarchy/dependencies
- `aops-core/lib/task_index.py` - Task indexing
- `aops-core/lib/task_model.py` - Task data models

### Specifications
- `aops-core/specs/tasks-v2.md` - Task system v2 design spec

### Scripts
- `aops-core/scripts/task.py` - Task CLI

### Tests
- `tests/lib/test_task_*.py` - Unit tests for task libraries
- `tests/integration/test_task_viz.py` - Integration tests
- `tests/run_integration_tests.py` - Task server test runner

## Replacement

All work tracking now uses `bd` (beads):
- `bd create "description"` - Create issue
- `bd list` - View issues
- `bd update <id> --status=<status>` - Update status
- `bd close <id>` - Close issue
- `bd sync` - Sync state

See `workflows/bd-workflow.md` for complete documentation.

## Recovery

If needed, this code remains available:
1. In this archive directory
2. In git history (preferred per P#24)
