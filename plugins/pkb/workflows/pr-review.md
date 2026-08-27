---
id: pr-review
kind: process
category: operations
description: Triage open PRs, invoke reviewer agents, synthesize a per-PR verdict table — human makes the final merge call
requires: [batch]
pairs-with: [worktree-merge]
conflicts: []
version: 1.0.0
permalink: workflows-process-pr-review
---

# Process: PR Review

The supervisor triages, invokes reviewer agents, and presents findings. The
human provides final approval — this template never merges on its own.

## Core Rule

**Always invoke reviewer agents.** The supervisor's own diff read is
supplementary, never a substitute for structured reviewer analysis.

## Steps

1. **Triage** — list open PRs with CI/mergeable/review metadata. Classify:
   CI failing → hold, do not review code yet; merge conflicts → hold, author
   resolves first; CI passing + mergeable → reviewable, proceed.
2. **Dispatch reviews** — compose [[batch]] to invoke reviewer agents on all
   reviewable PRs in parallel.
3. **Collect findings** — wait for reviews; comments land on the PR itself.
4. **Synthesize** — a per-PR verdict table: description, CI, conflicts,
   reviewer verdicts, recommendation.
5. **Act on verdicts** — clean PRs get approved; PRs with issues get specific
   fix comments, tagged to the responsible agent. Once ready to merge, hand
   off to [[worktree-merge]]. A merge to a protected branch is Nic's to make,
   and **his merge is the sign-off** — do not emit a human sign-off task node
   for it (Nic, 2026-08-26).
