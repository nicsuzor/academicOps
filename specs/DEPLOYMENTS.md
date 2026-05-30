# aops Bot Deployments

> Canonical reference for which repositories have aops bot automation installed,
> at what tier, and with which workflows and agents. State — the current truth,
> not a proposal. To _deploy_ to a new repo, follow the
> [deploy-bot-to-repo workflow](../aops-core/skills/project/workflows/deploy-bot-to-repo.md).

## Audience and scope

**Primary audience**: orchestrator agents and operators deciding whether a repo
already has automation, what tier it runs, and what to expect there. Also:
future-Nic auditing coverage and planning the next deployment.

**How to keep current**: when a repo is newly deployed, upgraded, or has its
workflows/agents materially changed, update its row in the same PR. Per-row
updates only — don't rewrite the table to record a single change.

## Tiers

- **Light** — `claude.yml` + `pr-review`: @claude mention handler and PR review.
  For small/low-activity repos.
- **Full** — review pipeline + `agent-enforcer` + `agent-merge-prep` +
  `merge-prep-cron` + QA agents. For active repos with regular PRs.

See [deploy-bot-to-repo](../aops-core/skills/project/workflows/deploy-bot-to-repo.md)
for what each tier installs and how.

## Current deployments

| Repo                  | Tier  | Workflows                                                                                       | Agents                                      |
| --------------------- | ----- | ----------------------------------------------------------------------------------------------- | ------------------------------------------- |
| nicsuzor/academicOps  | Full  | pr-pipeline, agent-enforcer, agent-merge-prep, merge-prep-cron, claude                          | pr-reviewer, enforcer, qa                   |
| qut-dmrc/buttermilk   | Full  | pr-review-pipeline, agent-merge-prep, agent-qa, agent-strategic-review, claude, merge-prep-cron | custodiet, gatekeeper, qa, strategic-review |
| nicsuzor/mem          | Full  | pr-pipeline, agent-enforcer, agent-merge-prep, merge-prep-cron                                  | pr-reviewer, enforcer, custodiet, qa        |
| nicsuzor/brain        | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/explorations | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/omcp         | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/zotmcp       | Light | pr-review, claude                                                                               | —                                           |
| nicsuzor/labeler      | Light | pr-review, claude                                                                               | —                                           |
