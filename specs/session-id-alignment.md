# Session / Task / PR-Branch ID Alignment

**Task:** task-c36a6b0c
**Status:** Design + minimal additive impl landed
**Depends on:** task-e8647b0c (gap analysis — running in parallel; this design did not block on it)

## Goal

Given a task ID, a single `grep -r task-XXXXXXXX $AOPS_SESSIONS` returns ALL artefacts
(transcripts, hook logs, client logs, session JSON, gate files) for that task.

Today: task ID lives in _directory paths_ (worktree dir, polecat dir) but session shorthash
lives in _filenames_. A flat grep across `$AOPS_SESSIONS` misses things because the directories
that carry the task ID are upstream of the artefacts.

## Current state

### Session-ID generation

- **Claude Code**: full UUID (e.g. `550e8400-e29b-41d4-a716-446655440000`); the framework derives
  an 8-char shorthash via `session_naming.get_session_short_hash()` (first 8 alphanumeric chars).
- **Gemini CLI**: shipped in `GEMINI_SESSION_ID`; otherwise router synthesises
  `gemini-{timestamp}-{short_uuid}` (router.py:258).
- **Polecat workers**: `derive_polecat_session_id(task_id)` extracts the 8-char hex segment
  from the task ID — so polecat session shorthash IS already the task hash. (session_naming.py:73)

### Where task ID is known at session creation

- **Polecat dispatches**: `AOPS_TASK_ID` env var is set by the launcher and picked up by the
  router (router.py:360) and transcript writers (transcript.py:363, 1103, 1285). Already
  flows into session_summary frontmatter. **Not yet used in filenames.**
- **Manual / interactive sessions**: no task ID at SessionStart; task may be claimed mid-session
  via `/pull` or `manage_task`. The router currently writes `task_id` into `state.main_agent.current_task`
  on PostToolUse for PKB tools (router.py:757). Filenames are already locked at SessionStart so
  retroactive renaming would be needed if we wanted late binding.
- **Worktree branch names**: format `claude/<adjective>-<noun>-<8hex>` (this branch:
  `claude/admiring-wing-4a4909`). The 8-hex matches the task-ID shorthash by convention.

### Filename format (v4 unified)

```
{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}
e.g. 20260430-1234-29634cd0-academicops-session-full.md
```

where `shortform = {crew}-{repo}` (or just `{repo}` for non-crew).

## Proposed schema

**Embed task ID into the slug component** when known at session-creation time:

```
{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-task-{taskhash}-{slug}{-variant}.{ext}
e.g. 20260430-1234-29634cd0-academicops-task-c36a6b0c-session-full.md
```

### Why slug-prefix (not new positional segment)

- **Zero parser changes**: `parse_session_filename` uses positional indices for date/time/session_id
  and treats the rest as `shortform-slug`. A `task-XXXXXXXX-` prefix on the slug parses correctly.
- **Zero reader changes**: `find_sessions()`, `_find_existing_transcripts`, and
  `_sweep_legacy_client_logs` all use glob patterns anchored on session_id (`*-{shorthash}-*`).
  The new prefix is invisible to them.
- **Grep-friendly**: `grep -r 'task-c36a6b0c' $AOPS_SESSIONS` matches every artefact whose
  filename was generated with the task_id present.
- **Reversible**: if absent (manual session), filename is unchanged from today.
- **Non-task sessions** (manual, ad hoc): session shorthash remains primary, no task prefix.

### Where the task_id comes from at filename-gen time

1. `task_id` parameter passed explicitly by caller (preferred — used by polecat).
2. Fallback: `AOPS_TASK_ID` env var (set by polecat launcher, set by router for resumed
   sessions where state already binds a task).
3. Otherwise: None → no task prefix → existing behaviour.

## Implementation (this PR)

### Additive changes only

1. `session_naming.generate_session_filename()` — accepts new optional `task_id: str | None`.
   When set, prepends `task-{8char}-` to the slug.
2. `session_naming.generate_base_name()` — same.
3. Internal helper `_format_task_prefix(task_id)` derives the 8-char hex shortform via
   the same logic as `derive_polecat_session_id` (extract hex segment, else SHA-256[:8]).
4. **Callers** pass `task_id` when known:
   - `session_paths.get_hook_log_path()` — reads `AOPS_TASK_ID` from env.
   - `session_paths.get_session_file_path()` — reads `AOPS_TASK_ID` from env.
   - `session_paths.get_gate_file_path()` — reads `AOPS_TASK_ID` from env.
   - `transcript.sync_client_log()` — reads `AOPS_TASK_ID` from env.

Default for `task_id` is `None` everywhere → existing behaviour preserved exactly.

### Tests

`tests/lib/test_session_naming.py` extended:

- task_id=None → unchanged filename.
- task_id set → `task-` segment present in slug position.
- Filename remains parseable by `parse_session_filename`.

## Migration plan

- **Phase 1 (this PR)**: additive — new sessions get task prefix when AOPS_TASK_ID is set.
  Existing files untouched. Backwards compatible glob/parse.
- **Phase 2 (next subtask)**: backfill — sweep `$AOPS_SESSIONS` for sessions whose
  `session_summary.task_id` is set but filename lacks `task-` prefix; rename atomically
  (preserve symlinks, update sweep patterns).
- **Phase 3 (next subtask)**: late-binding — when router observes a task being claimed
  mid-session, write a sidecar `task-{taskhash}.txt` marker into the session dir so grep
  still finds it without renaming live files.

## Acceptance criteria

- [x] `generate_session_filename(task_id="task-c36a6b0c", ...)` produces filename containing
      `task-c36a6b0c` segment.
- [x] `generate_session_filename(task_id=None, ...)` produces existing filename unchanged.
- [x] `parse_session_filename(<new-format-filename>)` returns a valid `ParsedFilename`.
- [x] `grep -l 'task-c36a6b0c' $AOPS_SESSIONS/**/*` returns transcripts + hook logs + client
      logs + session JSON + gate files when polecat dispatch sets AOPS_TASK_ID.
- [x] All existing tests in `tests/lib/test_session_naming.py` continue to pass.
- [x] `find_sessions()` continues to enumerate sessions correctly.

## Next steps (out of scope for this PR)

- **Backfill script** (subtask): rename existing artefacts to embed task_id when
  `session_summary.task_id` is known. Includes a dry-run mode and atomic-rename guarantee.
- **Late-binding marker** (subtask): when router binds a task mid-session via
  `state.main_agent.current_task = task_id`, write `$AOPS_SESSION_STATE_DIR/task-{taskhash}.marker`
  so post-hoc grep still finds the session.
- **Branch-name → task lookup** (subtask): `polecat task <branch-name>` resolves
  `claude/admiring-wing-4a4909` → `task-c36a6b0c` via the registry, closing the loop
  between PR / branch / task.
- **PR-branch alignment audit** (subtask): verify that ALL polecat-created branches
  use the form `<provider>/<adjective>-<noun>-<8hex>` where 8hex matches task-id hex.
  Document/enforce in polecat manager.
