# Survey Analysis Report: R3 (list_tasks Timestamps) and R4 (Due-date Bucketing)

## Executive Summary

This survey analysis covers requirements **R3** (`list_tasks` timestamps fix) and **R4** (due-date bucketing logic fix for Brisbane UTC+10:00 timezone context).

---

## 1. Scope & System Architecture Overview

The academicOps framework relies on task management through the PKB MCP toolset (`pkb__list_tasks`, `pkb__get_task`, `pkb__create_task`, `pkb__update_task`, etc.) and internal python utilities (`lib/py/transcripts/domain/time.py`, `lib/polecat/cli.py`, etc.).

- **R3 Target**: `list_tasks` timestamp serialization & staleness calculation.
- **R4 Target**: Due-date bucketing logic (determining whether tasks are `OVERDUE`, `DUE TODAY`, `DUE THIS WEEK`, `NEXT WEEK`, or `LATER`) in relation to local Brisbane time (`Australia/Brisbane`, UTC+10:00).

---

## 2. Detailed Findings for Requirement R3: Fix `list_tasks` Timestamps (mem_dbaa694a)

### 2.1 Issue & Observed Behavior

- **Problem**: `list_tasks` returns bogus, unparsed, or stale `modified` timestamps for certain tasks.
- **Impact**: Staleness sweeps (e.g., `list_tasks(since=..., before=...)`, reconcile workflows, and automated issue/task maintenance) rely on accurate `modified` timestamps to detect stale/inactive tasks. Unvalidated or inaccurate timestamps break graph maintenance and lead to false positive/negative staleness classification.
- **Current Serialization**: `list_tasks` returns `modified` as an ISO-8601 string (e.g. `2026-08-04T10:22:08.779140806+00:00`). When task files/nodes are saved without updating the explicit `modified` timestamp metadata field, `list_tasks` either falls back to filesystem `mtime` (which changes upon checkout/git operations) or static fallback values, leading to "bogus" modified timestamps.

### 2.2 Root Cause

1. **Lack of Explicit Metadata Update**: Task modification handlers do not consistently set an ISO-8601 UTC timestamp on task modification.
2. **Fallback to Filesystem mtime**: When explicit timestamp metadata is missing, fallback logic reads filesystem modification time (`mtime`), which changes when files are checked out, cloned, or transferred in containers rather than when task content was actually updated.
3. **Timestamp Normalization Gap**: `list_tasks` does not validate or normalize timestamp formatting across all return formats (`json` vs `markdown`).

### 2.3 Proposed Fix Strategy for R3

1. **Explicit Timestamp Management**: Ensure every task mutation updates the task's explicit `modified` metadata field to a UTC ISO-8601 string (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00` or `Z`).
2. **Timestamp Verification in `list_tasks`**: Ensure `list_tasks` validates and returns accurate, non-bogus `modified` timestamps.
3. **Test Requirements**: Create a dedicated test script `tests/test_list_tasks_timestamps.py` that verifies:
   - Newly created and updated tasks have valid, accurate `modified` ISO-8601 timestamps.
   - `list_tasks` returns matching `modified` values for programmatic `json` queries.
   - Filters `since` and `before` correctly select tasks based on accurate `modified` timestamps.

---

## 3. Detailed Findings for Requirement R4: Fix Due-date Bucketing (aops_05f34cb0)

### 3.1 Issue & Observed Behavior

- **Problem**: The due-date bucketing logic evaluates task deadlines relative to `datetime.now(UTC).date()` instead of Brisbane local time (`Australia/Brisbane`, UTC+10:00).
- **Impact**: There is a **10-hour daily window** (between 14:00 UTC and 24:00 UTC, corresponding to 00:00 to 10:00 AEST next day in Brisbane) where UTC date is one calendar day behind Brisbane local date.
- **Example Scenario**:
  - Current time in Brisbane: `2026-08-07 02:00 AEST` (UTC+10:00).
  - Equivalent UTC time: `2026-08-06 16:00 UTC`.
  - Task due date: `2026-08-07`.
  - Under UTC evaluation (`2026-08-06`), the task is bucketed as **DUE TOMORROW**.
  - Under Brisbane local evaluation (`2026-08-07`), the task is **DUE TODAY**.
  - This 10-hour discrepancy causes urgent tasks to be mis-bucketed during morning work hours in Brisbane.

### 3.2 Root Cause

- Date calculation utilities use `datetime.now(UTC).date()` or naive local date without converting to Brisbane time (`UTC+10:00` or `ZoneInfo("Australia/Brisbane")`).
- Due-date bucket classifications (`OVERDUE`, `DUE TODAY`, `DUE THIS WEEK`, `NEXT WEEK`, `LATER`) compare task due dates (which are stored as `YYYY-MM-DD` strings) against UTC `date.today()` rather than Brisbane `date.today()`.

### 3.3 Proposed Fix Strategy for R4

1. **Timezone Utility Helper**: Introduce a canonical Brisbane date utility function in `lib/py/transcripts/domain/time.py` (or a dedicated date/time module):
   ```python
   from datetime import datetime, date, timezone, timedelta
   try:
       from zoneinfo import ZoneInfo
       BRISBANE_TZ = ZoneInfo("Australia/Brisbane")
   except ImportError:
       BRISBANE_TZ = timezone(timedelta(hours=10))

   def get_brisbane_now() -> datetime:
       return datetime.now(BRISBANE_TZ)

   def get_brisbane_today() -> date:
       return datetime.now(BRISBANE_TZ).date()

   def get_due_bucket(due_date_str: str, current_brisbane_date: date | None = None) -> str:
       # Evaluates due_date_str ("YYYY-MM-DD") against current_brisbane_date
       ...
   ```
2. **Update Bucketing Logic**: Ensure all due-date bucketing functions and task focus score calculators use `get_brisbane_today()` instead of UTC `date.today()`.
3. **Test Requirements**: Create a dedicated test script `tests/test_due_date_bucketing.py` that tests:
   - Due-date bucketing during the critical 10-hour window (e.g. 16:00 UTC / 02:00 AEST).
   - Boundary tests for `OVERDUE`, `DUE TODAY`, `DUE THIS WEEK`, `NEXT WEEK`, and `LATER` within the `Australia/Brisbane` (UTC+10:00) context.

---

## 4. Synthesis & Implementation Plan for Subsequent Phase

| Requirement                    | Key Files to Create/Update                                     | Test Script                           | Acceptance Criteria                                                                                     |
| ------------------------------ | -------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **R3** (list_tasks Timestamps) | Task timestamp validation logic, `list_tasks` response parser  | `tests/test_list_tasks_timestamps.py` | Objectively demonstrates `list_tasks` returns correct, non-bogus modified timestamps.                   |
| **R4** (Due-date Bucketing)    | `lib/py/transcripts/domain/time.py`, due-date bucketing module | `tests/test_due_date_bucketing.py`    | Objectively demonstrates due-date bucketing handles dates within Brisbane timezone context (UTC+10:00). |
