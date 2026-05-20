# Execution Surfaces

> Canonical reference for where Claude Code and Gemini CLI run across this framework, what each surface can and can't do, and the load-bearing operational facts that bite when wrong.

## Audience and scope

**Primary audience**: orchestrator agents (`jr` / `junior`, `james`) deciding _where to send work_ or _whether a given thing is supposed to function here_. Also: future-Nic debugging cross-surface issues.

**Not the primary audience**: an agent already inside a surface trying to orient itself — that agent should rely on the surface's own startup context (`CORE.md` / `CLAUDE.md` / `GEMINI.md` / hydration). This doc is for the dispatcher's view, not the dispatchee's.

**When to consult**:

- Before dispatching work: "which surface for this task?"
- When diagnosing: "is X _supposed_ to work on surface Y? if not, where would it work?"
- When changing one surface: "what else depends on the current behaviour here?"

**How to keep current**: when a surface's behaviour materially changes (new plugin override, env-propagation fix, new MCP, retired gate), update its section in the same PR. Per-row updates only — don't rewrite the whole doc to add a single fact.

---

## TL;DR matrix

| Surface                 | Engine                             | Persistence                           | Plugin source                                                                | Hook env propagation                          | Trust posture                  | Can dispatch onto                       |
| ----------------------- | ---------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------- | ------------------------------ | --------------------------------------- |
| WSL crew container      | Claude Code (interactive, in `polecat crew` container) | Persistent crew worktree (`/workspace`); container itself ephemeral | `dist/aops-claude/` baked into the crew Docker image | Container env at launch (no `launchctl` / `.zshenv` hop) | Orchestrator — full user trust | polecat (`run`/`crew`), Jules, GHA      |
| Claude Code CLI on host | Claude Code                        | Persistent                            | aops-core plugin from `~/.claude/plugins/cache/academicOps/aops-core/<ver>/` | ⚠ broken — stripped (see traps)               | Full user trust                | polecat (run/crew), Jules, host shell   |
| Gemini CLI on host      | Gemini CLI (Google)                | Persistent                            | aops-gemini extension from `nicsuzor/academicOps`                            | ⚠ unknown — verify                            | Full user trust                | polecat (run/crew --gemini), host shell |
| `polecat run` Claude    | Claude Code (headless)             | Disposable worktree, Docker container | `dist/aops-claude/` from `nicsuzor/aops-dist` (built into image)             | `POLECAT_SESSION_TYPE=run` → run-mode gates   | Autonomous, repo-scoped        | Nothing (terminal worker)               |
| `polecat run` Gemini    | Gemini CLI (headless)              | Disposable worktree, Docker container | `dist/aops-gemini/` from `nicsuzor/academicOps` (extension install)          | ⚠ unknown — verify                            | Autonomous, repo-scoped        | Nothing                                 |
| `polecat crew` Claude   | Claude Code (interactive)          | Persistent crew worktree, Docker      | `dist/aops-claude/` (same as run)                                            | `POLECAT_SESSION_TYPE=crew` → crew-mode gates | Multi-agent interactive        | Sibling crew agents                     |
| `polecat crew` Gemini   | Gemini CLI (interactive)           | Persistent crew worktree, Docker      | `dist/aops-gemini/`                                                          | ⚠ unknown — verify                            | Multi-agent interactive        | Sibling crew agents                     |
| GHA runner              | `anthropics/claude-code-action@v1` | Transient (per job)                   | Agent prompt from `.github/agents/*.md` (no plugin)                          | Workflow `env:` block only                    | Repo-scoped, ephemeral         | Nothing                                 |
| Jules                   | Jules (Google)                     | Google-side session, async            | Opaque (Google infra)                                                        | N/A — no host hooks                           | Google-sandboxed, async        | Nothing                                 |

> Retired surface — Mac Cowork sandbox dispatching to WSL via `ssh wsl` — is preserved at the end of this doc under "Retired surfaces" (2026-05-19). Do not consult it for current architecture.

---

## Surfaces

### WSL crew container

The orchestrator's current daily-driver surface. Claude Code runs **directly inside a `polecat crew` Docker container on WSL** — the same Docker host environment that runs polecats. `/workspace` is the mounted persistent working tree. There is no Mac → WSL SSH hop: this container *is* the runtime that the orchestrator agent (junior) speaks from. The Mac Cowork → SSH-into-WSL model that preceded this is retired as of 2026-05-19 after the SSH-key incident (see "Retired surfaces" below).

- **Engine**: Claude Code (interactive), running inside a long-running `polecat crew` container on WSL.
- **Persistence**: The crew worktree at `/workspace` is persistent (mounted from the WSL host). The container itself is ephemeral — anything outside `/workspace` should be treated as wiped between sessions. State that must survive lives in `/workspace` (this repo), in `~/junior/` (mounted), or in the PKB.
- **Plugin source**: `dist/aops-claude/` baked into the crew Docker image at build time (same image as `polecat crew` Claude rows below — this surface *is* that crew). No marketplace involvement; no local-install override mechanic. Plugin version is pinned at image build until the image is rebuilt.
- **Hook env propagation**: The container receives env at launch (`POLECAT_SESSION_TYPE=crew`, `$AOPS_SESSIONS`, `$AOPS_POLECAT_CONFIG`, etc.) directly from the polecat launcher. There is **no `launchctl` / `.zshenv` hop** — the cross-surface env-stripping bug that bites Mac surfaces does not apply here. `gate_config.py` reads `polecat.yaml` and resolves with `for_mode("crew")`.
- **MCPs available**: PKB (`mcp__plugin_aops-core_pkb__*`) via Tailscale from the container — load via `ToolSearch select:mcp__plugin_aops-core_pkb__*` since they are deferred. Other MCPs depend on the crew launch config; verify per-session.
- **Gates active**: Per `polecat.yaml crew_defaults` overlay + `gates.*`.
- **Worker dispatch**: Direct — invoke polecat via `uv run --project ~/src/academicOps ~/src/academicOps/polecat/cli.py <subcommand> ...`. Can launch Jules via `pkb task | jules new --repo`. Can launch GHA via `gh workflow run`. No SSH hop required; no `ssh wsl` aliases.
- **Canonical polecat invocation** (from `~/junior/.agents/CORE.md`): always use the direct `uv` form — `uv run --project ~/src/academicOps ~/src/academicOps/polecat/cli.py run -t <task-id> -p <project> --model <name>`. Do **not** use the `polecat` / `pc` shell aliases — they live in interactive zsh only and load a different env. Polecat must self-configure from `polecat.yaml`.
- **Editing the canonical aops repo**: Do not edit `$AOPS` (`~/src/academicOps`) directly from this orchestrator container. Framework-file edits go through the PKB-task → polecat-worker → PR loop. Stealth edits from the orchestrator bypass review.
- **Known traps**:
  - **Mount scope is narrow but not single-folder**: `/workspace` is the persistent working tree; `~/junior/` is mounted; `~/src/academicOps` and `~/brain` are reachable to support framework operations and task inspection. Other container paths are ephemeral.
  - **Obsolete bootstrap**: `~/junior/bootstrap.sh` is left over from the retired Mac → SSH → WSL model; do not run it.
  - **PKB indexing lag** — `create_task` returns before the task is searchable; confirm with `get_task` before dispatching a polecat that needs to find it.
  - **Background-subagent file outputs are invisible to Nic** — if you delegate, summarise inline. Filenames are traceability, not deliverables.
- **Trust posture**: Full user trust — runs as the orchestrator, can take destructive actions with user approval.

---

### Claude Code CLI on host

Native Claude Code installation on a developer machine (laptop, WSL, services-new). Same surface, different hosts.

- **Engine**: Claude Code (Anthropic CLI / Claude.app)
- **Persistence**: Persistent. Filesystem, settings, plugin cache all survive.
- **Plugin source & override behaviour**: aops-core loaded from `~/.claude/plugins/cache/academicOps/aops-core/<ver>/` (most recent dir wins). Plugin enabled per `~/.claude/settings.json` `enabledPlugins`. No marketplace-override issue on this surface.
- **Hook env propagation**: ⚠ **Broken.** `settings.json` `env` block doesn't propagate to hook subprocesses (`launchctl setenv` ignored; `.zshenv` partially sourced but `PATH` overridden). All `*_GATE_MODE` env vars in settings.json are dead — `gate_config.py` ignores env vars by design (hard-fail policy) and reads only from `polecat.yaml` via `$AOPS_SESSIONS`. Result: gates silently fail on import if `$AOPS_SESSIONS` isn't in hook env. → see _Cross-cutting: Hook env stripping_.
- **MCPs available**: Same set as the WSL crew container plus host-shell access. Specific MCP set depends on host's `settings.json` `mcpServers` block.
- **Gates active**: ⚠ Currently none reliably — see hook env trap. After cleanup, ida/handover/custodiet/qa active per `polecat.yaml gates.*`.
- **Worker dispatch**: Direct — can launch `pc run`, `pc crew`, `jules`, GHA workflows. The intended primary dispatcher surface alongside the WSL crew container.
- **Known traps**:
  - Hook env stripping (see above and cross-cutting).
  - **Stale plugin cache directories** — multiple `0.3.23-dev.*` versions in `~/.claude/plugins/cache/academicOps/aops-core/`; Claude.app uses most recent but doesn't garbage-collect old ones.
  - **`AOPS_BOT_GH_TOKEN` leakage risk** — token sits in plaintext in `settings.json`. Anything dumping `env` to logs leaks it.
- **Trust posture**: Full user trust.

---

### Gemini CLI on host

Native Gemini CLI installation on a developer machine. Same plugin/hook philosophy as Claude Code CLI but distinct extension format.

- **Engine**: Gemini CLI (Google)
- **Persistence**: Persistent.
- **Plugin source & override behaviour**: aops-gemini extension installed from `nicsuzor/academicOps` (via `gemini extensions install`). Distinct codebase from aops-core: `dist/aops-gemini/` mirrors `dist/aops-claude/` but with Gemini-specific tool wrappers (e.g. `delegate_to_agent`, `activate_skill`).
- **Hook env propagation**: ⚠ **Unknown.** Gemini's hook subprocess env behaviour not documented anywhere I've found. Likely similar gap to Claude Code CLI but not verified.
- **MCPs available**: ⚠ Subset of Claude's — needs verification per-host.
- **Gates active**: ⚠ Unknown. Gate logic shared via `dist/aops-gemini/hooks/gate_config.py` (same `IDA_GATE_MODE` constant) but firing behaviour not verified.
- **Worker dispatch**: Can launch `pc run --gemini`, `pc crew --gemini`. ⚠ Other dispatch paths not verified.
- **Known traps**:
  - Bare-agent tools (`aops_core_enforcer`, `aops_core_rbg`, `aops_core_marsha`) registered as top-level Gemini tools per `gate_config.py:388-390`. Distinct from Claude's `Agent(subagent_type=…)` path.
  - Common typo variant: PKB tools sometimes show up as `mcp__pbk__*` (per `gate_config.py:466` normalization comment). Don't depend on naming consistency.
- **Trust posture**: Full user trust.

---

### `polecat run` Claude (autonomous worker)

The canonical autonomous worker. Headless Claude Code in a Docker container against a disposable worktree.

- **Engine**: Claude Code (headless mode: `claude -p <prompt> --max-turns <budget>`)
- **Persistence**: Disposable worktree at `$POLECAT_HOME/polecat/<task-id>/`. Container ephemeral. On success: auto-finish pushes branch, marks task `merge_ready`, nukes worktree.
- **Plugin source & override behaviour**: `dist/aops-claude/` baked into the Docker image (built from `nicsuzor/aops-dist`). No marketplace involvement. Plugin version pinned at image build time — may lag canonical source until image rebuild.
- **Hook env propagation**: Container sets `POLECAT_SESSION_TYPE=run`; `gate_config.py:431` resolves run-mode overlay from `polecat.yaml`. Other env (`$AOPS_SESSIONS`, etc.) propagated via container env at launch.
- **MCPs available**: ⚠ **Significantly reduced.** PKB MCP requires Tailscale network access, which is host-side; container's reachability needs verification per-config. Aim is full PKB access; reality varies.
- **Gates active**: Per `polecat.yaml run_defaults` overlay + `gates.*`. Reads same `polecat.yaml` as host but resolves with `for_mode("run")`.
- **Worker dispatch**: Terminal — workers don't dispatch further work. They commit, push, exit.
- **Known traps**:
  - **Stealth edits to canonical repo** — workers can `git push` directly to feature branches but should not edit framework files outside their task scope.
  - **PKB write lag** — same indexing-lag issue as host; downstream supervisor ticks may not see worker outputs immediately.
  - **OOM (exit 137)** — Docker memory limits hit on extended-thinking tasks. Surfaced with platform-specific remediation per `polecat-system` spec.
  - **Auto-finish override loop** — if another worker already completed the task (e.g. Jules), polecat detects zero changes and resets to active, creating retry loop. (Known issue, see `aops-fdc9d0e2`.)
- **Trust posture**: Autonomous within repo scope. Can push to feature branches, create PRs. Should NOT push to main, modify shared infra, or touch out-of-repo paths.

---

### `polecat run` Gemini

Same surface as `polecat run` Claude but with the Gemini CLI as the engine.

- **Engine**: Gemini CLI (headless)
- **Persistence**: Same as Claude variant.
- **Plugin source & override behaviour**: `dist/aops-gemini/` baked into image. Same caveats.
- **Hook env propagation**: ⚠ Unknown — likely same as Claude run-mode but not verified.
- **MCPs available**: ⚠ Unknown subset; needs verification.
- **Gates active**: Same `polecat.yaml` source; gate-firing behaviour ⚠ not verified for Gemini engine.
- **Worker dispatch**: Terminal.
- **Known traps**:
  - **Per `academicops-7d85d45d`**: `pc run -it` (without explicit `--gemini`) historically launched Gemini instead of Claude due to default-agent confusion. Verify default is Claude.
  - Gemini workers are slower (~15 min for medium tasks per `mem-0f8a18d8`) — good for correctness, bad for throughput.
  - Marsha-side boot-time stderr noise is cosmetic, not a failure signal.
- **Trust posture**: Same as Claude variant.

---

### `polecat crew` Claude (interactive multi-agent)

Interactive Docker session — multiple Claude Code instances cooperating in a persistent crew worktree. **This is the engine of the "WSL crew container" surface above** (the orchestrator runs as one such crew session); other crew sessions are sibling worker agents within the same worktree.

- **Engine**: Claude Code (interactive)
- **Persistence**: Persistent worktree at `$POLECAT_HOME/polecat/crew/` (not disposable like `run` worktrees). Multiple crew sessions can revisit the same worktree.
- **Plugin source & override behaviour**: `dist/aops-claude/` from `nicsuzor/aops-dist` (same image as `polecat run`). Per `aops-d40b25a7`, crew should launch with Claude settings in 'user' mode.
- **Hook env propagation**: Container sets `POLECAT_SESSION_TYPE=crew`; `gate_config.py` resolves crew-mode overlay. `polecat.yaml` `crew_defaults: {}` block must exist (per inline YAML comment) — empty overlay is valid, but the key is required.
- **MCPs available**: ⚠ Per-launch; depends on `pc crew` flags.
- **Gates active**: Per `polecat.yaml crew_defaults` overlay.
- **Worker dispatch**: Crew agents can hand off to sibling crew agents within the same session.
- **Known traps**:
  - **Sudden silent exit** (`crew-session` PKB doc) — crew sessions that "just quit" after extended thinking are more likely API timeouts than OOM. Restart; no work lost (worktree preserved).
  - **No tmux harness in test suite** — pytest e2e for crew is brittle; an in-progress test harness is `aops-44c697d7`. Don't rely on automated crew testing.
- **Trust posture**: Interactive multi-agent — multiple user-trusted agents collaborating.

---

### `polecat crew` Gemini

Same as `polecat crew` Claude with Gemini CLI as engine.

- **Engine**: Gemini CLI (interactive, sandbox mode)
- **Persistence**: Same persistent crew worktree pattern.
- **Plugin source**: `dist/aops-gemini/` (extension install).
- **Hook env propagation**: ⚠ Unknown — verify.
- **MCPs available**: ⚠ Unknown subset.
- **Gates active**: ⚠ Unknown — verify crew-mode gate behaviour for Gemini.
- **Worker dispatch**: Same as Claude crew variant.
- **Known traps**: ⚠ Sparsely tested. The `academicops-ced83088` task covered initial setup but verification is incomplete.
- **Trust posture**: Same.

---

### GHA runner

GitHub Actions agent runs via `anthropics/claude-code-action@v1` on transient Ubuntu runners. Distinct from polecats in every meaningful way.

- **Engine**: Claude (Anthropic API) via `claude-code-action@v1`. No interactive CLI; runs as a GitHub Action step.
- **Persistence**: Transient — each job starts clean. No state between runs.
- **Plugin source & override behaviour**: **No aops-core plugin.** Agent prompt loaded from `.github/agents/*.md` files in the repo (rbg-agent, pr-reviewer-agent, etc.) or fetched via sparse-checkout. Mechanism is entirely different from local plugins.
- **Hook env propagation**: Workflow `env:` block only. Secrets via GitHub Actions secrets store.
- **MCPs available**: **None** — PKB MCP server is Tailscale-only. No PKB, no zot, no email, no computer-use.
- **Gates active**: None (no plugin, no hooks).
- **Worker dispatch**: Terminal — GHA jobs don't launch other surfaces. (They can `gh pr create`, `gh pr review`, etc. — these are GitHub API actions, not worker dispatch.)
- **Constraints**:
  - Job timeout: typically 10–30 min (configurable, hard cap 6 h).
  - Available tooling: `git`, `gh` CLI, `uv`, Python, bash. File read/write on checked-out repo.
  - Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `AOPS_BOT_GH_TOKEN`.
- **Known traps**:
  - Untriaged GHA review feedback can pile up on admin-merged PRs (per `aops-215aa5a8`).
  - Agent prompt drift: prompts in `.github/agents/*.md` are not auto-synced with plugin-side equivalents; each side evolves separately.
- **Trust posture**: Repo-scoped only. Can push to PR branches, post reviews, set statuses. Cannot reach Tailscale services or any external infra.

---

### Jules

Asynchronous Google-infra worker. Receives a task spec, returns a session URL, eventually produces a PR after human approval on the Jules web UI.

- **Engine**: Jules (Google) — opaque Google-side implementation.
- **Persistence**: Google-side session, async. One session per task.
- **Plugin source & override behaviour**: N/A — Jules runs on Google infrastructure; our plugins don't apply.
- **Hook env propagation**: N/A — no local hooks.
- **MCPs available**: N/A — Jules operates with whatever Google provides.
- **Gates active**: None of ours.
- **Worker dispatch**: Terminal.
- **Dispatch syntax**: `pkb task <task-id> | jules new --repo <owner>/<repo>` (pipes full task context into Jules's session creator).
- **Status checks**: `jules remote list --session`. Approval surface: https://jules.google.com.
- **Install**: `npm install -g jules` (⚠ verify package name).
- **Known traps**:
  - **Approval gate** — sessions show "Completed" when coding is done but require human approval on Jules web UI before branches are pushed and PRs are created. Don't assume Completed = PR exists.
  - **Auto-finish conflict** — if Jules completes a task that's also assigned to a polecat, polecat's auto-finish detects zero changes and resets task to active, creating retry loop. (Same trap as `polecat run` known-trap, surfaces from Jules side.)
  - **Opaque failures** — Jules-side errors don't surface to PKB or Slack; check the web UI.
- **Trust posture**: Google-sandboxed, async, human-gated. Highest sandbox; lowest visibility.

---

## Cross-cutting notes

### Hook env stripping (load-bearing bug across Mac/CLI host surfaces)

`settings.json`'s `env` block does NOT propagate into hook subprocesses on Mac/CLI host surfaces. `launchctl setenv` is ignored by Claude.app; `.zshenv` is partially sourced but `PATH` is overridden. `gate_config.py` (post-2026-03 cleanup) hard-fails when `$AOPS_SESSIONS` or `$AOPS_POLECAT_CONFIG` is absent — there are no env-var fallbacks by design.

**Net effect**: any gate reading `polecat.yaml` crashes on hook import on Mac/CLI host surfaces. PreToolUse path appears to fire correctly (custodiet works); Stop/SessionEnd paths crash silently.

**Scope**: this bug bites surfaces that go through `launchctl` / `.zshenv` to reach hook subprocesses — i.e. the Mac/CLI host surfaces above. The WSL crew container and `polecat run/crew` containers receive env directly at container launch and are **not** affected.

Tracking: archived-but-still-true [academicops-459eb8f3] and [aops-1bf76d85]. Resolution is a precondition for trusting any cross-surface gate-firing claim in this document.

### Plugin source variance

| Surface                   | Where the plugin code physically lives                                                        |
| ------------------------- | --------------------------------------------------------------------------------------------- |
| WSL crew container        | `dist/aops-claude/` baked into the crew Docker image (same as `polecat crew` Claude)          |
| Claude Code CLI on host   | `~/.claude/plugins/cache/academicOps/aops-core/<ver>/`; populated from marketplace            |
| Gemini CLI on host        | `~/.gemini/extensions/aops/` (via `gemini extensions install`)                                |
| `polecat run/crew` Claude | `dist/aops-claude/` baked into Docker image at build time                                     |
| `polecat run/crew` Gemini | `dist/aops-gemini/` from extension install in image                                           |
| GHA runner                | `.github/agents/*.md` agent prompts (no plugin)                                               |
| Jules                     | Opaque (Google-side)                                                                          |

Implication: when shipping a plugin change, multiple consumers need to pick it up via different mechanisms. PR landing isn't propagation.

### Mode resolution (crew vs run)

`gate_config.py:432-433` reads `POLECAT_SESSION_TYPE`. Value `crew` → crew-mode overlay; anything else → run-mode overlay. The "anything else" includes the host (Claude Code CLI on laptop) — host sessions resolve to **run mode** by default, not a separate "host" mode. This is implicit; no doc names it as a design decision. The WSL crew container surface resolves to **crew mode** (it is a `polecat crew` session).

---

## Gaps / open questions

- Gemini CLI hook env propagation — verify whether Gemini behaves like Claude Code CLI (stripped) or differently.
- Gemini polecat (run & crew) gate-firing behaviour — empirically verify.
- MCP availability per polecat surface — what reaches into a Docker container vs not.
- Jules sandbox internals — what model, what tool surface, what context window. Currently opaque.
- Post-cleanup gate-firing matrix — once hook env stripping is fixed on Mac/CLI host surfaces, replace `⚠ Currently…` cells with verified state.
- **Domain Specialists registry** — referenced from `instructions/decomposition-and-review.md` (Domain Specialist Invocation protocol) but does not exist anywhere. Either backfill here, move to a sibling doc, or remove the calling section.
- **Sizing defaults & cost/speed profiles** — referenced from `SKILL.md` and `instructions/worker-dispatch.md` but undefined. Likely obsolete (the `polecat swarm` command was removed). Confirm and clean the calling references.
- **Per-worker failure-modes consolidated table** — per-surface "Known traps" sections above cover this distributed; consider whether a consolidated table earns its keep.
- jeeves residue: epic-4234682b Step 7 and Step 9 both say `JulesWorker` after rename — collapse or rename one.

> _Resolved 2026-05-20 (via [aops-e6a80f83]):_ the Cowork-vs-CORE.md contradiction in the Cowork row, and the Cowork mount-scope contradiction, are both resolved by retiring the Mac-Cowork-via-SSH surface and rewriting this doc's primary orchestrator row as "WSL crew container" per `junior/.agents/CORE.md`. The retired surface is preserved in "Retired surfaces" below.

---

## Retired surfaces

Surfaces preserved here for historical traceability. **None of the entries below describe current architecture.** Anything an orchestrator agent needs to decide where to dispatch work today should come from the live "Surfaces" section above.

### Cowork sandbox (Mac Claude.app, dispatching to WSL via `ssh wsl`) — retired 2026-05-19

**Reason for retirement**: SSH-key incident on 2026-05-19. The cross-surface SSH dispatch model (Mac Claude.app orchestrator → `ssh wsl 'polecat run …'`) was retired in favour of running the orchestrator directly inside a `polecat crew` container on WSL (see "WSL crew container" in the live surfaces section). The replacement removes the SSH hop entirely.

**Historical description** (do not treat as current):

The Claude.app-hosted orchestrator environment Nic used as his daily driver for cross-machine coordination work, prior to the 2026-05-19 architecture change.

- **Engine**: Claude Code (Anthropic Claude.app)
- **Persistence**: Ephemeral VM. `~/.ssh/`, `~/.bashrc`, anything outside `~/junior/` was wiped between sessions. Persistence lived in `~/junior/` (mounted from host) or in the PKB.
- **Plugin source & override behaviour**: Claude.app's plugin loader did not load aops-core from the marketplace, so the cowork-plugin had to be installed _locally_. When the local install happened, Claude.app overwrote whatever marketplace version was present.
- **Hook env propagation**: ⚠ partial. `settings.json` `env` block reached the agent's Bash tool but NOT hook subprocesses. Gates that read `$AOPS_SESSIONS` (e.g. via `gate_config.py`) crashed on import. PreToolUse path did fire (custodiet worked); Stop/SessionEnd path crashed silently.
- **MCPs available**: PKB (`mcp__plugin_aops-core_pkb__*`), Slack (Anthropic Slack MCP), Chrome (`mcp__Claude_in_Chrome__*`), computer-use (`mcp__computer-use__*`), playwright, outlook, zot, hass, scheduled-tasks, ccd-session-mgmt, mcp-registry, claude-preview. **Not** present: direct shell access to polecat host (needed `ssh wsl`).
- **Gates active**: PreToolUse / custodiet fired; ida / handover / hydration crashed on env.
- **Computer-use tier**:
  - Browsers (Safari/Chrome/Firefox/Arc): **read** — screenshots OK, clicks/typing blocked.
  - Terminals + IDEs (Terminal/iTerm/VS Code/JetBrains): **click** — left-click OK, typing/right-click/modifiers/drag blocked.
  - Everything else: **full**.
- **Worker dispatch**: Could launch polecats on WSL via `ssh wsl 'polecat run …'`. Could launch Jules via `pkb task | jules new --repo`. Could launch GHA via `gh workflow run`. Could not launch host-side Claude Code sessions directly (Cowork → host was one-way SSH).
- **Known traps (historic)**:
  - **Hook env stripping** — `settings.json` `env` block did not reach hooks; gates reading `$AOPS_SESSIONS` crashed on import.
  - **Plugin override mechanic** — re-installing locally overwrote the marketplace version.
  - **Mount scope contradiction** — CORE.md stated "only `~/junior` is mounted" but `~/src/academicOps`, `~/brain`, `~/.aops/` were also reachable in practice. Resolved by retirement (the contradiction is moot now that the surface itself is retired).
  - **PKB indexing lag** — `create_task` returned before the task was searchable.
- **Trust posture**: Full user trust — ran as the orchestrator, could take destructive actions with user approval.

**What replaced it**: see "WSL crew container" in the live surfaces section above. The orchestrator now runs as an interactive `polecat crew` session on WSL, with `/workspace` as the persistent working tree. The SSH hop is gone.

---

## How to update this doc

1. **Per-row updates only.** When a surface's behaviour changes, edit only that surface's section + relevant rows in the TL;DR matrix. Don't restructure to add one fact.
2. **New surface arrives** (e.g. remote docker host worker per polecat v2 plan): add a new section in the same shape; add a row to the TL;DR matrix; cross-reference the polecat-system spec.
3. **A trap is discovered**: add it to that surface's "Known traps" _and_ (if it spans surfaces) the Cross-cutting notes section.
4. **Cleanup lands** (e.g. hook env propagation fixed): zero out the `⚠` cells; move resolved traps to a brief "Resolved" appendix or just delete.
5. **A surface is retired**: move its section to "Retired surfaces" with a retirement date and reason; preserve content for traceability. Do not delete history.
6. **PKB pointer**: a thin `surfaces` PKB doc exists whose only job is vector-search discoverability — its content is just "canonical at `aops-core/SURFACES.md`" plus a paragraph excerpt. When this doc's framing changes (audience, scope), update the PKB pointer to match.

---

## See also

- `polecat-system` PKB spec — deep lifecycle, refinery, dispatch internals
- `execution-environments` PKB doc — older GHA-vs-local framing (subsumed here; consider deprecating)
- `infrastructure` PKB doc — machines, services, named agents, repos
- `~/junior/.agents/CORE.md` — WSL-crew-container-specific orientation (the in-surface CLAUDE.md for this orchestrator surface; source of truth for the 2026-05-19 architecture change)
- [aops-2b8dd7a7] — the SSoT epic this doc is one deliverable of
- [aops-e6a80f83] — the Phase A2 task that reconciled the Cowork → WSL-crew rewrite (2026-05-20)
