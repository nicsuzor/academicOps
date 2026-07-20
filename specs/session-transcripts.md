# Session Transcript Pipeline Specification

This spec outlines the design, architecture, and behavior of the modernized session transcript generation and sync pipeline.

## 1. Intent and Context
The transcript pipeline extracts and distills agent session logs into readable, structured, and audit-ready artifacts. It ensures full observability of both interactive human-driven sessions and background-dispatched automated agent runs, supporting retro loops, compliance checks, and the overwhelm landing dashboard.

## 2. Architecture: Two-Layer Design
To separate parsing churn (caused by upstream log schema drift) from business logic, the pipeline is divided into two distinct layers:

### Layer A: Parse & Normalize (Adapters)
Layer A delegates log parsing and direct formatting to adapters, exposing a single stable target schema defined by `NormalizedSession` (and `NormalizedEvent` / `NormalizedToolCall`).
- **Claude Adapter**: Wraps the live, unpinned `claude-code-log` library, which contains the Pydantic models for the Claude Code JSONL schema and handles markdown/HTML rendering.
- **Agy Adapter**: A lightweight, custom JSONL parser that normalizes the agy logs (which follow a different schema).

### Layer B: academicOps Domain
Layer B consumes typed objects from Layer A only (never raw JSON). It contains all domain logic, metadata enrichment, and synchronization processes:
- **Slug Generation**: Deterministic slug derivation from `session_id`.
- **Classification**: Semantic human-vs-automated `has_user_context` classification (inspecting event content, not relying on brittle surface/client whitelists).
- **Timestamps**: Event-derived `started_at`, `last_modified`, and `ended_at` times (never falling back to file mtime).
- **Correlation**: Inferring related PRs, tasks, and projects from logs.
- **Insights**: Extracting accomplishments, decisions, tool counts, and errors.
- **Sync**: Direct git add/commit/push of transcripts and summaries to the sessions repo.

## 3. Source Scope
- **Supported**: Claude Code CLI sessions, agy brain sessions.
- **Excluded**: Gemini sessions (gemini-cli/gemini-crew) are excluded due to high heartbeat file volume causing lock contention.

## 4. Maintenance and Resilience Strategy
- **Unpinned Live Library**: The pipeline imports `claude-code-log` dynamically without locking its version, allowing it to stay updated with upstream changes.
- **Fixture Corpus and Snapshot Tests**: Real, anonymized session fixtures are committed to the repository. The test suite runs parser and renderer assertions against these fixtures to catch upstream schema drift immediately as local CI failures rather than silent cron crashes.

## 5. Output Formats
For every non-empty session, Layer B outputs three artifacts to `$AOPS_SESSIONS/transcripts/YYYY-MM/`:
1. **Markdown (`session-*.md`)**: Human-readable transcript prefixed with a YAML front-matter block containing session metadata, timestamps, and inferred correlations.
2. **HTML (`session-*.html`)**: Standalone, styled document matching academicOps responsive and rich design aesthetics.
3. **JSON (`session-*.json`)**: Metadata sidecar serialized for dashboard ingestion.
