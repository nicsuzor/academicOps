# Framework Capabilities & Artifacts

This document catalogs the operational capabilities, artifacts, and artifact conventions managed by the academicOps framework.

## Transcripts

The framework records every LLM prompt as an individual transcript file, rather than one monolithic transcript per session.

**Naming Convention:**

```text
{date}-{time}-{session_id}-{shortform}-{prompt_slug}-{variant}.md
```

- `date`: `YYYYMMDD` format.
- `time`: `HHMM` format.
- `session_id`: 8-character hash identifying the overarching session.
- `shortform`: Identifying context constructed from available identifiers (e.g., crew, repo, machine, and provider like `claude` or `gemini`), joined by hyphens.
- `prompt_slug`: A short slug derived from the specific prompt content, making each file unique per interaction within the session.
- `variant`: Usually `full` or `abridged`.

### Finding the Current Transcript

Because transcripts are per-prompt, asking to find "the current transcript" requires identifying the most recently modified file for a given `session_id`.

**Recipe to find the most recent full transcript for a session:**

```bash
ls -t $AOPS_SESSIONS/transcripts/*-${session_id}-*-full.md | head -n 1
```

_(Substitute `${session_id}` with your actual 8-character session ID.)_
