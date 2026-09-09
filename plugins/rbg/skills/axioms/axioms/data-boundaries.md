---
description: Treat data as private; never emit across trust boundaries without surface-specific authorization.
trigger: off
---

## Data Boundaries

Treat all data as private by default. Never emit private or PKB data (raw task IDs `task-[a-f0-9]{8}`, titles, internal JSON) across trust boundaries (commits, PRs, issue comments, docs) without surface-specific authorization. Use structural handles or masked identifiers.
