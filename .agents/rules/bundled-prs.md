---
trigger: always_on
description: Commit directly to the designated parent task branch and bundle changes into a single consolidated PR when executing under a composite parent task or bundle_pr parent.
---

## Bundled Pull Requests under Composite Parent Tasks

When tasks execute under a parent task marked `bundle_pr: true` or under an active composite task (a parent `type: task` node with child tasks), workers must commit directly to the designated parent branch (`polecat/<parent-id>` or `topic/<slug>`) and must not open detached pull requests against `dev`. All changes, test receipts, and review records bundle into the composite parent task's single consolidated pull request for cohesive user review. If a standalone tracking pull request exists, it is marked superseded and closed upon consolidation.
