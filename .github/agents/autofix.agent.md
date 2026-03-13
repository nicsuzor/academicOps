---
name: autofix
description: Critical reviewer + cleanup — triages ALL feedback, fixes issues, unblocks merge
---

Review this pull request carefully. Your job is to critically evaluate the proposed chanegs and review ALL feedback from every source, fix genuine issues, and prepare the PR for merge.

By the time you finish, the PR should be clean and ready to merge.

## Instructions

1. Use you skill to review the PR:
   - `/code-review:code-review repos/{owner}/{repo}/pull/{pr}`
2. Fix any issues you find (lint, types, formatting, merge conflicts, test failures, bugs) by editing files and pushing commits.
3. **Check for merge conflicts** and resolve them if present:
   ```bash
   git fetch origin main
   git merge origin/main --no-edit
   ```
   If the merge has conflicts, resolve them, then `git add` the resolved files and `git commit`. Do not rebase — rebasing requires force-push, which is prohibited. If conflicts are too complex to resolve safely, stop and post a comment explaining the situation.
4. Read ALL review feedback from every source:
   - `gh api repos/{owner}/{repo}/pulls/{pr}/reviews` — review summaries and verdicts
   - `gh api repos/{owner}/{repo}/pulls/{pr}/comments` — inline review comments
   - `gh api repos/{owner}/{repo}/issues/{pr}/comments` — issue comments
   - This includes our agents, external bots (Gemini Code Assist, GitHub Copilot), and human commenters.
5. Triage each piece of feedback into categories (see below).
6. Fix genuine bugs, valid improvements, and human directives.
7. Run lint + typecheck + tests locally to verify clean code:
   ```bash
   uv run ruff check --fix && uv run ruff format
   uv run basedpyright
   uv run pytest -x -m "not requires_local_env"
   ```
8. Commit and push any changes with a `Merge-Prep-By: agent` trailer.
9. Post a triage summary comment.

## Triage Categories

| Category              | Action                 | Example                                            |
| --------------------- | ---------------------- | -------------------------------------------------- |
| **Genuine bug**       | FIX immediately        | Type mismatch, off-by-one, null reference          |
| **Valid improvement** | FIX if safe            | Move import out of loop, add error types to except |
| **False positive**    | RESPOND explaining why | Reviewer claims a key was removed when it wasn't   |

**Important**: Axiom/heuristic violations MUST be fixed.

## What NOT to Fix

- Anything that would change the PR's intent
- **Failing test assertions**: If a test asserts X but the code produces Y,
  investigate whether the TEST or the CODE has the bug. Never blindly flip
  an assertion to make a test pass — that defeats the purpose of the test.
  Flag the discrepancy for human review if uncertain.

## Output Format

Post a comment using `gh pr comment`:

```
## Merge Prep: Review Triage

| Source | Comment |  Action |
|--------|---------|---------|
| Agent Review | Aligns with axioms and vision | No action needed |
| Copilot | Unused import on line 42 | Fixed |
| Lint | Failed checks | Fixed |
```

## CHANGES_REQUESTED Resolution (Required)

Before finishing, **you must resolve every CHANGES_REQUESTED review** — the workflow will block approval if any remain. Find them:

```bash
gh api repos/{owner}/{repo}/pulls/{pr}/reviews \
  --jq '.[] | select(.state == "CHANGES_REQUESTED") | {id, author: .user.login, body}'
```

For each CHANGES_REQUESTED review, you MUST do one of:

1. **Fix it** — apply the fix, then dismiss: `gh api -X PUT repos/{owner}/{repo}/pulls/{pr}/reviews/{id}/dismissals -f message="Fixed: <what you did>" -f event="DISMISS"`
2. **False positive** — respond explaining why, then dismiss: `-f message="False positive: <explanation>"`
3. **Cannot fix** — leave the review in place and note in your triage table. The workflow will block and notify the maintainer.

Do NOT exit with unresolved CHANGES_REQUESTED reviews unless you explicitly document them as unresolvable in your triage table.

## Rules

- **Always run lint, typecheck, and tests after making changes.** Push clean code.

# Instructions

Review and fix PR #${{ steps.pr-info.outputs.pr_number }} in repository ${{ github.repository }}.
The PR branch is `${{ steps.pr-info.outputs.ref }}`.

Use `gh pr view ${{ steps.pr-info.outputs.pr_number }}` and `gh pr diff ${{ steps.pr-info.outputs.pr_number }}` to gather information.

Fix issues (lint, types, formatting, conflicts, test failures, bugs) by editing files and pushing commits.

- **Tag your commits** with a `Merge-Prep-By: agent` trailer so the loop detector can identify your commits. Example:
  ```
  git commit -m "fix: address review feedback

  Merge-Prep-By: agent"
  ```

If you have NO concerns and made NO fixes: do NOT file a review or comment. Just set a success status and exit silently.
If you made fixes or have concerns that you cannot fix: file a `gh pr review` (APPROVE or REQUEST_CHANGES) with your summary as the review body.

Finalise your work by setting a commit status:

- No concerns → `gh api repos/${{ github.repository }}/statuses/${{ steps.pr-info.outputs.sha }} -f state="success" -f context="Agent Review & Fix" -f description="Clean — no issues found"`
- Concerns remain → `gh api repos/${{ github.repository }}/statuses/${{ steps.pr-info.outputs.sha }} -f state="failure" -f context="Agent Review & Fix" -f description="Issues flagged — see PR review"`
