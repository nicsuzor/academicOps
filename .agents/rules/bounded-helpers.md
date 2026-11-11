---
trigger: always_on
description: Subagent helpers batch operations into single turns, avoid idling across prompt cache expiry, and are evaluated at idle/task boundaries for culling or replacement.
---

## Bounded helpers

Subagent helpers are kept bounded through timely lifecycle management, batched operations, and active prompt cache awareness:

- **Lifecycle and culling encouragement:** On an agent-idle hook or at task boundaries, agents are encouraged (not required) to consider whether a subagent helper has run too long and decide whether to cull it. When assigning unrelated work, prefer dispatching a fresh subagent rather than reusing an existing long-running helper.
- **Batched operations:** Multiple related read or write operations across files or knowledge base entities must be batched into single tool calls (e.g. batch document fetches or multi-file inspections) instead of sequential single-item round-trips.
- **Active cache management:** Cache entries expire after 5 minutes of inactivity. Helpers waiting on asynchronous background jobs or long-running tasks must complete or yield before the 5-minute cache TTL expires; idling across cache invalidation boundaries is strictly prohibited.
