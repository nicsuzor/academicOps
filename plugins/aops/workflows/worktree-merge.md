---
title: Worktree Merge
type: template
category: process
description: Merge a verified, merge-ready git branch or worktree into the integration branch and clean up worktree state. Select when integrating completed and tested work. Not for active code development (use `feature-dev`) or PR review (use `pr-review`).
tags: [git, merge, worktree, integration, operations, process]
---

# Process: Worktree Merge

Safe integration and cleanup procedure for verified worktree branches.

## 1. Readiness Verification

- Confirm the target branch is marked `merge_ready` and all CI/local test suites pass cleanly.
- Verify that PR reviews or required sign-offs are satisfied.

## 2. Integration and Branch Merge

- Switch to the main integration branch and pull latest remote changes.
- Squash-merge or rebase the feature branch according to repository policy (`<merge-strategy>`).
- Ensure commit message follows repository conventions and references linked issue IDs.

## 3. Post-Merge Regression Check

- Run full repository test suite on the updated integration branch (`<test-suite>`).
- Confirm build succeeds and no integration regressions occurred.

## 4. Branch Cleanup and Push

- Push updated integration branch to remote.
- Delete feature branch locally and remotely.
- Remove worktree directory and associated transient scratchpads.
