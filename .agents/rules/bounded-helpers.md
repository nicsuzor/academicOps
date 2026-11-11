---
trigger: always_on
description: Subagent helpers are strictly bounded to 30 calls, batch operations into single turns, and never idle across prompt cache expiry.
---

## Bounded helpers

Subagent helpers are strictly bounded: a hard cap of 30 model calls per helper (operational range 25–35), related operations batched into single turns, and no helper left idle on background work past the prompt cache lifetime.

- **Call cap per helper:** Subagent worker turns are budgeted to complete within ≤ 30 tool calls. If a subagent task cannot complete within this ceiling, the worker hands back on the record as `partial` with current progress and missing evidence rather than continuing unconstrained execution.
- **Batched operations:** Multiple related read or write operations across files or knowledge base entities must be batched into single tool calls (e.g. batch document fetches or multi-file inspections) instead of sequential single-item round-trips.
- **Active cache management:** Cache entries expire after 5 minutes of inactivity. Helpers waiting on asynchronous background jobs or long-running tasks must complete or yield before the 5-minute cache TTL expires; idling across cache invalidation boundaries is strictly prohibited.
