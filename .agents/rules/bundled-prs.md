---
trigger: always_on
description: Commit directly to the designated epic branch and bundle changes into a single consolidated PR when executing under an epic or bundle_pr parent.
---

## Bundled Pull Requests under Epics

When tasks execute under a parent task marked `bundle_pr: true` or under an active epic (`type: epic`), workers must commit directly to the designated epic branch (`polecat/<epic-id>` or `topic/<slug>`) and must not open detached pull requests against `dev`. All changes, test receipts, and review records bundle into the epic's single consolidated pull request for cohesive user review. If a standalone tracking pull request exists, it is marked superseded and closed upon consolidation.
