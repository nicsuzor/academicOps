# aops-jr

The sole coordinator package. `aops-jr` is a coordination layer between Nic and
the automation framework — it dispatches polecat workers and holds
coordinator-only doctrine. It is deliberately **not** a task-execution
package: skills that run *inside* a dispatched worker (`pull`, `verify`,
`handover`, `situate`, …) stay in the `aops` plugin. Anything that runs on the
coordinator's side of the fence — deciding what to dispatch, spinning up the
container, driving it — belongs here.

## Contents

- [`polecat/`](polecat/) — the CLI that spawns a polecat worker container
  (`polecat run`). Packaged independently (see `pyproject.toml`) so it has no
  dependency on the root `academicops` package. Run it via:

  ```bash
  uv run --project aops-jr python aops-jr/polecat/cli.py run <agent> -p <project> -t <task-id>
  ```

  See [`specs/polecat/polecat-system.md`](../specs/polecat/polecat-system.md)
  and [`specs/polecat/tmux-interactive-driving.md`](../specs/polecat/tmux-interactive-driving.md)
  for the current implementation status and driving patterns.
- [`skills/dispatch/`](skills/dispatch/SKILL.md) — the coordinator-side
  dispatch instructions: claims an Epic, sequences its subtasks, and launches
  polecat workers against them.

## Not yet implemented (placeholders — do not treat as live)

This package is a new home, not a finished product. The following are known
gaps, tracked but not yet built here:

- **Coordinator-mode doctrine SSoT.** `junior.md §Coordinator mode` (Nic's
  personal, machine-local orchestrator — see `.agents/CORE.md`) has doctrine
  that belongs here once consolidated. Tracked: PKB task `aops-cff86ef4`
  ("Consolidate dispatch-only / coordinator-mode doctrine into a single SSoT").
  Until that lands, this plugin has no canonical coordinator persona/doctrine
  file of its own.
- **`supervisor` skill.** `specs/polecat/supervisor.md` describes supervisor
  doctrine referenced elsewhere (`.agents/CORE.md`'s aops-core skill list
  names `/supervisor`), but no `SKILL.md` implementing it exists anywhere in
  the repo today. When it's built, it belongs in `aops-jr/skills/supervisor/`,
  not `aops`.
- **Multi-worker orchestration** (`swarm` / `watch` / `crew` / `list`).
  Described in the pre-2026-07-14 polecat architecture
  (`specs/polecat/polecat-system.md`) but not implemented in the current
  `polecat/cli.py`, which exposes only `run`. Whether/how this is rebuilt is
  an open decision (see that spec's stale-implementation banner).
- **Build/marketplace packaging.** Unlike `aops` / `aops-tools` / `aops-ts`,
  `aops-jr` is not yet wired into `scripts/build.py`, the `Makefile`
  build/install targets, or `templates/marketplace.json` — there is no
  `dist/aops-jr-claude` output today. It is source-only until that pipeline
  work happens.
- **`debug` skill relocation.** `.agents/skills/debug/SKILL.md` (interactive
  polecat driving) is conceptually coordinator-side but currently lives in
  `.agents/skills/` as a framework-dev-only tool, not a distributable skill.
  Left in place pending a decision on whether it ships as part of this plugin.
