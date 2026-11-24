---
trigger: always_on
description: Workers never pause or release review; hand back on record.
---

## Headless workers

- Never pause, ask approval, or escalate to the user; hand back on record.
- Workers deliver in-session and queue follow-ups only if cross-repo, delayed, or external, using composite parent tasks (`type: task`, never `type: epic`) with `needs` edges and zero leaf `serves` edges.
- Release failures as `failed` and approval boundaries as `partial` (never `review`).
