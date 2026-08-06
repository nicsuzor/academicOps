# Project: Batch Resolution of 5 Codebase Tasks

## Architecture

- Codebase layout: `plugins/` (source plugins), `build/` (build scripts & marketplace SSoT), `dist/` (client-specific plugin artifacts), `lib/` (domain libraries), `tests/` (pytest test suite), `scripts/` (linting/validation tools).
- Interface contracts & workflow conventions: `wf-*` obligation templates, ISO-8601 UTC timestamps, Brisbane timezone (`UTC+10:00`) due-date bucketing, skill status classification.

## Feature Inventory

| # | Feature                             | Description                                                                 | Milestone | Source                  |
| - | ----------------------------------- | --------------------------------------------------------------------------- | --------- | ----------------------- |
| 1 | R1: Email Triage Workflow Component | Create reusable `wf-email-triage` component and update `INDEX.md`           | M1        | ORIGINAL_REQUEST.md §R1 |
| 2 | R2: Fix Dangling Plugin References  | Ensure 0 dangling `/email` slash command references in `plugins/` & `dist/` | M2        | ORIGINAL_REQUEST.md §R2 |
| 3 | R3: Fix list_tasks Timestamps       | Standardize task mutation timestamps to ISO-8601 UTC in `list_tasks`        | M3        | ORIGINAL_REQUEST.md §R3 |
| 4 | R4: Fix Due-date Bucketing          | Update due-date bucketing to use Brisbane local date (UTC+10:00)            | M4        | ORIGINAL_REQUEST.md §R4 |
| 5 | R5: Clarify /daily Skill Status     | Distinguish deliberately removed `/daily` skill from install failure        | M5        | ORIGINAL_REQUEST.md §R5 |

## Milestones

| #       | Name                       | Scope                                                          | Dependencies              | Status |
| ------- | -------------------------- | -------------------------------------------------------------- | ------------------------- | ------ |
| M-E2E   | E2E Testing Suite          | Create test infrastructure & test cases for R1-R5              | None                      | DONE   |
| M1      | R1 Email Triage Component  | Create `wf-email-triage.md` & update `INDEX.md` + test         | None                      | DONE   |
| M2      | R2 Clean Plugin References | Verify 0 dangling `/email` refs + test assertion               | M1                        | DONE   |
| M3      | R3 list_tasks Timestamps   | Fix timestamp recording & list_tasks outputs + test            | None                      | DONE   |
| M4      | R4 Due-date Bucketing      | Implement Brisbane time helper & bucketing logic + test        | None                      | DONE   |
| M5      | R5 /daily Skill Status     | Update status diagnosis for deliberately removed skills + test | None                      | DONE   |
| M-FINAL | Final Integration & Audit  | Pass 100% test suite, linting, verification, forensic audit    | M1, M2, M3, M4, M5, M-E2E | DONE   |

## Interface Contracts

### `plugins/pkb/workflows/wf-email-triage.md`

- Frontmatter: `id: wf-email-triage`, `kind: obligation`, `permalink: wf-email-triage`, `requires: [task-tracking]`
- Routing: listed in `plugins/pkb/workflows/INDEX.md`

### `lib/py/transcripts/domain/time.py` / Time Utilities

- `get_brisbane_today() -> datetime.date`: returns current date in `Australia/Brisbane` (UTC+10:00) timezone.
- Timestamp format: ISO-8601 UTC string (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`).

### Skill Status Schema

- Skill state: `deliberately_removed` when skill entry was intentionally retired (e.g. `/daily`).

## Code Layout

- `plugins/pkb/workflows/` — PKB workflow components and index
- `lib/py/transcripts/domain/` — Time and domain models
- `tests/` — Automated test suite
- `build/` — Build system (`build.py`, `install.py`, `marketplace.toml`)
