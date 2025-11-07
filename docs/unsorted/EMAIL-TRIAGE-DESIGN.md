# Email triage design notes

- `email-triage.py`: fast, one-shot triage. No interactive flows. Uses a fast model (env: TRIAGE_FAST_MODEL | FAST_MODEL | TRIAGE_MODEL, default gemini-2.5-flash). Cleans and stores message body (quoted replies stripped) for local search, creates or updates a single task (1:1 with the email), and best-effort archives clear Noise.

- Drafting remains an interactive, supervised step (see `.gemini/commands/email/do.toml`) which calls `scripts/task_process.py` (or the wrapper `scripts/task_process.py`) to save drafts. We intentionally do not move the interactive drafting loop into Python; Python scripts must be deterministic single-run tools without conversational control.

### Interaction with Outlook

PowerShell scripts used:

- Draft creation uses `scripts/task_process.py` -> `scripts/outlook-draft.ps1`.
- Archiving uses `scripts/task_process.py modify` -> `scripts/outlook-message.ps1`.

On successful Outlook archive, the corresponding local task is also archived (moved to `data/tasks/archived/` and marked with `archived_at`). Archived tasks never appear in views.

### Environment

- First pass triage: `TRIAGE_FAST_MODEL` (default: gemini-2.5-flash)
- Optional high-quality model for deeper work (default: ?, currently unused). The interactive drafting task can read this env var and switch models.
- Auto-archive toggle: `TRIAGE_AUTO_ARCHIVE` (default on unless set to false/0).
- Body cleaning uses `email-reply-parser` when available; otherwise raw body is stored.

### Deduplication and Single Source of Truth

- Emails are tasks. We enforce a one-task-per-email invariant keyed by `metadata.email_id`.
- If a task already exists for an email, triage updates it in place (priority, classification, description) and moves it between `inbox/` and `queue/` if required; no new task file is created.
- Processed metadata (`data/emails/processed/<id>.json`) remains a lightweight store for email-specific fields and body text for local search; it is not considered a duplicate task.
