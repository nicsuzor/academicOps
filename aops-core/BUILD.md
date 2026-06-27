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
     dist/aops-claude/  dist/aops-tools-claude/  dist/aops-cowork/  dist/aops-gemini/  …
   • .claude-plugin/marketplace.json at the root (sources ./dist/aops-claude, …)
        │
        ▼
   end-users install from main  (marketplace nickname: academicOps)
```

There is no separate dist repo. `nicsuzor/academicOps` is both the source of truth (on `dev` / feature branches) and the published distribution: a `v*` tag fires `.github/workflows/build-extension.yml`, which builds the per-platform `dist/` artifacts and publishes the built plugin directories under `dist/` on `main` (`dist/aops-claude/`, `dist/aops-tools-claude/`, `dist/aops-cowork/`, `dist/aops-gemini/`, …) alongside a root `.claude-plugin/marketplace.json` whose sources are `./dist/aops-*`. End-users install from `main` and never build locally — see `INSTALL.md` / `README.md` (repo root) for the canonical Claude and Gemini install commands.

## What goes where

`scripts/build.py` reads from the source layout and writes to `dist/`. Mapping:

| Source                                              | Claude artifact                               | Cowork artifact                                                                     | Gemini artifact                                |
| --------------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------- |
| `aops-core/skills/`, `agents/`, `commands/`, `lib/` | `dist/aops-claude/<same>/`                    | `dist/aops-cowork/<same>/` (cowork-only blocks kept; `cowork-sync` skill present)   | `dist/aops-gemini/<same>/` (skills mostly)     |
| `aops-core/hooks/`                                  | `dist/aops-claude/hooks/` (verbatim)          | **omitted** — the cowork build ships NO hooks (aops-core supplies the shared stack) | transformed via `_generate_gemini_hooks_json`  |
| `aops-core/mcp.json.template`                       | `dist/aops-claude/.mcp.json`                  | `dist/aops-cowork/.mcp.json`                                                        | merged into `gemini-extension.json.mcpServers` |
| `templates/aops-core.plugin.json`                   | `dist/aops-claude/.claude-plugin/plugin.json` | (not used)                                                                          | (not used)                                     |
| `templates/aops-core.cowork-plugin.json`            | (not used)                                    | `dist/aops-cowork/.claude-plugin/plugin.json`                                       | (not used)                                     |
| `templates/aops-core.gemini-extension.json`         | (not used)                                    | (not used)                                                                          | `dist/aops-gemini/gemini-extension.json`       |
| `templates/marketplace.json`                        | `dist/.claude-plugin/marketplace.json`        | (not advertised; Cowork is upload-only)                                             | (not used)                                     |
| `GEMINI.md` + imports                               | (not used)                                    | (not used)                                                                          | `dist/aops-gemini/GEMINI.md` + resolved files  |

`build.py` also injects the version into every manifest, strips marketplace-only fields (`source`, `category`) from the plugin manifest (CC bug [#26555](https://github.com/anthropics/claude-code/issues/26555) — leak causes "Unrecognized keys" validation error), and packages `aops-cowork-v{version}.zip` (plus a legacy `aops-core-v{version}.zip` symlink) for Cowork manual upload.

`aops-tools` is a separate, lightweight plugin: skills only, no hooks/agents/MCP. Built from `aops-tools/` with its own `templates/aops-tools.*` manifests.

`aops-ts` is a separate, **opt-in** plugin (no skills/agents/MCP) that ships two hooks for remote/cloud sessions: a `SessionStart` hook running `tailscale up` so tailnet-only services (e.g. the PKB MCP at `*.ts.net`) resolve, and a `SessionEnd` hook that parses the session transcript and rsyncs it to a tailnet host (`AOPS_TS_SYNC_DEST`) so cloud transcripts survive container reclamation. The bring-up hook is self-contained bash with no dependency; the sync hook reuses aops-core's `transcript.py` when present and falls back to shipping the raw JSONL. Keeping it a separate plugin means joining the tailnet / shipping transcripts stays an explicit choice. Built from `aops-ts/` by `build_aops_ts` (Claude only → `dist/aops-ts-claude`) with the `templates/aops-ts.plugin.json` manifest; registered in `templates/marketplace.json` with source `./dist/aops-ts-claude`. Tailscale itself is installed by the environment's setup script, not this plugin (the authkey only exists at session runtime, so bring-up must be a hook, not setup).

## The cowork build variant

`aops-cowork` is a separate plugin built from the same `aops-core/` source tree. It is Claude-shaped (same `.claude-plugin/plugin.json` + `.mcp.json` layout) but ships **four** cowork-specific differences:

1. **Distinct plugin manifest.** Built from `templates/aops-core.cowork-plugin.json` rather than `templates/aops-core.plugin.json` — the manifest names the plugin `aops-cowork` and tunes the description/keywords. This lets Cowork installs coexist with Claude Code CLI installs without colliding.
2. **`cowork-sync` skill included.** The skill at `aops-core/skills/cowork-sync/SKILL.md` describes the PKB → native task list mirror that the Cowork harness depends on. The build strips it from every other platform's output: the helper has no analogue outside Cowork.
3. **Cowork-only blocks kept.** Source files (currently `aops-core/commands/pull.md` and `aops-core/skills/end_session/SKILL.md`) wrap Cowork-specific instructions in `<!-- cowork:only --> ... <!-- /cowork:only -->`. The cowork build strips only the marker lines (keeping the wrapped content); every other build strips both the markers and the content. The marker handling lives in `_process_cowork_markers` in `scripts/build.py`.
4. **No hooks bundled.** The cowork build ships **no `hooks/` directory and no `hooks.json`** — the `if platform != "cowork"` guard in section 2 of `build_aops_core` skips the hook copy, and `generate_aops_core_pyproject(version, "cowork")` drops `hooks` from the hatch wheel packages (so `uv sync --frozen` doesn't reference a missing dir). Installing `aops-core` into Cowork from the `nicsuzor/aops` main `dist` marketplace makes Cowork fire the standard aops-core hook stack (empirically confirmed — see `mem-fe29111a` / task `aops-04075740`), so one shared hook stack serves both surfaces. Bundling hooks here too would register the router a second time and double-fire every lifecycle hook. aops-cowork is therefore an **additive, skills-only** layer on top of aops-core.

The cowork build is invoked from `main()` as `build_aops_core(aops_root, dist_root, aca_data_path, "cowork", version)` alongside `claude`/`gemini`/`antigravity`. Output goes to `dist/aops-cowork/`; `package_artifacts` then zips that directory into `dist/aops-cowork-v{version}.zip` for manual upload. The legacy `aops-core-v{version}.zip` filename is kept as a symlink for backward compatibility with existing download URLs.

To add a new cowork-only behaviour, choose the smallest surface that fits:

- **A whole skill that only makes sense on Cowork** → drop it under `aops-core/skills/<name>/` and add an exclusion in `build_aops_core` mirroring the `cowork-sync` line (or, if it's a per-skill check, factor that out).
- **A few paragraphs inside an existing skill or command** → wrap them in `<!-- cowork:only -->` markers and they will be auto-included by the cowork build and stripped from every other.

## The plugin manifest contract

Claude Code auto-discovers components from conventional directories — `agents/`, `commands/`, `skills/`, and `hooks/hooks.json`. None of these need to be declared in `.claude-plugin/plugin.json`. `mcpServers` is the exception: it does need an explicit pointer (`"mcpServers": "./.mcp.json"`) because MCP config doesn't live at a fixed conventional path.

Verify what CC actually loaded with `/hooks` inside an interactive Claude session — registered hooks appear under their plugin source, e.g. `Plugin Hooks (aops-core@academicOps)`. If the plugin shows enabled in `~/.claude/plugins/installed_plugins.json` but `/hooks` doesn't list its events, the loader couldn't read the hooks file — usually a JSON syntax error, missing event name, or unresolvable `${CLAUDE_PLUGIN_ROOT}` in a command path.

Symptom of a hook that's _registered but not firing_: no `*-session-hooks.jsonl` file is written for the session. Most common cause is the router or its underlying Python crashing before it writes the log; invoke the router manually with a synthetic event to reproduce:

```bash
echo '{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}' \
  | bash ~/.claude/plugins/cache/academicOps/aops-core/<version>/hooks/router.sh --client claude
```

If that succeeds but a real session produces no hook log, the cause is in how the session is being spawned (not all session kinds run SessionStart — programmatically-spawned subagents and isolated worktree sessions may not).

## The Gemini parallel

Gemini uses a completely separate manifest (`templates/aops-core.gemini-extension.json` → `dist/aops-gemini/gemini-extension.json`) and auto-discovers hooks from `<extension>/hooks/hooks.json` regardless of what the manifest declares. `_generate_gemini_hooks_json()` in `build.py` rewrites the Claude-format `hooks.json` into Gemini's expected shape (different event names, different command-spec format).

**Changes to `templates/aops-core.plugin.json` do not affect Gemini.** The two platforms have separate templates and separate transforms. If you touch one, validate the other still builds:

```bash
uv run scripts/build.py --platform claude
uv run scripts/build.py --platform gemini
```

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
- **Gemini extension fails to load.** Usually `_generate_gemini_hooks_json()` rejecting the source hooks.json. Look for "Could not read hooks.json" or "hooks.json has no 'hooks' key" in the build output.

## Do not modify

Files under `dist/` are build outputs. Edit `templates/`, `aops-core/`, or `scripts/build.py` and rerun the build. PRs that touch `dist/` will be reverted.
