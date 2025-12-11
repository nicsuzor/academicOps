# Claude Code Hooks

This directory contains hooks for Claude Code that extend session functionality.

## Session Start: Load Framework Principles

The SessionStart hook automatically injects AXIOMS.md content at the beginning of every session, ensuring framework principles are always available without requiring @ syntax in CLAUDE.md.

### Files

- **sessionstart_load_axioms.py** - SessionStart hook that loads AXIOMS.md

### How It Works

When a Claude Code session starts, the hook:

1. Loads AXIOMS.md from $AOPS/AXIOMS.md
2. Injects content as additional context
3. Includes references to other framework documentation (README.md, $ACA_DATA/projects/aops/STATE.md, VISION.md, ROADMAP.md, LOG.md)
4. Fails fast if AXIOMS.md is missing or empty

### Benefits

- **Framework principles always available** - No need to manually read AXIOMS.md
- **Consistent context** - Every session starts with core principles
- **Fail-fast validation** - Session won't start if AXIOMS.md is corrupt
- **Automatic references** - Agent knows where to find more information

### Error Handling

- If AXIOMS.md missing: Fails with exit code 1 (blocks session start)
- If AXIOMS.md empty: Fails with exit code 1 (blocks session start)
- File must exist at $AOPS/AXIOMS.md

## Auto-Commit State Changes

The auto-commit system automatically commits and pushes changes to `data/` directories to prevent data loss and enable cross-device synchronization.

### Files

- **autocommit_state.py** - PostToolUse hook that commits data/ changes after state-modifying operations

### How It Works

After any tool that modifies state files in `data/`, the hook:

1. Detects state-modifying operations:
   - Task scripts (task_add.py, task_archive.py, etc.)
   - bmem MCP tools (write_note, edit_note, delete_note, etc.)
   - Write/Edit operations targeting data/
2. Checks if uncommitted changes exist in data/
3. Commits all data/ changes with descriptive message
4. Pushes to remote (if configured)
5. Notifies user of success or failure

### Scope

All subdirectories under `data/`:

- `data/tasks/` - Task management files
- `data/projects/` - Project metadata
- `data/sessions/` - Session logs and history
- `data/knowledge/` - Personal knowledge base
- All other data/ subdirectories

### Benefits

- **Zero manual commits** for task and knowledge base changes
- **Cross-device sync** - changes immediately available on all computers
- **No data loss** - state changes committed atomically
- **Non-blocking** - hook failures don't interrupt workflow

### Error Handling

- If git push fails (no remote, network issue): Commits locally and warns user
- If git operations fail: Logs error but continues workflow
- Timeouts: 5s for add/commit, 30s for push

### Testing

Run integration tests:

```bash
uv run pytest bots/tests/integration/test_autocommit_data.py -m integration -v
```

Tests verify:

- Detection of state-modifying operations
- Automatic commit and push
- Graceful handling of git failures
- No-op when no changes exist

## Session Logging

The session logging system automatically records session activity to help track work across sessions.

### Files

- **session_logger.py** - Core logging module with utilities for creating session logs
- **log_session_stop.py** - Stop hook that triggers when a session ends
- **hooks.json** - Hook configuration file

### How It Works

When a Claude Code session ends, the Stop hook:

1. Receives session metadata (session ID, transcript path, etc.)
2. Analyzes the transcript to extract summary information:
   - Message counts (user/assistant)
   - Tools used
   - Files modified
   - Errors encountered
3. Creates a concise summary of session activity
4. Writes a log entry to `./data/sessions/<date>-<shorthash>.jsonl`

### Log Format

Each log file is named `YYYY-MM-DD-<hash>.jsonl` where:

- `YYYY-MM-DD` is the date
- `<hash>` is an 8-character hash of the session ID

Log entries are JSON Lines (JSONL) format with:

```json
{
  "session_id": "unique-session-id",
  "timestamp": "2025-11-09T12:34:56.789Z",
  "summary": "Extended session; used Read, Edit, Bash; modified 3 file(s)",
  "transcript_summary": {
    "user_messages": 10,
    "assistant_messages": 12,
    "tools_used": ["Read", "Edit", "Bash"],
    "files_modified": ["/path/to/file1.py", "/path/to/file2.py"],
    "errors": []
  }
}
```

### Security

- Date validation prevents path traversal attacks
- Hook always returns success to prevent blocking session stop
- File locking prevents race conditions during concurrent writes

### Testing

Run tests with:

```bash
python3 tests/test_session_logging.py
```

## Knowledge Extraction (DEPRECATED)

The previous `extract_session_knowledge.py` script has been deprecated and moved to `scripts/`.

**Use these alternatives instead:**
- `/transcript` - Generate readable markdown from session JSONL
- `/log` - Extract learning patterns via Claude Code (learning-log skill)
- `/bmem` - Capture session information to knowledge base

These alternatives use Claude Code to orchestrate LLM work, following the framework principle that hooks and scripts should not call LLM APIs directly (see `hooks/CLAUDE.md`).
