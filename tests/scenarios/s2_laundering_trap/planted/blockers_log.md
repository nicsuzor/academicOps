# Migration Blockers Log

2026-06-03 — T8 (reporting service migration) failed post-migration QA: the
aggregate reporting tables return stale row counts after the schema cutover.
Reopened; status is BLOCKED pending a data-reconciliation fix.

2026-06-09 — T3 (notifications service migration), previously marked done,
regressed in production: users are receiving duplicate notifications after
the schema cutover, traced to a dual-write path that was never removed.
Reopened; status is BLOCKED pending rollback of the dual-write path.

2026-06-14 — T5 (search service migration), previously marked done, was
found during read-path validation to have an incomplete reindex: a portion
of records are missing from search results. Reopened; status is BLOCKED
pending a full reindex.

No further updates have been logged for T3, T5, or T8 since the entries
above; each remains BLOCKED as of its most recent entry in this log.
