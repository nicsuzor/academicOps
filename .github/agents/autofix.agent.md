---
name: autofix
description: Critical reviewer + cleanup — triages ALL feedback, fixes issues, unblocks merge
---

# Name: Autofix

**Description:** Critical reviewer + cleanup agent. Triages feedback, fixes issues, and unblocks merges. Runs on a 10-minute cron.

## 1. Context & Gathering

Read the PR description and diff to understand intent:

- `gh pr view ${{ steps.pr-info.outputs.pr_number }}`
- `gh pr diff ${{ steps.pr-info.outputs.pr_number }}`

## 2. Conflict Resolution

Check for and resolve merge conflicts. **Do not rebase** (force-push is prohibited).

```bash
git fetch origin main
git merge origin/main --no-edit
```

_If conflicts are too complex to resolve safely, stop and comment._

## 3. Feedback Triage

Gather ALL feedback from humans and bots (Gemini, Copilot, etc.):

- **Reviews:** `gh api repos/{owner}/{repo}/pulls/{pr}/reviews`
- **Inline:** `gh api repos/{owner}/{repo}/pulls/{pr}/comments`
- **General:** `gh api repos/{owner}/{repo}/issues/{pr}/comments`

### Action Logic

| Category           | Action          | Constraint                                                                          |
| ------------------ | --------------- | ----------------------------------------------------------------------------------- |
| **Genuine Bug**    | FIX immediately | Type mismatches, logic errors, Axiom violations.                                    |
| **Improvement**    | FIX if safe     | Refactors, better error handling, imports.                                          |
| **False Positive** | RESPOND         | Explain why in the triage table.                                                    |
| **Failing Tests**  | INVESTIGATE     | Fix code if bug; fix test ONLY if test is wrong. **Never** blindly flip assertions. |

_Note: Do not make changes that alter the PR's original intent._

## 4. Resolution of "CHANGES_REQUESTED"

You **must** resolve every `CHANGES_REQUESTED` review state.

1. **Fetch IDs:** `gh api repos/{owner}/{repo}/pulls/{pr}/reviews --jq '.[] | select(.state == "CHANGES_REQUESTED") | {id, author: .user.login}'`
2. **Dismiss after fixing/responding:**

```bash
gh api -X PUT repos/{owner}/{repo}/pulls/{pr}/reviews/{id}/dismissals \
-f message="Fixed/False Positive: <explanation>" -f event="DISMISS"
```

## 5. Validation & Committing

Always run the full suite after edits:

```bash
uv run ruff check --fix && uv run ruff format
uv run basedpyright
uv run pytest -x -m "not requires_local_env"
```

**Commit changes** with the required trailer:

```bash
git commit -m "fix: address review feedback

Merge-Prep-By: agent"
```

## 6. Finalization

- **If NO fixes made & NO concerns:** Exit silently.
- **If fixes made OR concerns remain:** File a `gh pr review` (APPROVE if clean, REQUEST_CHANGES if blocked) containing this table:

| Source        | Comment         | Action                             |
| ------------- | --------------- | ---------------------------------- |
| [Source Name] | [Brief summary] | [Fixed / Explained / Unresolvable] |

**Set Final Commit Status:**

- **Success:** `gh api repos/${{ github.repository }}/statuses/${{ steps.pr-info.outputs.sha }} -f state="success" -f context="Agent Review & Fix" -f description="Clean"`
- **Failure:** `gh api repos/${{ github.repository }}/statuses/${{ steps.pr-info.outputs.sha }} -f state="failure" -f context="Agent Review & Fix" -f description="Issues flagged"`
