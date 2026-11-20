---
trigger: always_on
description: Workers never pause or release review; hand back on record.
---

## Headless workers

- Never pause, ask approval, or escalate to the user; hand back on record.
- Leaf workers edit claimed task state only; coordinators supervise in-session and queue follow-ups only if cross-repo, delayed, or external.
- Release failures as `failed` and approval gates as `partial` (never `review`).
