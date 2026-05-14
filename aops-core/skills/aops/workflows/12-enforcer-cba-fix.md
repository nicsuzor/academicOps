---
title: Enforcer CBA Fix Workflow
type: workflow
category: instruction
permalink: workflow-enforcer-cba-fix
description: Coordinator workflow for delegating mechanical PR reviews to polecat workers
---

# Workflow 12: Enforcer CBA Fix

**When**: The `claude[bot]` enforcer issues `CHANGES_REQUESTED` on a PR with a parseable feedback shape. (e.g., PR #1006 CBA-1, PR #1016 CBA-4+5, PR #1017)

## Problem Statement

The enforcer catches mechanical or formatting violations on PRs (e.g., CBA rules, A8 compliance) and requests changes. Resolving these is low-judgment, mechanical work: reading the review, identifying the specific envelope required to fix it, executing the change, and dismissing the review. This should drop below the user's surface; the coordinator handles it instead.

## 1. Trigger (The Signal)

The workflow is triggered when:

- A GitHub PR receives a `CHANGES_REQUESTED` review from `claude[bot]` (the enforcer).
- The review contains a parseable feedback shape indicating specific, mechanical violations.

## 2. Envelope-Composition Heuristics (Drafting the Task)

The coordinator reads the review and creates a `fix-task` in the PKB. The task must provide a clear execution envelope for the polecat worker:

- **Defensible Defaults:**
  - **Priority:** Inherit the parent task's priority or default to `P2` (unblocking active work).
  - **Effort/Token-cost:** Estimate low cost (`<1h`), as the work is mechanical and bounded.
- **Scope Envelope:**
  - **In-scope:** Addressing _only_ the specific violations listed in the enforcer review.
  - **Out of scope:** Any unrelated refactoring, logic changes, or edits to files not directly cited in the review.
- **Success Criteria:**
  - Changes pushed that satisfy the enforcer's review.
  - Enforcer review is explicitly dismissed.

## 3. Dispatch Shape

With the task created, the coordinator dispatches the worker:

```bash
polecat run -t <this-task-id> -p <project> -g --model gemini-3.1-pro-preview
```

_(Ensure the correct `-p <project>` is passed, inheriting from the original PR's context)._

## 4. Dismissal Protocol

The polecat worker's execution steps must include the dismissal protocol. The worker will:

1. **Act:** Execute the necessary file edits and push the changes.
2. **Update PR:** Edit the PR body to reflect the fixes if required.
3. **Dismiss Review:** Explicitly dismiss the `claude[bot]` review via the GitHub CLI.
   ```bash
   gh pr review <pr_url> --dismiss -m "Fixed mechanical violations per enforcer review"
   ```
4. **Release:** Call `mcp_pkb_release_task` with `status="merge_ready"` and exit immediately. _Do not wait for CI._
