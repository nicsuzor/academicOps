---
trigger: always_on
description: Gather related changes onto a shared feature branch via three-lens diff-checked constituent branches, close superseded donor PRs immediately, run a compliance description check pre-approval, and run the full combined-diff review after approval and rebase.
---

## Consolidated Feature-Branch Pull Requests

Related changes -- tasks executing under a composite parent task (`type: task` with children or `bundle_pr: true`), tasks modifying overlapping surfaces, or open pull requests grouped during a sweep -- gather on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) and reach the user as a single consolidated pull request into `dev`. Each self-contained constituent branch (`polecat/<task-id>`) undergoes the three-lens diff review (strategic fit, compliance, quality) and, on `PASS`, is merged directly into the shared feature branch by the agent without waiting for user approval. Any superseded standalone donor pull request is closed immediately in the same step with a comment linking to the consolidated pull request. Pre-approval review on the consolidated pull request is a compliance description-only check (`wf-rbg`, "is this stupid?") without pre-approval rebase against `dev`; after user approval, the agent rebases onto `dev` and runs the full three-lens diff review over the combined diff before merging.
