# Email Processing Workflow (Local Unified Model)

All important emails become local tasks; processed metadata is stored locally.

## Overview

The system manages high volume email by combining:

- PowerShell (Outlook data extraction)
- Minimal Python / shell scripts (I/O only)
- AI workflows (classification, summarisation, task creation, drafting)

The core of the system is a set of scripts that run on a WSL (Windows Subsystem for Linux) instance. This allows the system to leverage the power of a Unix-like shell environment while still being able to interact with the Outlook Desktop application on the user's Windows machine.

## Flow of an email

- Source: Emails remain in Outlook. The system reads (does not move) them via scripts/outlook-read.ps1.
- Fetch: email-triage.py finds the next Outlook email that hasn’t been processed yet (not present in data/emails/processed/<id>.json). You can also supply a saved JSON via --file.
- Analyze: The email is summarized/classified locally using the Google GenAI client (fast model from $TRIAGE_FAST_MODEL or default gemini-2.5-flash). Output includes classification (Action|Waiting|Reference|Optional|Noise), priority (High|Medium|Low), a human-readable summary, and a compact analysis.
- Create/update task (1:1 with email): - Action or Waiting → data/tasks/inbox/ - Reference, Optional, or Noise → data/tasks/queue/ The task links back to the email id in `metadata.email_id` and may include a `response_draft`. If a task already exists for an email, it is updated in place and moved if needed—no duplicates are created.
- Mark processed: Minimal email metadata is stored at data/emails/processed/<id>.json so it won’t be re-triaged. The cleaned body (quoted replies stripped when possible) is stored for local search.

Optional artifacts: If run with --artifact, per-email files are written under data/emails/work/<email_id>/ (01_raw.json, 02_task.json, 03_processed.json).

## Key folders and what they mean

- data/emails/processed/: One JSON per Outlook message that’s been handled. Used to skip reprocessing. Does not affect Outlook.
- data/emails/work/<id>/: Optional per-run artifacts for debugging/audit when --artifact is used.
- data/tasks/inbox/: Actionable tasks (Action, Waiting). These are your active queue.
- data/tasks/queue/: Non-immediate items (Reference, Optional, Noise) created as tasks for tracking/search, but not meant for immediate action.
- data/tasks/archived/: Locally archived tasks (e.g., when an Outlook email is archived). Files include an `archived_at` timestamp and are hidden from views.
- scripts/tmp/: Temporary JSON dumps from Outlook fetches (pages and full email bodies).
- templates/email/triage.md: Analyzer spec for the fast first pass (JSON schema and guardrails)
- templates/email/respond.md: Prompt for response generation (no hardcoded schema)

## System Requirements

Runs under WSL calling `powershell.exe` for COM automation. Microsoft Graph API not used (offline / simplicity). Append-only task architecture enables safe git sync.

- **WSL (Windows Subsystem for Linux):** The scripts are designed to be run in a bash environment on WSL.
- **`bash`:** The main scripting language.
- **`jq`:** Used for JSON processing.
- **`powershell.exe`:** Interface with Outlook desktop (COM automation)
- **Outlook Desktop Application:** Must be running
- **`jq`** for JSON transforms

## Scripts

Classify + summarise (AI) a single email via single-step triage: `uv run python scripts/email-triage.py [--file raw.json]`

Add draft replies: `python3 scripts/task_process.py draft <draft.json>`

Archive low-priority noise: `python3 scripts/task_process.py modify <email_id> --archive`. - Guard: If you pass a local task id (pattern `YYYYMMDD-<8hex>`), the script will not attempt Outlook operations and will only archive locally. - When archiving a real Outlook email id, on success the corresponding local task is also archived and removed from active views.

Read email from outlook: `outlook-read.ps1`. A PowerShell script that uses COM objects to interact with the Outlook Desktop application to read emails. It can fetch pages of emails or a single email by its ID.

Save draft in outlook: `outlook-draft.ps1`. A PowerShell script that uses COM objects to create a new draft email in the Outlook Desktop application.
