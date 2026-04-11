# Session Naming Convention & Directory Layout

**Status**: Draft (pending review)
**Task**: task-979e5ec2
**Epic**: task-bbd1b7e3 (Unified session visibility)

## Overview

This spec defines the canonical naming convention for all session artifacts stored in `$AOPS_SESSIONS`. It replaces the current inconsistent naming across `transcript.py`, `session_paths.py`, and hook log generation.

## Goals

1. Every session (polecat, crew, manual; Claude or Gemini; any machine) produces a consistent set of artifacts in `$AOPS_SESSIONS`
2. Filenames encode enough context to identify the session at a glance without opening the file
3. All artifacts for a given session share the same base name, differing only by suffix
4. Session IDs are consistent and, for polecat sessions, match the task ID

## Filename Format

```
{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}
```

### Components

| Component | Format | Example | Source |
|-----------|--------|---------|--------|
| `YYYYMMDD` | Date | `20260411` | First entry timestamp, fallback to file mtime |
| `HHMM` | 24h hours + minutes | `1430` | First entry timestamp, fallback to file mtime |
| `session_id` | 8-char alphanumeric | `a1b2c3d4` | See [Session ID Derivation](#session-id-derivation) |
| `shortform` | See [Shortform](#shortform-format) | `gloria-academicops-nuc-claude` | Composed from session metadata |
| `slug` | kebab-case, max 5 words | `fix-hook-log-paths` | Auto-generated from first user prompt |
| `variant` | Optional suffix | `-full`, `-abridged` | Artifact-specific (transcripts only) |
| `ext` | File extension | `.md`, `.json`, `.jsonl` | Determined by artifact type |

### Component Ordering Rationale

1. **Date-time first** — enables chronological sorting with `ls` and glob patterns like `20260411-*`
2. **Session ID second** — the stable cross-file join key; easy to grep for all files from one session
3. **Shortform third** — human context (who/where/what) for quick visual scanning
4. **Slug fourth** — content summary, most variable and least structural
5. **Variant last** — only differentiates sub-types of the same artifact (full vs abridged)

## Shortform Format

The shortform encodes session provenance in a compact, readable string:

```
{crew}-{repo}-{machine}-{provider}
```

### Rules

| Field | Source | Omission Rule |
|-------|--------|---------------|
| `crew` | `$POLECAT_CREW_NAME` | Omitted for manual sessions and polecat-run sessions (no crew) |
| `repo` | Repository name from `$CLAUDE_PROJECT_DIR` or cwd | Always present. Derived from the basename of the project directory, lowercased |
| `machine` | `$AOPS_MACHINE` env var, fallback to `hostname -s` | Always present. Must be set explicitly — container hostname `aops-crew` is not useful |
| `provider` | `claude` or `gemini` | Always present. Detected via `_is_gemini_session()` or `$POLECAT_SESSION_TYPE` + `-g` flag |

### Examples by Session Type

| Session Type | Shortform | Full Filename Example |
|---|---|---|
| Manual Claude | `academicops-nuc-claude` | `20260411-1430-a1b2c3d4-academicops-nuc-claude-fix-hook-paths-full.md` |
| Manual Gemini | `academicops-nuc-gemini` | `20260411-1430-b2c3d4e5-academicops-nuc-gemini-review-pr-full.md` |
| Crew Claude | `gloria-academicops-nuc-claude` | `20260411-1430-c3d4e5f6-gloria-academicops-nuc-claude-refactor-tests-full.md` |
| Crew Gemini | `gloria-academicops-nuc-gemini` | `20260411-1430-d4e5f6a7-gloria-academicops-nuc-gemini-update-docs-full.md` |
| Polecat Claude | `academicops-nuc-claude` | `20260411-1430-e5f6a7b8-academicops-nuc-claude-fix-lint-full.md` |
| Polecat Gemini | `academicops-nuc-gemini` | `20260411-1430-f6a7b8c9-academicops-nuc-gemini-add-tests-full.md` |

Note: Polecat-run sessions have no crew name (they run as isolated workers, not in a named worktree).

### Machine Name

**New env var required**: `AOPS_MACHINE`

- Must be set in the host environment (e.g., in `.bashrc` or systemd unit)
- Forwarded to containers via the existing `AOPS_*` prefix forwarding in `polecat/cli.py`
- Short, human-readable name (e.g., `nuc`, `mbp`, `dev01`) — NOT the full hostname
- Fallback: `hostname -s` (but this returns `aops-crew` inside containers, which is useless — `AOPS_MACHINE` must be set)

## Session ID Derivation

The `session_id` is an 8-character identifier that is consistent across all artifacts for a given session.

### For Claude sessions

Use the first 8 characters of `$CLAUDE_SESSION_ID` (UUID format, so first 8 hex chars). This matches the current `get_session_short_hash()` behavior.

### For Gemini sessions

Use the first 8 characters of `$GEMINI_SESSION_ID`. For crew sessions this is `gemini-{crew_name}` — hash it to 8 chars. For polecat sessions this is `gemini-{task_id}` — hash it to 8 chars.

### For Polecat sessions (task ID matching)

The session ID must be derivable from the task ID so they can be correlated:

```python
def derive_polecat_session_id(task_id: str) -> str:
    """Derive session hash from task ID for polecat sessions.

    For task IDs like 'aops-a1b2c3d4-fix-something', extracts the
    8-char hash portion. For other formats, hashes the full ID.
    """
    # Task IDs have format: prefix-8charhash-slug
    parts = task_id.split("-")
    for part in parts:
        if len(part) == 8 and all(c in '0123456789abcdef' for c in part):
            return part
    # Fallback: hash the whole task ID
    return hashlib.sha256(task_id.encode()).hexdigest()[:8]
```

This ensures `task_id = "aops-a1b2c3d4-fix-something"` produces `session_id = "a1b2c3d4"`, matching across all artifact files.

## Directory Layout

```
$AOPS_SESSIONS/
  transcripts/           # Markdown transcript files (-full.md, -abridged.md)
  summaries/             # Session insights JSON files (.json)
  hooks/                 # Per-session hook log files (-hooks.jsonl)
  client-logs/           # Raw client session logs (-client.jsonl)
```

### Rationale: Flat by Type (not Grouped by Session)

Files are organised by artifact type, not grouped into per-session directories. Reasons:

1. **Glob patterns work**: `transcripts/20260411-*` finds all transcripts for a date
2. **Git-friendly**: adding a transcript doesn't create a new directory (smaller diffs)
3. **Existing convention**: `transcripts/` and `summaries/` already exist and work this way
4. **Cross-session queries**: "show me all hook logs from today" is a common query
5. **Session correlation**: use the `session_id` component to find all files for one session across directories

### Subdirectory Details

| Directory | Contents | Filename Pattern |
|-----------|----------|------------------|
| `transcripts/` | Human-readable markdown transcripts | `{base}-full.md`, `{base}-abridged.md` |
| `summaries/` | Session insights, metrics, reflection | `{base}.json` |
| `hooks/` | Hook execution log (one entry per hook invocation) | `{base}-hooks.jsonl` |
| `client-logs/` | Raw session log from Claude/Gemini CLI | `{base}-client.jsonl` |

Where `{base}` = `{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}`

## File Taxonomy

| Suffix | Extension | Content | Producer |
|--------|-----------|---------|----------|
| `-full` | `.md` | Full session transcript with all tool calls | `transcript.py` |
| `-abridged` | `.md` | Abbreviated transcript (prompts + key outputs) | `transcript.py` |
| (none) | `.json` | Session insights: summary, metrics, reflection | `insights_generator.py` |
| `-hooks` | `.jsonl` | Hook activity log (one JSON object per line) | `session_paths.py` / router |
| `-client` | `.jsonl` | Raw client session log (Claude JSONL or Gemini JSON converted) | Sync pipeline (new) |

## Migration & Backward Compatibility

### Reading (Discovery)

All file discovery functions (`find_sessions()`, `_find_existing_transcripts()`, `find_existing_insights()`) must support BOTH old and new naming patterns during the transition period.

Old patterns to support:
- `YYYYMMDD-HH-project-sessionid-slug-full.md` (transcripts, no minutes, no shortform)
- `YYYYMMDD-HH-project-sessionid-slug.json` (insights, no minutes, no shortform)
- `YYYYMMDD-shorthash-hooks.jsonl` (hook logs, no minutes, no context)

### Writing (Generation)

All new files are written with the new naming convention immediately. No old-format files are generated after the migration.

### Renaming Existing Files

Existing files are NOT renamed. The old files remain discoverable via backward-compatible globs. Over time, old files will be naturally superseded as sessions age out.

## New Environment Variables Required

| Variable | Purpose | Where to Set |
|----------|---------|-------------|
| `AOPS_MACHINE` | Short machine name for filename shortform | Host `.bashrc` or systemd; forwarded to containers via `AOPS_*` prefix |

## Implementation Notes

### Single Source of Truth

All naming logic lives in `aops-core/lib/session_naming.py`. No other module generates session filenames. All consumers (transcript.py, session_paths.py, insights_generator.py, sync pipeline) call into this module.

### Parsing

`session_naming.parse_session_filename(filename)` must be able to extract all components from a filename. The format is designed to be unambiguously parseable:

- Date-time: first 13 chars (`YYYYMMDD-HHMM`)
- Session ID: next 8 chars after separator
- Shortform: variable-length, but each component is separated by `-` and the set of valid provider values (`claude`, `gemini`) terminates the shortform
- Slug: everything between provider and variant/extension
- Variant: `-full`, `-abridged`, `-hooks`, `-client` (known set)

### Slug Generation

Reuses existing `SessionProcessor.generate_session_slug()` from `transcript_parser.py`. Max 5 words, kebab-case, stop words removed.

### Timestamp Precision

Adding minutes (`HHMM` instead of `HH`) resolves the current collision risk when multiple sessions start in the same hour. The timestamp is taken from the first entry in the session log, with fallback to file modification time.
