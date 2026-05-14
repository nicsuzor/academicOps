# Worker Dispatch

The dispatch mechanics that govern epic progression. The supervisor loop executes this protocol on the golden path; **pauli's** role in preflight is restricted to PKB-side reasoning (task completeness, dependency state, and decomposition), NOT shell-based environmental discovery.

> **Worker registry**: see [[WORKERS.md]] for worker types, capabilities, cost/speed profiles, capacity limits, and selection rules. Pauli reads it fresh on each preflight.

## Pre-Dispatch Validation (PKB-Side)

Before pauli emits a `dispatch` verdict, she validates the task purely through PKB operations:

1. **Task ID:** The epic / subtask being dispatched.
2. **Project:** Task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
3. **Next link in chain:** Ensure the task unblocks the epic's critical path.
4. **Existing PR Check:** Is there already a PR linked to this task? If it's a known `pr_url`, Pauli checks its state (this is the only external call Pauli makes, if needed, though strictly we prefer to just trust the PKB status).

If the task lacks a `project` and ancestors are ambiguous, or if dependencies are not met, Pauli halts or recommends a fix-task.

## Critic Gate for High-Blast-Radius Tasks

Some tasks carry risk of irreversible harm: OTA firmware updates, production deployments, data migrations, file deletions at scale. These require independent review of the task spec BEFORE dispatch.

### When the gate applies

- Task is tagged `high-risk`, `irreversible`, `production`, or `destructive`
- Task body mentions: OTA, flash, deploy, migrate, delete (at scale)
- Task modifies infrastructure (CI/CD workflows, deployment configs)
- **Pauli judgment** (authoritative): action closes a recovery path

### Gate Protocol

1. **Prepare dispatch review context** (task spec, blast radius, rollback plan).
2. **Invoke critic** — pauli evaluates: is the spec complete? Are preconditions verified? Does the action close any recovery path? Verdict: `SAFE_TO_DISPATCH` / `NEEDS_REFINEMENT` / `DO_NOT_DISPATCH`.
3. **Record gate result** in the task body's Pattern Memory.

Every critic-gated task MUST include a Rollback Plan in the task body before dispatch.

## Dispatch Execution

The supervisor main agent runs the dispatch. See the **Canonical Dispatch Template** in `SKILL.md` for the exact Bash invocation.

**Jules notes**: For Jules (asynchronous, runs on Google infrastructure), pipe task context:
`pkb task <task-id> | jules new --repo <owner>/<repo>`

### Coordinated Branch Dispatch

For tightly coupled subtasks (3+ tasks modifying overlapping files), pauli may coordinate multiple polecats onto a shared feature branch.

1. Record in Supervisor State: `**Feature Branch**: feature/<epic-id> (PR #NNN, draft)`
2. Add Branch Instructions to each subtask body: "Push commits to branch `feature/<epic-id>`. Do NOT file a separate PR."
3. Dispatch one polecat at a time to the shared branch.

## Post-Dispatch

The supervisor checks status on its next ORIENT tick — it does not actively poll.
Stale task cleanup is periodic: `polecat reset-stalled --hours 4`

Worker failures surface as missing PRs or crashed statuses. The task stays `in_progress` until reset or picked up by the react phase.

## Parallel Dispatch into a Shared Repo

When dispatching multiple general-purpose subagents at once into the same underlying repo:

1. Each agent's brief MUST instruct it to create its own private worktree (`git worktree add /tmp/wt-<task-id> ...`).
2. Explicit refspec to push (`git push -u origin <branch>:<branch>`).
3. Compute each agent's **no-touch list** = every file any other agent is touching.
