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

## The plugin manifest contract (the bug we just fixed)

Claude Code's plugin loader does **not** auto-discover all components. The `.claude-plugin/plugin.json` must explicitly declare each component file via a path field:

```json
{
  "name": "aops-core",
  "version": "...",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json"
}
```

Auto-discovered (directory convention, no manifest declaration needed): `agents/`, `commands/`, `skills/`.
Manifest-declared (silently skipped if undeclared): `hooks`, `mcpServers`.

Symptom of an undeclared component: the plugin shows as `enabled` in `~/.claude/plugins/installed_plugins.json` and `claude plugin list`, but its component never runs. For hooks, the giveaway is that no `*-session-hooks.jsonl` file is written for the session. No error is surfaced — the loader just skips.

If you add a new top-level component to `aops-core/` (a new hooks file path, a new MCP config), it must be declared in `templates/aops-core.plugin.json` or it won't load.

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
# 1. Manifest contains expected component declarations
jq '{hooks, mcpServers}' dist/aops-claude/.claude-plugin/plugin.json

# 2. Hook payload is at the declared path
cat dist/aops-claude/hooks/hooks.json | jq '.hooks | keys'

# 3. Install locally and confirm hooks fire
claude plugin install ./dist/aops-claude
# then in a new Claude session, check:
ls ~/.claude/projects/$(pwd | sed 's|/|-|g')/*-session-hooks.jsonl
```

If step 3 produces no file, the manifest is missing the `hooks` declaration or the hooks router is failing — invoke `bash ~/.claude/plugins/cache/aops/aops-core/<version>/hooks/router.sh --client claude <<<'{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}'` to test the router in isolation.

## Common breakage modes

- **Hook payload present but not loading.** Manifest missing the explicit `"hooks"` declaration. Fix in `templates/aops-core.plugin.json`, never in `dist/`.
- **Plugin shows installed but version drifted.** `~/.claude/plugins/installed_plugins.json` pins an older version than `marketplace.json` advertises. Run `claude plugin update aops-core@aops` (note: the marketplace nickname is `aops`, the plugin name is `aops-core`).
- **"Unrecognized keys" validation error on install.** `source` and `category` leaked into `dist/aops-claude/.claude-plugin/plugin.json`. `build.py` already strips these — if it recurs, check the template doesn't have them either.
- **Gemini extension fails to load.** Usually `_generate_gemini_hooks_json()` rejecting the source hooks.json. Run the build with `-v` and look for "Could not read hooks.json" or "hooks.json has no 'hooks' key".

## Do not modify

Files under `dist/` are build outputs. Edit `templates/`, `aops-core/`, or `scripts/build.py` and rerun the build. PRs that touch `dist/` will be reverted.
