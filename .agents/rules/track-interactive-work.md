---
trigger: always_on
description: Interactive user prompts must be tracked in claimed tasks, with topic threading and single-PR review bundling.
---

## Track interactive work

Interactive user prompts must be tracked systematically in tasks on the task graph to maintain visibility and prevent dropped requests.

- **Interactive user prompts only**: Task claiming and tracking requirements apply strictly to interactive prompts directly from the user, excluding prompts from other agents or automated harness injections.
- **Task claiming by topic**: For each new topic in a user prompt, check open tasks before acting. For non-casual topics, claim an existing open task or create and claim an aggregation task via `/q` (searching both open and closed tasks to resume or reopen where appropriate). Casual requests are tracked within the general session task created at session start.
- **Topic threading**: Where the communication channel supports threads or hashtags, group all communications for each topic into a distinct thread or hashtag to protect user working memory.
- **Cohesive review bundling**: When modifications span related topics under a task, bundle all repository modifications and review/approval steps into a single pull request for cohesive user review.
