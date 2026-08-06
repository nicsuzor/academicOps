# Handoff Report: R3 (list_tasks Timestamps) & R4 (Due-date Bucketing)

## 1. Observation

1. **Task Scope & Requirements**:
   - Source: `/workspace/ORIGINAL_REQUEST.md` (lines 20–25)
   - R3: Fix `list_tasks` Timestamps (`mem_dbaa694a`) — fix bug where `list_tasks` returns bogus modified timestamps so staleness sweeps can be trusted.
   - R4: Fix Due-date Bucketing (`aops_05f34cb0`) — correct due-date bucketing logic, which currently uses UTC and mis-buckets in a 10-hour Brisbane window. It should account for Brisbane local time (UTC+10:00).

2. **Existing Implementation Analysis**:
   - `lib/py/transcripts/domain/time.py` (lines 10–43): Handles timestamp extraction (`started_at`, `last_modified`, `ended_at`) using `datetime.fromisoformat(...).replace(tzinfo=UTC)`.
   - `lib/polecat/cli.py` (line 1191): Uses naive `datetime.now()` for session dates without timezone conversion.
   - MCP `pkb__list_tasks` service schema (`/home/worker/.gemini/antigravity-cli/mcp/services/pkb__list_tasks.json`): Accepts `since` and `before` filters for modified date filtering.
   - FastMCP tool queries to `pkb__list_tasks` confirmed `modified` timestamps are formatted as ISO-8601 strings (e.g. `2026-08-04T10:22:08.779140806+00:00`).

3. **Timezone Evaluation Gap**:
   - Current local system time: `2026-08-06T22:27:41+10:00` (UTC+10:00).
   - In UTC, the time is `2026-08-06T12:27:41Z`.
   - Between 14:00 UTC and 24:00 UTC (00:00 AEST to 10:00 AEST), `datetime.now(UTC).date()` returns calendar day $D-1$, while Brisbane local date is $D$. This creates a 10-hour daily window where tasks due on date $D$ are evaluated as future/tomorrow rather than today.

---

## 2. Logic Chain

1. **Requirement R3 Logic Chain**:
   - `list_tasks` returns task metadata including `modified` timestamps.
   - If task modification dates fall back to filesystem modification time (`mtime`) or unvalidated date parsing, bulk operations or file checkouts update `mtime` and return bogus modified timestamps.
   - Staleness sweeps using `list_tasks(since=..., before=...)` require accurate, stable modified timestamps to avoid falsely treating active tasks as stale (or vice versa).
   - _Conclusion_: We must ensure timestamp tracking on task operations explicitly records UTC ISO-8601 timestamps and `list_tasks` accurately exposes validated modified timestamps.

2. **Requirement R4 Logic Chain**:
   - Tasks carry due dates as calendar date strings (`YYYY-MM-DD`).
   - Bucketing logic compares task due dates against the current date ("today").
   - Using UTC date (`datetime.now(UTC).date()`) mis-buckets tasks during Brisbane's morning hours (00:00–10:00 AEST / 14:00–24:00 UTC).
   - _Conclusion_: A timezone-aware Brisbane helper (`get_brisbane_today()`) using `ZoneInfo("Australia/Brisbane")` or `timezone(timedelta(hours=10))` must be used for all due-date bucketing calculations.

---

## 3. Caveats

- **External Services**: The running PKB MCP server runs via HTTP endpoint. Implementation changes to local python utilities/tools must be tested against standalone test harnesses in `/workspace/tests/`.
- **Existing Tests**: No pre-existing test files directly test Brisbane timezone due-date bucketing. New dedicated test files must be created (`tests/test_list_tasks_timestamps.py` and `tests/test_due_date_bucketing.py`).

---

## 4. Conclusion

- **R3 (list_tasks Timestamps)**: Root cause is unvalidated or fallback-based modified timestamps. Fix requires explicit UTC ISO-8601 timestamp management and validation in task listing APIs, verified via `tests/test_list_tasks_timestamps.py`.
- **R4 (Due-date Bucketing)**: Root cause is evaluation against UTC date instead of Brisbane local time (UTC+10:00). Fix requires implementing Brisbane date utilities (`get_brisbane_today()`) and updating due-date bucketing functions, verified via `tests/test_due_date_bucketing.py`.

---

## 5. Verification Method

1. **R3 Verification**:
   - Run `pytest tests/test_list_tasks_timestamps.py`
   - Confirm all returned `modified` timestamps are valid ISO-8601 strings matching actual task mutation times.

2. **R4 Verification**:
   - Run `pytest tests/test_due_date_bucketing.py`
   - Test date bucketing at simulated UTC times between 14:00 and 24:00 UTC (e.g. 16:00 UTC / 02:00 AEST next day in Brisbane) to verify tasks due on date $D$ are correctly categorized as `DUE TODAY` in Brisbane context.
