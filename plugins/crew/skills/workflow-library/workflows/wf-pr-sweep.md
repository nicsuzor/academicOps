---
description: "Crew (needs GitHub access): triage every open pull request in one or more repositories, queue the next step for each, and report a disposition for all of them."
tags:
  - wf-template
  - pr
  - sweep
  - triage
title: PR sweep
type: template
---

## What this step does

Sorts open pull requests by what each needs next. It decides; it does not do the next step itself.

## Obligations

1. **List**: open PRs in the target repositories, leaving out work-in-progress drafts and automated release PRs.
2. **Classify each** against the repository's merge rules: needs review, needs its feedback addressed, ready and awaiting approval, or approved (or covered by a ruling) and ready to land.
3. **Queue**: for each PR that needs agent work, find its open task by PR or branch, or create one. A PR awaiting approval is recorded as such, with its review summary and a recommendation, never handed to the user as something to read.
4. **Report** a disposition for every PR listed.

## Must not

Merge, push fixes or rebase inline; merge a release PR without release approval.

## Output contract

A disposition for every PR, with the task id of each queued next step.

## When to include

Periodic or on-demand triage of open pull requests.
