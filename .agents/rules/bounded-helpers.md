---
trigger: always_on
description: Bound helpers via batching, cache awareness, and culling.
---

## Bounded helpers

- Consider culling stale helpers at idle/task boundaries; spawn fresh ones for new work.
- Batch related file or PKB calls into one turn.
- Yield or finish before prompt cache expiry; never idle across invalidation.
