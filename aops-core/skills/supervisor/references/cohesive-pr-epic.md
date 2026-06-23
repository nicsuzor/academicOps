# Cohesive Single-PR-Epic Pattern

The framework defaults to the **cohesive single-PR-epic pattern** for all related work meant to
land together — whether pre-decomposed epics or ad-hoc/emergent tasks that arise mid-session.
The only exception is when work items must genuinely ship and be deployed independently — then
they keep legacy branch-per-task behavior.

## Live Mechanism (PR #1749 / aops-613690b5)

- **`is_shared_branch` Detection**: The manager detects shared branches by checking for custom
  branch overrides. If the branch name does not match `polecat/task-<task-id>` (e.g.
  `polecat/epic-<epic-id>`), it is treated as a shared branch.
- **Cooperative Sync**: Workers on a shared branch perform cooperative pulls and rebases
  (`git fetch` + `git rebase origin/<branch-name>`) to integrate other workers' commits.
- **Force-with-lease**: Push operations use `--force-with-lease` (low-concurrency contract).
- **No Deletion**: Shared branches bypass staleness and nuke-delete cleanup, preserving
  in-flight contributions.

## Dispatch and Concurrency Rules

1. **Shared Branch Default**: Every worker dispatched for a subtask of a cohesive epic must use
   the exact same branch via the override flag: `--branch polecat/epic-<epic-id>`.
2. **Decomposition Structure**:
   - **Parallel-able units**: no inter-dependency, can execute concurrently on the shared branch.
   - **Sequential-dependency units**: carry explicit `depends_on: [<id>]` edges; blocked until
     predecessor tasks are marked complete.

## One Epic, One PR — promote at the capstone

**One epic ships as ONE pull request.** No per-task / single-part PRs reach the merge pipeline.
Your single PR-state action is the **promotion at the end**: flip it ready once all work items
are `done` and the capstone (one cumulative `marsha` pass) is green. A PR with outstanding work
items is the normal mid-epic state — do not promote early.

You do **not** manage merge mechanics. The single PR materialises automatically when the first
worker on the shared branch finishes; workers never create PRs, and the supervisor never
hand-creates one. Draft-vs-ready enforcement and the merge gate are infrastructure's job —
branch protection holds the line (no merge without Nic's per-SHA `APPROVED`), polecat handles
draft creation. Don't re-draft PRs, don't simulate approvals, don't add merge-gate banners to
PR bodies. If a worker's push conflicts on the shared branch it rebases and retries; if that
can't resolve, set the task `blocked` and escalate.

## Canonical Dispatch Command (polecat surface)

The discipline is dispatch-surface independent — identical across polecat containers and
Agent-tool background subagents.

**Polecat-surface**: the canonical invocation form, host path, and model alias list are
machine-specific and live in the PKB — see memory `mem-3014f36b` (polecat `--model` flag
aliases) and `remote-polecat-tmux-dispatch` (SSH/WSL dispatch guide). Always consult PKB
before constructing a dispatch command; the model flag API has changed before and will again.

Template (fill in host path and model alias from PKB):

```bash
uv run --project <host-path> <host-path>/polecat/cli.py run \
  -t <task-id> -p <project> --branch polecat/epic-<epic-id> --model <alias>
```

**Agent-tool surface**: `Agent(subagent_type=…, run_in_background=True)` replaces the Bash
invocation; the §7 context-economy and capped-handback contract still apply.

## Known Limitations

For Gemini exit-code 1 / `429 QUOTA_EXHAUSTED` diagnosis: see PKB memory
`mem-0b59a37b` (Gemini polecat exit-code diagnosis tree). Do not substitute Gemini
with Claude automatically (Halt-on-substitute).
