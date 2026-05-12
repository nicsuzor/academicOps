# Build & Deploy

How AcademicOps plugin artifacts are built, packaged, and installed. End-users want [INSTALL.md](INSTALL.md); this doc is for developers changing the build.

## Three repos, one direction

```
nicsuzor/academicOps          nicsuzor/mem               nicsuzor/aops
┌────────────────────┐        ┌──────────────────┐        ┌──────────────┐
│ source of truth    │        │ pkb binary       │        │ dist repo    │
│ (this repo)        │        │ releases per     │        │ (artifacts + │
│                    │        │ platform         │        │  marketplace)│
└─────────┬──────────┘        └────────┬─────────┘        └──────▲───────┘
          │ checked out @ ref           │ binaries downloaded     │
          │ (public, unauth)            │ (public, unauth)        │
          └─────────────────┬───────────┘                         │
                            ▼                                     │
                 ┌──────────────────────┐                         │
                 │  uv run scripts/     │  commit + release ──────┘
                 │  build.py            │  (default GITHUB_TOKEN)
                 └──────────────────────┘
```

End-users install from `nicsuzor/aops` (the dist repo). They never touch `academicOps` directly. See `.github/aops-dist/build.yml` for the workflow definition that runs in the dist repo.

## What goes where

`scripts/build.py` reads from the source layout and writes to `dist/`. Mapping:

| Source                                              | Claude artifact                                | Gemini artifact                                |
| --------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `aops-core/skills/`, `agents/`, `commands/`, `lib/` | `dist/aops-claude/<same>/`                     | `dist/aops-gemini/<same>/` (skills mostly)     |
| `aops-core/hooks/hooks.json`                        | `dist/aops-claude/hooks/hooks.json` (verbatim) | transformed via `_generate_gemini_hooks_json`  |
| `aops-core/mcp.json.template`                       | `dist/aops-claude/.mcp.json`                   | merged into `gemini-extension.json.mcpServers` |
| `templates/aops-core.plugin.json`                   | `dist/aops-claude/.claude-plugin/plugin.json`  | (not used)                                     |
| `templates/aops-core.gemini-extension.json`         | (not used)                                     | `dist/aops-gemini/gemini-extension.json`       |
| `templates/marketplace.json`                        | `dist/.claude-plugin/marketplace.json`         | (not used)                                     |
| `GEMINI.md` + imports                               | (not used)                                     | `dist/aops-gemini/GEMINI.md` + resolved files  |

`build.py` also injects the version into every manifest, strips marketplace-only fields (`source`, `category`) from the plugin manifest (CC bug [#26555](https://github.com/anthropics/claude-code/issues/26555) — leak causes "Unrecognized keys" validation error), and packages `aops-core-v{version}.zip` for Cowork manual upload (same `aops-claude/` payload).

`aops-tools` is a separate, lightweight plugin: skills only, no hooks/agents/MCP. Built from `aops-tools/` with its own `templates/aops-tools.*` manifests.

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

`release-please` manages version bumps from conventional commits on `main`. A release PR opens automatically; merging it tags the source repo. The tag fires a `repository_dispatch` to `nicsuzor/aops` via the workflow in `.github/aops-dist/build.yml` (which is mirrored to that repo at install time). The dist repo builds artifacts and publishes a release.

Manual rebuild against a specific ref: `gh workflow run build.yml -R nicsuzor/aops -f ref=<sha> -f release_type=testing`.

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
- **Plugin shows installed but version drifted.** `~/.claude/plugins/installed_plugins.json` pins an older version than `marketplace.json` advertises. Run `claude plugin update aops-core@aops` (note: the marketplace nickname is `aops`, the plugin name is `aops-core`).
- **"Unrecognized keys" validation error on install.** `source` and `category` leaked into `dist/aops-claude/.claude-plugin/plugin.json`. `build.py` already strips these — if it recurs, check the template doesn't have them either.
- **Gemini extension fails to load.** Usually `_generate_gemini_hooks_json()` rejecting the source hooks.json. Run the build with `-v` and look for "Could not read hooks.json" or "hooks.json has no 'hooks' key".

## Do not modify

Files under `dist/` are build outputs. Edit `templates/`, `aops-core/`, or `scripts/build.py` and rerun the build. PRs that touch `dist/` will be reverted.
