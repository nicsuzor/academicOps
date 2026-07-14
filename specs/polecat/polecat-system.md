---
id: polecat-system
title: "Polecat System: Ephemeral Agent Workspaces"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, architecture]
---

# Polecat System: Ephemeral Agent Workspaces

> [!warning] STALE as of 2026-07-15 — describes deleted architecture
> Commit `e70e96475` ("remove old polecat scripts", 2026-07-14) deleted
> `polecat/cli.py` (5734 lines) and its supporting modules (`manager.py`,
> `claim.py`, `finalize.py`, `bootstrap.py`, `swarm.py`, `watch.py`,
> `pkb_bridge.py`, `prompt_template.py`, `summary.py`, `validation.py`,
> `diagnostics.py`, `observability.py`). Every guarantee, CLI surface, and
> layout described below (`crew`, `nuke`, `swarm`, `list`, `finish`,
> atomic claiming, per-task worktrees, self-filed PRs, transcripts) no
> longer exists in the codebase. The sole survivor,
> `polecat/cli_lite.py`, was renamed `polecat/cli.py` on 2026-07-15 and
> exposes exactly one subcommand, `run`, which does nothing more than a
> single `docker run` (bind-mount workspace, forward env, spawn
> claude/agy/shell/sleep) — no task claiming, no PR filing, no worktree
> lifecycle. See `tests/harness/README.md` for the current, verified tmux
> pattern for driving `run` interactively.
>
> Separately, `aops/commands/pull.md` and `aops/commands/dispatch.md`
> (referenced below under "Giving Effect") both delegate to a
> `task-lifecycle` skill that does not exist in this repo — not under
> `aops/skills/`, not in the built `dist/aops-claude/skills/` bundle. It
> only survives in stale Docker build-cache layers. `/pull` and `/dispatch`
> are therefore currently broken as written; unclear whether task-claiming
> moved somewhere else or was dropped along with the rest of `cli.py`.
>
> This spec needs a full rewrite once the intended replacement
> architecture (if any) for claiming/PR-filing/worktree-isolation is
> decided — not attempted here since that's a real design decision, not a
> documentation fix. Tracked in [[aops-polecat-architecture-gap]].

The polecat system gives every dispatched task its own isolated, disposable git
workspace so many agents can work concurrently without touching each other or the
user's development checkouts. It builds on top of the PKB task system: tasks are the
queue; polecat is the workspace and execution surface.

## Giving Effect

- [[polecat/cli.py]] — CLI (`polecat run`, `polecat start`, `polecat finish`, …)
- [[polecat/manager.py]] — workspace lifecycle (mirrors, clones, claiming, nuking)
- [[polecat/finalize.py]] — `finish`: push, PR detection (for CI-gating), status transition
- [[polecat/pkb_bridge.py]] — task reads/writes against the PKB MCP server
- [[polecat/prompt_template.py]] — self-contained worker prompt built from the task
- [[polecat/observability.py]] + lifecycle events in `cli.py` — metrics and per-task
  transcript stubs
- `aops/commands/pull.md` and `aops/commands/dispatch.md` — commands which route
  work onto this surface

## Guarantees

1. **Isolation.** Each task runs in its own full clone under
   `$POLECAT_HOME/worktrees/<task-id>`, spawned from a bare mirror (or the registered
   repo path if no mirror exists) with `origin` re-pointed at the real remote.
   Nothing an agent does is visible in the user's dev checkout until merged.
2. **Concurrency.** Workspace creation is lock-protected; branch-per-task naming
   (`polecat/<task-id>` by default) prevents collisions across parallel workers.
3. **Atomic claiming.** Claiming a `queued`/`ready` task sets it `in_progress` with
   an assignee and verifies the claim stuck — two claimants cannot both win.
4. **Verified merge.** The agent files its own GitHub PR from within its session
   (`gh pr create`, per `polecat/prompt_template.py`); `finish` pushes the branch
   and detects that PR to gate on its CI status. Merging happens through PR review
   and CI, never by polecat writing to main. Failing CI checks or finish failures
   kick the task back (`in_progress` / `review`) instead of merging.
5. **Observability.** Every run updates the task record (status, assignee, PR URL)
   and appends lifecycle events to `$POLECAT_HOME/transcripts/<task-id>.jsonl`, so a
   supervisor can see where any run — including a crashed one — got to.
6. **Cleanup.** `nuke` removes the workspace and branch; unpushed work is protected
   unless explicitly forced.

## Layout

```
$POLECAT_HOME/                 # resolved via lib.paths (env var or polecat_home: config)
├── .repos/<project>.git       # bare mirrors, synced from origin (never from local checkouts)
├── worktrees/<task-id>/       # ephemeral per-task clones
├── crew/<name>/               # persistent named workspaces for interactive crew sessions
├── transcripts/<task-id>.jsonl # lifecycle events per run
└── local.yaml                 # machine-local path overrides
```

The project registry lives in `$AOPS_SESSIONS/polecat.yaml` (projects, aliases, crew
names, operational config), with per-machine paths overridable in
`$POLECAT_HOME/local.yaml`.

## Task Status Lifecycle

Polecat uses the canonical PKB statuses (see
[[aops/skills/remember/references/TAXONOMY.md#status-values-and-transitions]]):

```
queued → in_progress → merge_ready → done   (PR merged)
              │              ↘ review        (needs human judgment)
              ↘ partial                      (honest partial stop: draft PR + follow-up task)
```

## CLI Surfaces

- `polecat run` — full cycle: claim (or `-t <id>` / `--issue`) → clone workspace →
  build self-contained prompt from the task → run the agent in a container →
  auto-`finish` on success; on failure, leave the workspace intact with recovery
  instructions.
- `polecat start` / `polecat checkout <id>` / `polecat resume <id>` — claim or
  re-enter a task workspace without running an agent.
- `polecat finish` — push, set `merge_ready` (`--partial` for an honest partial
  stop). The agent files/updates the PR itself in-session; `finish` only detects
  it (for the CI-check gate) and, with `--promote`, marks an existing draft ready.
- `polecat nuke <target>` — destroy a workspace and its branch.
- `polecat crew` — persistent named interactive workspace (branch `crew/<name>`).
- `polecat swarm` / `polecat watch` / `polecat summary` — run, monitor, and
  summarise parallel workers.
- `polecat init` / `polecat sync` — create and refresh bare mirrors and working
  repos; mirrors are also safe-synced automatically before each workspace spawn.
- `polecat list` / `list-crew` / `reset-stalled` / `ping-pkb` / `setup` — inventory
  and maintenance.

## User Expectations

1. **Workspace isolation** — Test: changes in a polecat workspace are not visible in
   the registered dev repo until merged via PR.
2. **Concurrency** — Test: two `polecat start` invocations for different tasks
   produce two distinct workspaces and branches.
3. **Atomic claiming** — Test: two processes claiming the same task — one wins; the
   other picks the next task or gets none.
4. **Branch management** — Test: a new task workspace is on `polecat/<task-id>`
   (unless the task or config specifies a shared branch).
5. **Verified merge** — Test: a `merge_ready` task's work lands on main only through
   its PR; finish failures set `review`, failing CI checks set `in_progress`.
6. **Clean exit** — Test: after `polecat nuke <task-id>`,
   `$POLECAT_HOME/worktrees/<task-id>` no longer exists.
7. **Mirror freshness** — Test: workspace spawn safe-syncs the mirror from origin
   first; a sync failure warns and proceeds rather than blocking offline work.
