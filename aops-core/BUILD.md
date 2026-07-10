# Build & Deploy

How AcademicOps plugin artifacts are built, packaged, and installed. End-users want `INSTALL.md` (repo root); this doc is for developers changing the build.

## Two repos, self-publishing to main

```
nicsuzor/academicOps  (source of truth: dev / feature branches)
        │   uv run scripts/build.py        nicsuzor/mem
        │   ───────────────────────  ◄──── pkb binary (per platform)
        ▼
   dist/   (local build artifacts)
        │
        │   v* tag → .github/workflows/build-extension.yml
        ▼
nicsuzor/academicOps @ main   (published distribution channel)
   • built plugin dirs published under dist/:
     dist/aops-claude/  dist/aops-tools-claude/  dist/aops-cowork/  dist/aops-antigravity/  …
   • .claude-plugin/marketplace.json at the root (sources ./dist/aops-claude, …)
        │
        ▼
   end-users install from main  (marketplace nickname: academicOps)
```

There is no separate dist repo. `nicsuzor/academicOps` is both the source of truth (on `dev` / feature branches) and the published distribution: a `v*` tag fires `.github/workflows/build-extension.yml`, which builds the per-platform `dist/` artifacts and publishes the built plugin directories under `dist/` on `main` (`dist/aops-claude/`, `dist/aops-tools-claude/`, `dist/aops-cowork/`, `dist/aops-antigravity/`, …) alongside a root `.claude-plugin/marketplace.json` whose sources are `./dist/aops-*`. End-users install from `main` and never build locally — see `INSTALL.md` / `README.md` (repo root) for the canonical install commands.

## What goes where

`scripts/build.py` reads from the source layout and writes to `dist/`. Mapping:

| Source                                              | Claude artifact                               | Cowork artifact                                                                                                                                                                                                                                                                   |
| --------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aops-core/skills/`, `agents/`, `commands/`, `lib/` | `dist/aops-claude/<same>/`                    | **NOT copied** — except individual files carrying `<!-- cowork:only -->` markers (currently `aops-pkb/skills/end_session/SKILL.md` and `aops-pkb/commands/pull.md`, scanned across both plugin trees — `aops-core`, `aops-pkb`), copied singly with markers stripped/content kept |
| `aops-cowork/` (real package)                       | (not used)                                    | `dist/aops-cowork/skills/<same>/` — the entirety of aops-cowork's shipped skill content (e.g. `cowork-sync`)                                                                                                                                                                      |
| `aops-core/hooks/`                                  | `dist/aops-claude/hooks/` (verbatim)          | **omitted** — the cowork build ships NO hooks (aops-core supplies the shared stack)                                                                                                                                                                                               |
| `aops-core/mcp.json.template`                       | `dist/aops-claude/.mcp.json`                  | `dist/aops-cowork/.mcp.json` (launcher: `scripts/run-mcp.sh` + `scripts/ensure-path.sh` are copied in from `aops-pkb/scripts/` — the sole tracked copy, see `aops-pkb` section below — not from anything in `aops-core/`)                                                         |
| `templates/aops-core.plugin.json`                   | `dist/aops-claude/.claude-plugin/plugin.json` | (not used)                                                                                                                                                                                                                                                                        |
| `aops-cowork/.claude-plugin/plugin.json` (tracked)  | (not used)                                    | `dist/aops-cowork/.claude-plugin/plugin.json`                                                                                                                                                                                                                                     |
| —                                                   | —                                             | aops-cowork ships **no** `pyproject.toml`/`uv.lock` — no Python deps of its own (no `lib/`, no hooks)                                                                                                                                                                             |
| `templates/marketplace.json`                        | `dist/.claude-plugin/marketplace.json`        | `dist/.claude-plugin/marketplace.json` — `aops-cowork` entry, source `./dist/aops-cowork`, installed alongside `aops-core`                                                                                                                                                        |

`build.py` also injects the version into every manifest, strips marketplace-only fields (`source`, `category`) from the plugin manifest (CC bug [#26555](https://github.com/anthropics/claude-code/issues/26555) — leak causes "Unrecognized keys" validation error), and packages `aops-cowork-v{version}.zip` (plus a legacy `aops-core-v{version}.zip` symlink) for Cowork manual upload.

`aops-tools` is a separate, lightweight plugin: skills only, no hooks/agents/MCP. Built from `aops-tools/` with its own `templates/aops-tools.*` manifests.

`aops-ts` is a separate, **opt-in** plugin (no skills/agents/MCP) that ships two hooks for remote/cloud sessions: a `SessionStart` hook running `tailscale up` so tailnet-only services (e.g. the PKB MCP at `*.ts.net`) resolve, and a `SessionEnd` hook that parses the session transcript and rsyncs it to a tailnet host (`AOPS_TS_SYNC_DEST`) so cloud transcripts survive container reclamation. The bring-up hook is self-contained bash with no dependency; the sync hook reuses aops-core's `transcript.py` when present and falls back to shipping the raw JSONL. Keeping it a separate plugin means joining the tailnet / shipping transcripts stays an explicit choice. Built from `aops-ts/` by `build_aops_ts` (Claude only → `dist/aops-ts-claude`) with the `templates/aops-ts.plugin.json` manifest; registered in `templates/marketplace.json` with source `./dist/aops-ts-claude`. Tailscale itself is installed by the environment's setup script, not this plugin (the authkey only exists at session runtime, so bring-up must be a hook, not setup).

`aops-pkb` is a separate, standalone plugin (agents + commands + skills + its own `pkb` MCP server registration, but **no hooks** — the module operates outside the agent loop, see PKB task `aops-b225ec53`). It ships the task/work-unit module extracted from `aops-core`: capture (`/q`), strategic planning + decomposition (the `planner` skill), the task-lifecycle spine (`/pull`, `/dispatch`), acceptance (`/verify` + `strategic-review`'s four-agent sign-off — `james`, `rbg`, `pauli`, `marsha`), PKB curation (`/remember`, `/learn`, `/maintain`), and session lifecycle (`/daily`, `/dump`, `/end_session` — moved here from the short-lived `aops-interactive` plugin per ruling A10, task `aops-7ea63b63`: these skills are bound up with the PKB, not with the head personality). Because it registers its own `pkb` MCP server under a distinct plugin name, its 4 moved agents (`james`/`rbg`/`pauli`/`marsha`) and the `task-lifecycle` skill were rewritten at the source level to the `mcp__plugin_aops-pkb_pkb__*` tool-name prefix (not a build-time rewrite, unlike aops-cowork's — aops-pkb is a standalone package, not an aops-core overlay). The other moved skill-body files (`planner`, `remember`'s procedures/SKILL.md, etc.) still reference the bare `mcp__pkb__*` short form in prose — the repo's pre-existing multi-form PKB-prefix tolerance (`aops-core/lib/tool_categories.py`'s `_PKB_PREFIX_VARIANTS`) — left as-is rather than over-fitting a rewrite beyond the load-bearing frontmatter tool grants. `rbg`/`marsha`'s axiom imports are co-shipped the same way `build_aops_core` does it (`build_aops_pkb` runs the same anti-drift guards, `_assert_plugin_imports_resolve` / `_assert_no_axiom_decoys`). `end_session/SKILL.md` still carries the `<!-- cowork:only -->` marker it had in `aops-core`, so the cowork build's marker scan walks this tree too (see the cowork section below). Built from `aops-pkb/` by `build_aops_pkb` (Claude and Antigravity → `dist/aops-pkb-claude`, `dist/aops-pkb-antigravity`) with its own **tracked** `aops-pkb/.claude-plugin/plugin.json` (aops-cowork-style, not template-fabricated) and `aops-pkb/mcp.json.template`; registered in `templates/marketplace.json` with source `./dist/aops-pkb-claude`. `aops-pkb/scripts/run-mcp.sh` is also the sole tracked copy of the pkb stdio MCP launcher: the antigravity build ships it via its normal full-tree copy, and the cowork build of `aops-core` (above) copies it in at build time rather than keeping a second copy under `aops-core/scripts/`. `ensure-path.sh` is the one exception to the single-copy rule — `aops-core/scripts/ensure-path.sh` is a deliberately-maintained second tracked copy, because `aops-core/hooks/router.sh` sources it for PATH bootstrap and `aops-core` must install standalone without a sibling `aops-pkb` present.

`aops-core` also ships the `ida` agent, the shared head ROLE charter it `@`-imports (`.agents/charter/head-role-charter.md`, co-shipped from `specs/interactive-experience/head-role-charter.md` the same way axioms are co-shipped), and the `narrative-digest` skill. These lived briefly in a separate `aops-interactive` plugin (epic `aops-c70490f4`, PR #2115, 2026-07-05) before that plugin was dissolved pre-ship (ruling A10, never installed anywhere, task `aops-7ea63b63`, 2026-07-06): hooks don't work across plugins, and the head personality that the `ida` honesty-at-Stop gate binds to must live where the hooks are. `ida` does not own the PKB interface — it consumes `aops-pkb`'s, so its PKB tool grants stay the `mcp__plugin_aops-pkb_pkb__*` prefix unchanged by the move. The `junior` personality skin was **not** moved here — ruling A8 makes junior user-level, canonical in Nic's brain repo (`~/brain/.agents/`), never plugin-shipped.

## The cowork build variant

`aops-cowork` is a **real, tracked package** (`aops-cowork/`) and a genuinely **additive, skills-only** layer on top of `aops-core` — it is not a manifest fabricated from `templates/`, and (as of aops-10afe69d) it is not a second copy of the aops-core tree either. Users install `aops-core` (from the main dist marketplace) AND `aops-cowork` side by side; aops-core supplies every shared agent/skill/command/lib file and the one shared hook stack, so aops-cowork ships only what's genuinely Cowork-specific. It is Claude-shaped (same `.claude-plugin/plugin.json` + `.mcp.json` layout) but differs in **four** ways:

1. **Distinct, tracked plugin manifest.** Sourced from `aops-cowork/.claude-plugin/plugin.json` (a committed file), not a template — the manifest names the plugin `aops-cowork` and tunes the description/keywords. This lets Cowork installs coexist with Claude Code CLI installs without colliding.
2. **`cowork-sync` skill included.** The skill at `aops-cowork/skills/cowork-sync/SKILL.md` lives ONLY in the cowork package and is overlaid onto the build. It describes the PKB → native task list mirror that the Cowork harness depends on.
3. **Cowork-only marker files, and ONLY those files.** Source files (currently `aops-pkb/skills/end_session/SKILL.md` — moved from `aops-core` via the short-lived `aops-interactive` plugin, aops-cf3fb2f0 then aops-7ea63b63 — and `aops-pkb/commands/pull.md` — inherited from aops-core in the aops-b225ec53 extraction) wrap a short Cowork-specific paragraph in `<!-- cowork:only --> ... <!-- /cowork:only -->`. The cowork build scans the `aops-core/` tree AND the `aops-pkb/` tree (aops-pkb has no cowork build of its own, so this is the only place its marker content ships) for `.md` files containing a real (regex-matched, not just string-contains) marker block and copies ONLY those files — nothing else from any tree is copied. The copied files get the markers stripped and the content kept; every other build of aops-core (claude/antigravity) gets the full aops-core tree with both the markers AND the content stripped, and aops-pkb's own (claude-only) build strips the block the same way. The marker handling lives in `_process_cowork_markers` / `_COWORK_BLOCK_RE` in `scripts/build.py`.
4. **No hooks, no Python deps.** The cowork build ships **no `hooks/` directory, no `hooks.json`, and no `pyproject.toml`/`uv.lock`** — it has no `lib/` or hooks of its own to declare deps for. Installing `aops-core` into Cowork from the `nicsuzor/aops` main `dist` marketplace makes Cowork fire the standard aops-core hook stack (empirically confirmed — see `mem-fe29111a` / task `aops-04075740`), so one shared hook stack serves both surfaces. Bundling hooks here too would register the router a second time and double-fire every lifecycle hook. The only non-Python file aops-cowork needs outside its skill is the pkb MCP launcher (`scripts/run-mcp.sh` + `scripts/ensure-path.sh`, copied individually from `aops-pkb/scripts/` — see the `.mcp.json` row above).

A full `dist/aops-cowork/` build is therefore just: `.claude-plugin/plugin.json`, `.mcp.json`, `scripts/{run-mcp.sh,ensure-path.sh}`, `commands/pull.md`, `skills/end_session/SKILL.md`, `skills/cowork-sync/`. Compare against `dist/aops-claude/`, which ships the full framework (hundreds of files) — the gap is the point.

The cowork build is invoked from `main()` as `build_aops_core(aops_root, dist_root, aca_data_path, "cowork", version)` alongside `claude`/`antigravity`. Output goes to `dist/aops-cowork/`; `package_artifacts` then zips that directory into `dist/aops-cowork-v{version}.zip` for manual upload. The legacy `aops-core-v{version}.zip` filename is kept as a symlink for backward compatibility with existing download URLs.

To add a new cowork-only behaviour, choose the smallest surface that fits:

- **A whole skill that only makes sense on Cowork** → drop it under `aops-cowork/skills/<name>/`. The cowork build overlays everything in the package's `skills/` automatically — no exclusion needed.
- **A few paragraphs inside an existing shared skill or command** → wrap them in `<!-- cowork:only -->` markers. The cowork build auto-discovers the file (by scanning for a real marker block, not by an allowlist) and ships ONLY that file, stripped of markers; every other build strips the markers and the wrapped content. Don't add a whole new shared file for this — the marker mechanism exists precisely so one inline paragraph doesn't force shipping the rest of that file's containing directory.

**Known gap (not addressed by aops-10afe69d):** `aops-core` and `aops-cowork` still each register their own `pkb` MCP server under different plugin-namespaced tool names (`mcp__plugin_aops-core_pkb__*` vs `mcp__plugin_aops-cowork_pkb__*`) — see `aops-6c39380e`. Separately, `aops-cowork/skills/cowork-sync/SKILL.md`'s own PKB tool references are unprefixed (`mcp__pkb__...`), which doesn't resolve to either registered namespace; this predates aops-10afe69d and wasn't introduced by the skills-only trim.

## The plugin manifest contract

Claude Code auto-discovers components from conventional directories — `agents/`, `commands/`, `skills/`, and `hooks/hooks.json`. None of these need to be declared in `.claude-plugin/plugin.json`. `mcpServers` is the exception: it does need an explicit pointer (`"mcpServers": "./.mcp.json"`) because MCP config doesn't live at a fixed conventional path.

Verify what CC actually loaded with `/hooks` inside an interactive Claude session — registered hooks appear under their plugin source, e.g. `Plugin Hooks (aops-core@academicOps)`. If the plugin shows enabled in `~/.claude/plugins/installed_plugins.json` but `/hooks` doesn't list its events, the loader couldn't read the hooks file — usually a JSON syntax error, missing event name, or unresolvable `${CLAUDE_PLUGIN_ROOT}` in a command path.

Symptom of a hook that's _registered but not firing_: no `*-session-hooks.jsonl` file is written for the session. Most common cause is the router or its underlying Python crashing before it writes the log; invoke the router manually with a synthetic event to reproduce:

```bash
echo '{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}' \
  | bash ~/.claude/plugins/cache/academicOps/aops-core/<version>/hooks/router.sh --client claude
```

If that succeeds but a real session produces no hook log, the cause is in how the session is being spawned (not all session kinds run SessionStart — programmatically-spawned subagents and isolated worktree sessions may not).

## Release path

`release-please` manages version bumps from conventional commits; merging the release PR creates the stable `vX.Y.Z` tag. The tag push fires `.github/workflows/build-extension.yml` **in this repo** — there is no `repository_dispatch` and no separate dist repo (the old `.github/aops-dist/build.yml` reference workflow was deleted in commit 65d77adf, 2026-06-04). The workflow builds the per-platform `dist/` artifacts, publishes the built plugin directories under `dist/` on `main` (the install channel), and uploads the release archives as GitHub Release assets.

Pre-release tags (`vX.Y.Z-rc.N`, `-dev.N`, …) take the same workflow but **skip the `main` publish** — they ship only as `--prerelease` GitHub Releases, so testers install them by tag while `main` (the stable channel) is left untouched.

Manual rebuild against a specific ref: push a pre-release tag at that commit — e.g. `git tag v<next>-rc.1 <sha> && git push origin v<next>-rc.1` — which triggers `build-extension.yml` against the tagged commit.

## Local verification

After running `uv run scripts/build.py`:

```bash
# 1. Manifest validates and strips marketplace leakage
jq '{name, version, mcpServers}' dist/aops-claude/.claude-plugin/plugin.json
jq 'has("source"), has("category")' dist/aops-claude/.claude-plugin/plugin.json  # both false

# 2. Hooks payload structure
jq '.hooks | keys' dist/aops-claude/hooks/hooks.json

# 3. Install locally, then in a fresh interactive `claude` session run `/hooks`
claude plugin install ./dist/aops-claude
# in the new session, `/hooks` should list `Plugin Hooks (aops-core@academicOps)`
# and a session-hooks.jsonl should appear under ~/.claude/projects/<slug>/
```

If `/hooks` shows the plugin's events but no `*-session-hooks.jsonl` is written, the router is crashing. Reproduce in isolation:

```bash
echo '{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}' \
  | bash ~/.claude/plugins/cache/academicOps/aops-core/<version>/hooks/router.sh --client claude
```

## Common breakage modes

- **Plugin enabled but `/hooks` doesn't list its events.** CC couldn't read `hooks/hooks.json` — usually a JSON syntax error or an unresolvable command path. Inspect with `python3 -c "import json; json.load(open('hooks/hooks.json'))"`.
- **`/hooks` lists events but no session-hooks log is written.** Router crashes before logging. Run the router manually with a synthetic event (see above).
- **Subagent / isolated-worktree sessions don't run SessionStart.** Programmatically-spawned Claude sessions (Agent tool with `isolation: worktree`, FleetView-launched sessions) may not invoke SessionStart hooks the way the interactive `claude` CLI does. Symptom: hooks fire fine for normal `claude` sessions in the same project, but a subagent in the same repo has no env file written. This is a session-kind issue, not a plugin manifest issue.
- **Plugin shows installed but version drifted.** `~/.claude/plugins/installed_plugins.json` pins an older version than `marketplace.json` advertises. Run `claude plugin update aops-core@academicOps` (note: the marketplace nickname is `academicOps`, the plugin name is `aops-core`).
- **"Unrecognized keys" validation error on install.** `source` and `category` leaked into `dist/aops-claude/.claude-plugin/plugin.json`. `build.py` already strips these — if it recurs, check the template doesn't have them either.

## Do not modify

Files under `dist/` are build outputs. Edit `templates/`, `aops-core/`, or `scripts/build.py` and rerun the build. PRs that touch `dist/` will be reverted.
