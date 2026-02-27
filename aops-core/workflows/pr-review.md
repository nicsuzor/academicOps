---
id: pr-review
category: integration
description: Protocol for reviewing GitHub PRs using reviewer agents before human merge decisions
triggers:
  - "review PRs"
  - "check PRs"
  - "are PRs ready to merge"
  - "PR review"
  - "review pull requests"
bases: [base-batch]
---

# PR Review

Structured protocol for reviewing GitHub pull requests. The supervisor triages, invokes reviewer agents, and presents findings. The human provides final approval.

## Core Rule

**Always invoke reviewer agents.** The supervisor's own diff read is supplementary, not a substitute for custodiet-reviewer and hydrator-reviewer analysis.

## Procedure

### 1. Triage

List open PRs with metadata:

```bash
gh pr list --repo {repo} --state open \
  --json number,title,author,mergeable,statusCheckRollup,headRefName,createdAt,labels,reviewDecision
```

Classify each PR:

| Status | Action |
|--------|--------|
| CI failing | **Hold** — do not review code until CI passes |
| Merge conflicts | **Hold** — author must resolve conflicts first |
| CI passing + mergeable | **Reviewable** — proceed to step 2 |

Present the triage table to the human before proceeding. Holds do not need reviewer agents — the blocking issue is clear.

### 3. Collect Findings

Wait for reviews to complete on each PR. Their comments will appear on the PR itself.

### 4. Synthesize

Present a per-PR verdict table to the human:

```
| PR | Description: what does the PR do? | CI | Conflicts | Custodiet | Hydrator | Recommendation |
|----|-------|----|-----------|-----------|----------|----------------|
| #N | ...   | ok | none      | approved  | advisory | Ready to merge |
| #M | ...   | ok | none      | changes   | warning  | Needs fixes    |
```

For each PR, incorporate:
- CI status
- Merge conflict status
- Custodiet-reviewer findings (blocking: approve or request-changes)
- Hydrator-reviewer findings (advisory: workflow guidance)
- Supervisor's own supplementary observations

### 5. Act on Verdicts

Based on the human's decisions:

- **Clean PRs**: Approve via github API/mcp/gh comamnd
- **PRs with issues**: Leave specific fix comments on the PR describing what needs to change. Tag or invoke agents to respond.
