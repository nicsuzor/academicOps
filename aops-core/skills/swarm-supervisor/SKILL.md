---
name: swarm-supervisor
description: Orchestrate parallel polecat workers with isolated worktrees. Use polecat swarm for production parallel task processing.
triggers:
  - "polecat swarm"
  - "polecat herd"
  - "spawn polecats"
  - "run polecats"
  - "parallel workers"
  - "batch tasks"
  - "parallel processing"
  - "supervise tasks"
  - "orchestrate workflow"
---

# Swarm Supervisor - Full Lifecycle Orchestration

Orchestrate the complete non-interactive agent workflow: decompose → review → approve → dispatch → PR review → capture.

## Design Philosophy

**Dispatch and walk away.** The supervisor's job ends at dispatch. Once tasks
are sent to workers (polecat, Jules, or any other), the next touchpoint is
when pull requests arrive on GitHub. Workers are autonomous — they claim tasks,
do the work, push branches, and create PRs. Everything between dispatch and
PR is the worker's problem.

- **Supervisor decides**: Task curation, worker selection, batch composition
- **Workers execute**: Autonomously, with no supervisor monitoring
- **GitHub handles**: PR review pipeline, merge gates, CI checks
- **GitHub Actions closes the loop**: PR merge → task marked done

Code is limited to:

- **MCP tools**: Task state management (create, update, complete)
- **CLI**: Worker spawning via `polecat run -t <id>`, `polecat swarm`, or `aops task <id> | jules new`
- **GitHub Actions**: Automated PR review and task completion on merge

## Lifecycle Phases

```
┌─────────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐
│  DECOMPOSE  │───►│  REVIEW  │───►│ APPROVE │───►│ DISPATCH │───►│ PR REVIEW │───►│ CAPTURE │
│  (agent)    │    │ (agents) │    │ (human) │    │(sup+fire)│    │(GH Action)│    │ (agent) │
└─────────────┘    └──────────┘    └─────────┘    └──────────┘    └───────────┘    └─────────┘
```

### Phase 1: Decompose & Phase 2: Multi-Agent Review

The supervisor decomposes large tasks into PR-sized subtasks and invokes reviewer agents to synthesize their feedback.

> See [[instructions/decomposition-and-review]] for detailed protocols on decomposition and multi-agent review.

### Phase 3: Human Approval Gate

Task waits for human decision. Surfaced via `/daily` skill in daily note.

**User Actions**:

| Action          | Task State    | Notes                           |
| --------------- | ------------- | ------------------------------- |
| Approve         | → in_progress | Subtasks created, first claimed |
| Request Changes | → decomposing | Feedback attached               |
| Send Back       | → pending     | Assignee cleared                |
| Backburner      | → dormant     | Preserved but inactive          |
| Cancel          | → cancelled   | Reason required                 |

### Phase 4: Dispatch (fire and forget)

Supervisor selects workers, dispatches tasks, and **walks away**. No active
monitoring — the supervisor's job ends here.

> See [[instructions/worker-execution]] for worker types, selection protocols,
> and dispatch commands.

**Dispatch flow:**

1. Curate batch: select tasks, set complexity, confirm assignees
2. Mark non-approved tasks as `waiting` to prevent accidental claiming
3. Dispatch: `polecat run -t <id> -g` for individual tasks, `polecat swarm` for batch, `aops task <id> | jules new --repo <owner>/<repo>` for Jules
4. Done. Next touchpoint is when PRs arrive.

**Known limitations (from dogfooding sessions):**

- `polecat swarm` claims ANY ready task in the project, not just the curated
  batch. Mark non-batch tasks as `waiting` to prevent claiming. See `aops-2e13ecb4`.
- Auto-finish overrides manual task completion when a task was already fixed
  by another worker. See `aops-fdc9d0e2`.
- Gemini polecats are slow (15-20+ min before first commit). Don't poll — let them work autonomously.
- `polecat.yaml` `default_branch` must match reality (e.g., buttermilk uses `dev`, not `main`). Wrong config causes worktree creation failures.
- Mirror SSH failures are non-fatal if `local` remote exists (points to `/opt/nic/<repo>`). `polecat sync` warns but recovers.

### Phase 5: PR Review & Merge

**GitHub-native.** PRs arrive from workers (polecat branches, Jules PRs).
The `pr-review-pipeline.yml` GitHub Action handles automated review. Human
merges via GitHub UI or auto-merge for clean PRs.

The supervisor does NOT actively monitor for merge-ready PRs. PRs surface
naturally through GitHub's notification system and the PR review pipeline.

**PR review pipeline** (`pr-review-pipeline.yml`) has three jobs:

1. **custodiet-and-qa** — scope/compliance + acceptance checks. Runs first on
   PR open/synchronize, giving bot reviewers (Gemini, Copilot) time to post.
2. **claude-review** — bot comment triage. Runs after custodiet-and-qa (~3 min
   delay). Triages bot reviewer comments as genuine bug / valid improvement /
   false positive / scope creep, and pushes fixes for actionable items.
3. **claude-lgtm-merge** — human-triggered merge agent. Fires on human LGTM
   comment, PR approval, or workflow_dispatch. Addresses all outstanding review
   comments, runs lint/tests, and posts final status. Has full Bash access,
   with permissions to run any command in the runner.

**Pipeline limitations:**

- PRs that modify workflow files (`.github/workflows/`) cannot get pipeline
  review due to OIDC validation (workflow content must match default branch).
  These PRs need manual review and admin merge.
- Bot reviewers take 2–5 min to post. The pipeline ordering (custodiet first)
  provides enough delay for most, but Copilot may occasionally post after
  triage runs.

**Merge flow:**

- Auto-merge is enabled. Once the merge agent approves and CI passes, GitHub
  merges automatically.
- Human LGTM comment (e.g., "lgtm", "merge", "@claude merge") triggers the
  merge agent.
- Admin bypass: `gh pr merge <PR> --squash --admin --delete-branch` for PRs
  that can't get pipeline approval (workflow PRs, urgent fixes).

**Task completion on merge**: When a PR merges, a GitHub Action parses the
task ID from the branch name (`polecat/aops-XXXX`) and marks the task done.
This closes the loop without supervisor involvement.

**Jules PR workflow**: Jules sessions show "Completed" when coding is done,
but require human approval on the Jules web UI before branches are pushed
and PRs are created. Check session status with `jules remote list --session`.

**Fork PR handling**: When a bot account (e.g., botnicbot) pushes to a fork
rather than the base repo, CI workflows must use `head.sha` for checkout
instead of `head.ref` (the branch name doesn't exist in the base repo).
Autofix-push steps should be guarded with `head.repo.full_name == github.repository`.

### Phase 6: Knowledge Capture

Post-merge, supervisor extracts learnings.

> See [[instructions/knowledge-capture]] for the knowledge extraction protocol.

---

## Lifecycle Trigger Hooks

External triggers that start lifecycle phases. The supervisor is invoked
for dispatch decisions; everything after dispatch is handled by workers
and GitHub Actions.

> **Configuration**: See [[WORKERS.md]] for runner types, capabilities,
> and sizing defaults — the supervisor reads these at dispatch time.

| Hook          | Trigger       | What it does                            |
| ------------- | ------------- | --------------------------------------- |
| `queue-drain` | cron / manual | Checks queue, starts supervisor session |
| `stale-check` | cron / manual | Resets tasks stuck beyond threshold     |
| `pr-merge`    | GitHub Action | PR merged → mark task done              |

**Agent-driven dispatch**: The supervisor reads WORKERS.md, inspects the
task queue via MCP, and decides which runners to invoke and how many.
Any runner that creates PRs from task work is compatible.

---

# Parallel Worker Orchestration

Orchestrate multiple parallel polecat workers, each with isolated git worktrees. This replaces the deprecated hypervisor patterns.

> See [[references/parallel-worker-orchestration]] for architecture, usage, and troubleshooting.

## Related

- `/pull` - Single task workflow (what each worker runs internally)
- `polecat run` - Single autonomous polecat (no swarm)
- `polecat crew` - Interactive, persistent workers
- `hypervisor` - Deprecated; atomic lock pattern still useful for non-task batches
- `/q` - Quick-queue tasks for swarm to implement
- `LIFECYCLE-HOOKS.md` - Configurable trigger parameters (thresholds, notifications, runner)
- `WORKERS.md` - Worker types, capabilities, sizing defaults
