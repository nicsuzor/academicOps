# Knowledge Base (PKB)

Before you answer from memory or assume, look it up. If this request touches anything that could already be written down — past decisions, project or task state, people, conventions, file locations, or your own earlier notes — consult the PKB first and let what you find ground your answer. You judge what's relevant; the PKB is the system of record, your recollection is not.

**Reach for a structured lookup before a semantic one.** When the request names exact-match attributes — a project, tag, status, type, or "the latest/last" by recency — one structured filter answers it in a single call: `list_tasks(project=…, tags=[…], status=…)`, `search_by_tag(...)`, `list_documents(...)`. Keep semantic `search` / `task_search` for fuzzy discovery, when you cannot name what you want. A structured request resolved by a semantic fan-out — six calls for a one-call answer — is the failure mode to avoid.

**Check for already-extracted corpora before re-deriving them.** Structured data is often already produced and queryable rather than something you must rebuild. Session summaries under `$AOPS_SESSIONS/summaries/` carry a `timeline_events` array — user prompts, tool calls, and events per session (schema: `specs/session-insights-metrics-schema.md`). When you need data that looks like it has already been extracted, look for the existing corpus first.
