---
type: spec
title: Build, Package & Install Pipeline
status: ready
tags: [framework, build, install, release, makefile, plugins, agy, cowork]
---

# Build, Package & Install Pipeline

How AcademicOps plugin artifacts are built from source, packaged per platform, installed
(both by end-users and by a developer's own `make` targets), cleaned up, and released.
Audience: a dev or auditor extending or auditing this repo's build/install tooling itself.
Researchers who just want to _install_ the framework want [`INSTALL.md`](../INSTALL.md)
(repo root) or [`README.md`](../README.md); contributors doing dev setup want
[`CONTRIBUTING.md`](../CONTRIBUTING.md), which points here for design detail.

> **Naming note.** The main plugin was formerly two plugins — `aops-core` (the large
> Claude plugin) and a separate `aops` task module — during a transitional period. They
> have since been **consolidated into a single `aops` plugin**. `aops-core` no longer
> exists as a plugin or a source directory; every reference below is to the current
> layout. The PKB MCP server is registered under the server name **`services`** (tools:
> `mcp__services__pkb__*`). The Gemini CLI **extension** surface (the old
> `gemini-extension.json`) has been dropped; only the Antigravity CLI (`agy`) build
> remains as a non-Claude target.

## 1. Shape of the pipeline (source → dist → install)

```
nicsuzor/academicOps @ dev   (source of truth: dev / feature branches)
        │   uv run scripts/build.py        nicsuzor/mem
        │   ───────────────────────  ◄──── pkb binary (per platform, runtime dep)
        ▼
   dist/   (local build artifacts: dist/aops-claude, dist/aops-antigravity, …)
        │
        │   vX.Y.Z tag → .github/workflows/build-extension.yml
        ▼
nicsuzor/academicOps @ dist   (published distribution channel — orphan branch)
   • built plugin dirs published at the branch ROOT:
     aops-claude/  aops-tools-claude/  aops-ts-claude/  aops-antigravity/  …
   • .claude-plugin/marketplace.json at the root (sources ./aops-claude, …)
        │
        ▼
   end-users install from dist  (marketplace nickname: academicOps)
```

There is no separate dist repo. `nicsuzor/academicOps` is both the source of truth (on
`dev` / feature branches) and the published distribution: a `vX.Y.Z` tag fires
`.github/workflows/build-extension.yml`, which builds the per-platform `dist/` artifacts
and fast-forward-publishes the built plugin directories to the ROOT of the orphan
**`dist`** branch (`aops-claude/`, `aops-tools-claude/`, `aops-ts-claude/`,
`aops-antigravity/`, …) alongside a root `.claude-plugin/marketplace.json` whose sources
are `./aops-*`. (Older publishes nested these one level under a `dist/` subdirectory —
`dist:dist/aops-claude` — that layout is superseded; the publish step removes the stale
subdirectory on first run against a branch still carrying it.) End-users install from
`dist` and never build locally — see `INSTALL.md` / `README.md` for the canonical install
commands.

`academicOps`'s `main` branch is a **deprecated** stale orphan from the pre-migration
topology (pending deletion — full branch-topology decision record in
[`specs/workflows/releasing.md`](workflows/releasing.md) §2); nothing in this pipeline
reads from or writes to it today. If you see `main` referenced as the install channel
anywhere (including stale Makefile comments), that reference is stale — the live channel
is `dist`.

## 2. What goes where (`scripts/build.py`)

`scripts/build.py` is a **simple, generic** assembler: one function, `build_plugin(name,
src_dir, dist_root, version)`, run once per plugin in the default set
`["aops", "aops-tools", "aops-ts"]` (override with `--plugins`). For each plugin it builds
the two client formats — `claude` and `antigravity` — except `aops-ts`, which is
Claude-only. Output goes to `dist/<plugin>-<client>` and each dir is also tarred to
`dist/<plugin>-<client>.tar.gz`:

| Plugin       | Claude build             | Antigravity build             |
| ------------ | ------------------------ | ----------------------------- |
| `aops`       | `dist/aops-claude`       | `dist/aops-antigravity`       |
| `aops-tools` | `dist/aops-tools-claude` | `dist/aops-tools-antigravity` |
| `aops-ts`    | `dist/aops-ts-claude`    | _(skipped — Claude-only)_     |

The core of `build_plugin` is an `os.walk` of the plugin's source tree that copies files
verbatim into the dist dir (skipping `__pycache__`, `.venv`, `.git`, and the other
`EXCLUDES`), with four transforms layered on top:

1. **`*.template.json` → concrete manifest.** Each template merges a `__base__` object
   with the active client's section. The stem picks the destination:
   - `<plugin>.template.json` → the plugin manifest, with `version` injected:
     `.claude-plugin/plugin.json` (claude) or `plugin.json` (antigravity).
   - `mcp.template.json` → `.mcp.json` (claude) or `mcp_config.json` (antigravity). For
     antigravity, build.py rewrites the `services` server's `args` to
     `["-c", "~/.gemini/config/plugins/<plugin>/scripts/run-mcp.sh"]` — a permanent
     workaround for antigravity-cli#390 (agy doesn't resolve `${extensionPath}` and runs
     MCP servers from the workspace cwd, so a relative path fails). This bakes the fix in
     at **build** time; there is no post-install `sed`.
   - `hooks.template.json` → `hooks/hooks.json` (claude — Claude Code auto-discovers hooks
     ONLY at `<plugin_root>/hooks/hooks.json`) or `hooks.json` (antigravity — root-level,
     with the `${AGY_PLUGIN_ROOT}/hooks/router.py` command quotes stripped because agy
     execs via argv).
2. **`commands/*.md` → `skills/cmd-<name>/SKILL.md` (antigravity only).** agy has no
   slash-command surface, so each command is republished as a skill with its frontmatter
   `type: command` rewritten to `type: skill`. Claude keeps `commands/*.md` verbatim.
3. **Always-on axioms.** `load_axioms(<plugin>/axioms)` collects the `trigger: always_on`
   rule files. For antigravity they're copied into `rules/*.md` (agy's canonical
   merged-rules location); for claude they're written to `axioms.jsonl` (Claude Code has
   no plugin-level rules folder, so `make install-dev` runs `scripts/install_automode.py`
   to merge them into `~/.claude/settings.json` separately).
4. **Manifest hygiene.** The version is stamped into every plugin manifest; lingering
   legacy per-client files (`*.claude.json`, `*.agy.json`, etc.) are skipped; empty dirs
   are pruned.

After the plugins are built, `main()` generates **two marketplaces** from
`templates/marketplace.json`:

- `generate_local_marketplace` → `dist/.claude-plugin/marketplace.json`, named **`aops`**
  (not `academicOps`) so `make dev` installs land in their own marketplace namespace,
  with sources rewritten `./dist/aops-*` → `./aops-*` (the marketplace root is `dist/`,
  so a co-located `./aops-claude` resolves to `dist/aops-claude`). Filtered to plugins
  that were actually built.
- `generate_production_marketplace` → `dist/marketplace-production.json`, the file the
  release workflow copies to the `dist` branch root, with the same `./dist/aops-*` →
  `./aops-*` rewrite.

`templates/marketplace.json` (name `academicOps`) is the source of truth for the shipped
plugin set: `aops` → `./dist/aops-claude`, `aops-tools` → `./dist/aops-tools-claude`,
`aops-ts` → `./dist/aops-ts-claude`. The `*-antigravity` builds are **not** in the
marketplace (antigravity installs go through `agy plugin install`, §5.5); Cowork gets its
own generated marketplace at `dist/cowork` (§3).

After the marketplaces, `main()` runs `generate_cowork_dist` → `dist/cowork`, the
self-contained Cowork channel (directory marketplace `academicOps-cowork` + per-plugin
upload zips) — see §3.

Version comes from `get_project_version`: the top-level `pyproject.toml` `version`, with
git short-SHA / `.dirty` metadata appended for local builds.

**Plugin identities today:**

- **`aops`** — the main, standalone plugin: agents + commands + skills + hooks + its own
  `services` (PKB) MCP registration + axioms. Its manifest/MCP/hooks templates live in
  `aops/templates/` (`aops.template.json`, `mcp.template.json`, `hooks.template.json`).
- **`aops-tools`** — a separate lightweight plugin: skills only, no hooks/agents/MCP
  (replaceable technology-specific skills — dbt, Streamlit, Python plotting/stats). Built
  for both `claude` and `antigravity`.
- **`aops-ts`** — a separate, **opt-in**, Claude-only plugin that ships two hooks for
  remote/cloud sessions: a `SessionStart` hook running `tailscale up` so tailnet-only
  services (e.g. the PKB MCP at `*.ts.net`) resolve, and a `SessionEnd` hook that parses
  the session transcript and rsyncs it to a tailnet host (`AOPS_TS_SYNC_DEST`) so cloud
  transcripts survive container reclamation. The bring-up hook is self-contained bash; the
  sync hook reuses the `aops` plugin's `transcript.py` when present and falls back to
  shipping raw JSONL. **No `make` target installs it** — install by hand:
  `claude plugin install aops-ts@academicOps`.
- **`aops-cowork`** — a Cowork-specific package; see §3.

## 3. The cowork channel (`dist/cowork`)

Cowork ships the **same two plugins as Claude Code — `aops` + `aops-tools`, in their
Claude-shaped builds** (decision 2026-07-16); there is no separate cowork plugin build.
What is cowork-specific is the _channel_, not the content: Cowork has no marketplace
mechanism on personal accounts, and its `RemotePluginManager.syncPlugins` nukes
github-source marketplaces on every restart (cf. claude-code issues #38429/#40600), so a
plain `aops@academicOps` (github-source) install never survives in Cowork. The install
channel must therefore be a **local directory marketplace**.

`generate_cowork_dist` in `scripts/build.py` assembles that channel on every build:

```
dist/cowork/.claude-plugin/marketplace.json   # marketplace name: academicOps-cowork
dist/cowork/aops/                             # verbatim copy of dist/aops-claude
dist/cowork/aops-tools/                       # verbatim copy of dist/aops-tools-claude
dist/cowork/aops-v{VERSION}.zip               # manual-upload fallback
dist/cowork/aops-tools-v{VERSION}.zip         # manual-upload fallback
```

The marketplace is generated from `templates/marketplace.json` filtered to
`aops`/`aops-tools`, renamed `academicOps-cowork`, with sources rewritten to the
co-located `./aops` / `./aops-tools` copies. The per-plugin zips (plugin dir at the zip
root) serve the manual path — Claude desktop → **Cowork → Customize → Add plugins →
Upload a file** — for accounts where even a local marketplace isn't usable.

**Cowork-only content markers.** Skill/command sources may wrap Cowork-specific
instructions in `<!-- cowork:only --> … <!-- /cowork:only -->` (today:
`aops/skills/handover/SKILL.md` §1.5, the native-task-list reconcile step).
`build_plugin` strips both the markers and the content from every claude/antigravity
`.md`; `generate_cowork_dist` then re-applies the marker-carrying source files into the
cowork copies with the content **kept** and the markers dropped. (This enforcement
existed in the old `build_aops_core`, was lost in the generic-builder rewrite — blocks
shipped verbatim everywhere as inert comments — and was restored 2026-07-16.)

> **Legacy note.** The earlier design shipped a separate skills-only `aops-cowork` plugin
> (source still tracked at `aops-cowork/`, containing the `cowork-sync` skill) with a
> local-dev rename `aops-coworklocal`. That build path was defunct for a long period and
> has been **retired** in favour of shipping the real `aops`/`aops-tools` builds through
> `dist/cowork`. `install-cowork`/`uninstall-cowork`/`clean-local` still tear down a
> lingering `aops-coworklocal@academicOps-cowork` install on sight. Folding the
> `cowork-sync` skill into `aops` (or re-adding `aops-cowork` to the cowork marketplace)
> is a separate decision — today `aops-cowork/` is source-only and unshipped.

## 4. The plugin manifest contract

Claude Code auto-discovers components from conventional directories — `agents/`,
`commands/`, `skills/`, and `hooks/hooks.json`. None of these need to be declared in
`.claude-plugin/plugin.json`. `mcpServers` is the exception: it does need an explicit
pointer (`"mcpServers": "./.mcp.json"`) because MCP config doesn't live at a fixed
conventional path.

Verify what CC actually loaded with `/hooks` inside an interactive Claude session —
registered hooks appear under their plugin source, e.g.
`Plugin Hooks (aops@academicOps)`. If the plugin shows enabled in
`~/.claude/plugins/installed_plugins.json` but `/hooks` doesn't list its events, the
loader couldn't read the hooks file — usually a JSON syntax error, missing event name, or
unresolvable `${CLAUDE_PLUGIN_ROOT}` in a command path.

Symptom of a hook that's _registered but not firing_: no `*-session-hooks.jsonl` file is
written for the session. Most common cause is the router or its underlying Python crashing
before it writes the log; invoke the router manually with a synthetic event to reproduce:

```bash
echo '{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}' \
  | bash ~/.claude/plugins/cache/academicOps/aops/<version>/hooks/router.sh --client claude
```

If that succeeds but a real session produces no hook log, the cause is in how the session
is being spawned (not all session kinds run SessionStart — programmatically-spawned
subagents and isolated worktree sessions may not).

## 5. Local install & dev loop (the Makefile)

The root `Makefile` is the single entry point for turning source into installed plugins on
a developer's own machine, across every distribution surface: Claude Code CLI, Cowork,
Antigravity CLI (`agy`), and Windows-side Claude (from WSL). It wraps `scripts/build.py`
(build) and drives the `claude` / `agy` CLIs directly for plugin lifecycle
(install/uninstall, marketplace add/remove). **There is no `scripts/install.py`** — it was
retired; every install path below is a direct `claude`/`agy` CLI call from a `make`
target.

### 5.1 Two install modes: dev vs release

|                             | `make dev` / `install-dev`                                              | `make install`                                                 |
| --------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Source**                  | This checkout's `dist/` (freshly built by `build-dev`)                  | The live `dist` branch on GitHub (`nicsuzor/academicOps@dist`) |
| **Claude marketplace name** | `aops` (local-dir source, from build.py's `generate_local_marketplace`) | `academicOps`                                                  |
| **Claude plugin ref**       | `aops@aops`                                                             | `aops@academicOps`                                             |
| **Purpose**                 | Iterating on source and testing the result immediately                  | Installing/updating the published framework like any user      |
| **First step run**          | `build-dev` (always rebuilds)                                           | `clean-local` (tears down any dev install first, see §5.3)     |

The two are namespaced under different marketplace names specifically so one can never
silently shadow the other — `claude plugin marketplace add` is a no-op when a name already
exists (it will **not** re-point an existing source to a new one), so both `install-dev`
and `install-claude` `remove` the marketplace before re-adding it. Without this a stale dev
override could survive a later `make install` and the "live" install would silently keep
serving the local build.

`make dev` chains `build-dev` → `install-dev` → `install-hooks` (pre-commit).

### 5.2 Is a dev install "live"? — it's copies, everywhere

With `install.py` retired, there is **no live-symlink dev path**. Both Claude Code and agy
install by **copying** the built `dist/` content into their plugin caches, so a source edit
is never picked up automatically:

| Surface             | Mechanism                                                                                                                                                | To see an edit                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Claude Code CLI** | `claude plugin marketplace add dist/` (dir source) + `claude plugin install aops@aops` — **copies** into `~/.claude/plugins/cache/aops/aops/<version>/`. | Re-run `make install-dev` (rebuild `dist/`, then uninstall + reinstall). |
| **Antigravity/agy** | `agy plugin install dist/aops-antigravity` — **copies** into `~/.gemini/config/plugins/aops/` and `~/.gemini/antigravity-cli/plugins/aops/`.             | Re-run `build-dev` + `install-agy`.                                      |

`install-dev` also prunes stale versions from the local `aops` marketplace cache and (via
the axioms transport, §2) runs `scripts/install_automode.py` to merge the always-on axioms
into `~/.claude/settings.json`.

### 5.3 Cleanup targets — what removes what, and when

| Target                                                 | Scope                                                                                                                                                                                                                                                                                                                                                                                                                                                            | When it runs                                                                                |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `clean-local`                                          | Uninstalls the local-dev Claude plugins (`aops@aops`, `aops-tools@aops`) and removes the `aops` marketplace; uninstalls the released plugins and removes the `academicOps` marketplace; uninstalls agy's `aops`/`aops-tools`; deletes `dist/aops-antigravity` + `dist/aops-tools-antigravity`; strips any leftover **symlink** (never a real copy) at the agy plugin paths so a dangling dev-symlink can't collide with the release install that follows (§5.5). | Automatically, as the first step of `make install`. Idempotent and quiet.                   |
| `uninstall-dev`                                        | Inverse of the dev install: tears down the local `aops` marketplace/plugins and restores the release `academicOps` marketplace + plugins.                                                                                                                                                                                                                                                                                                                        | Manually, when done dev-testing.                                                            |
| `uninstall-cowork`                                     | Removes the isolated `academicOps-cowork` marketplace + its `aops`/`aops-tools` installs (and any legacy `aops-coworklocal`). Leaves the `academicOps`/`aops` marketplaces alone — but note the plugins are then uninstalled everywhere (the cowork copies _were_ the install); re-run `make install` or `make dev`.                                                                                                                                             | Manually.                                                                                   |
| `clean` / `clean-plugins` (`scripts/clean_plugins.py`) | Disk hygiene, not marketplace/plugin-identity cleanup: prunes CLI-surface cache versions not referenced by `installed_plugins.json` plus orphaned `.install-manifests/*.json`; on the desktop GUI surface, force-strips the aops plugin entries (drop-set: `aops-core`, `aops`, `aops-ts`, `aops-tools`) from `local-agent-mode-sessions/*/rpm/manifest.json` and deletes their unpacked dirs (for when the GUI's own uninstall button fails).                   | Manually (`make clean`/`make clean-plugins`), or whenever the GUI uninstall path is broken. |

There is currently **no mechanism, anywhere in this pipeline, that removes stray/orphan
MCP server entries** from a user's `~/.claude.json`. If stray MCP servers need removing,
that's a manual edit today.

### 5.4 Cowork install

`make install-cowork` (depends on `build-dev`) registers `dist/cowork` as the
`academicOps-cowork` directory marketplace and installs `aops@academicOps-cowork` +
`aops-tools@academicOps-cowork` from it, halting on the first failure (same
no-soft-fail rule as `install-claude`) and forwarding `PKB_MCP_URL` as the `aops`
plugin's `pkb_mcp_url` userConfig when set. Restart the Claude desktop app afterwards so
Cowork picks the plugins up.

**These are the same plugins the CLI installs** — every user-scope install loads in every
Claude session — so `install-cowork` _replaces_ any other copy of `aops`/`aops-tools`
(dev `@aops`, released `@academicOps`, legacy `aops-coworklocal`) rather than sitting
alongside it; a second copy would double-register the hook router and MCP server.
Symmetrically, `install-dev` and `clean-local` (and therefore `make install`) tear down
the `@academicOps-cowork` copies — after a `make install`, re-run `make install-cowork`
on a machine that uses Cowork. Pick one channel per machine.

Where a local marketplace isn't usable, `make package-cowork` surfaces the per-plugin
zips (`dist/cowork/aops-v*.zip`, `aops-tools-v*.zip`) for manual upload via **Cowork →
Customize → Add plugins → Upload a file**, and on WSL `package-cowork-windows` copies
them into the Windows-side `Downloads` folder (UNC paths are flaky in the native
file-picker).

### 5.5 Antigravity (`agy`) install: release vs local

`install-agy` uses agy's **official** `agy plugin install <source>` — never hand-copying
plugin source. agy has no user-addable marketplace, so third-party plugins install from
either a local directory or a GitHub URL. For each of `aops` and `aops-tools`, `install-agy`
prefers the local `dist/aops-antigravity` / `dist/aops-tools-antigravity` when present (a
prior `build-dev` ran) and otherwise falls back to a live `dist`-branch URL. Either way,
**agy copies** the plugin into `~/.gemini/config/plugins/<plugin>/` and
`~/.gemini/antigravity-cli/plugins/<plugin>/` — it does not symlink.

The `${extensionPath}` non-resolution bug (antigravity-cli#390) is handled at **build**
time now: `build.py` writes the antigravity `mcp_config.json` `services` server to launch
via `bash -c ~/.gemini/config/plugins/<plugin>/scripts/run-mcp.sh` (§2), so there is no
post-install `sed` step. Remove that workaround once #390 is fixed upstream.

### 5.6 Plugin → surface matrix

| Plugin        | Claude Code CLI                                                                                  | Claude Cowork                                               | Antigravity/agy       | Windows-side Claude (WSL) |
| ------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- | --------------------- | ------------------------- |
| `aops`        | ✅ `aops@academicOps` — hard-fail gate (the success criterion of the whole `make install` chain) | ✅ `aops@academicOps-cowork` (`install-cowork`, §5.4)       | ✅ (`install-agy`)    | ✅                        |
| `aops-tools`  | ✅ (hard-fail — every plugin in `CLAUDE_PLUGINS` halts the chain on failure)                     | ✅ `aops-tools@academicOps-cowork` (`install-cowork`, §5.4) | ✅ (`install-agy`)    | ✅                        |
| `aops-ts`     | manual only — `claude plugin install aops-ts@academicOps` (§2)                                   | —                                                           | — (Claude-only build) | —                         |
| `aops-cowork` | —                                                                                                | — (retired from the ship set, §3 legacy note; source-only)  | —                     | —                         |

## 6. Release path (`dev` → tag → publish)

`release-please` manages version bumps from conventional commits; merging the release PR
creates the stable `vX.Y.Z` tag. The tag push fires `.github/workflows/build-extension.yml`
**in this repo** — there is no `repository_dispatch` and no separate dist repo. The
workflow builds the per-platform `dist/` artifacts, fast-forward-publishes them onto the
`dist` branch (the install channel), and uploads the release archives as GitHub Release
assets.

Pre-release tags (`vX.Y.Z-rc.N`, `-dev.N`, …) take the same workflow but publish a
semver-prerelease build to `dist` too, and cut a `--prerelease` GitHub Release with
installable assets, so testers can install by tag while semver-aware consumers don't treat
it as latest-stable.

Manual rebuild against a specific ref: push a pre-release tag at that commit — e.g.
`git tag v<next>-rc.1 <sha> && git push origin v<next>-rc.1` — which triggers
`build-extension.yml` against the tagged commit.

The full merge-gate → release → publish → version-sync contract (CI required checks, the
two human approval gates, the `dev`/`dist` branch topology decision record, and the
version/`uv.lock` sync hardening) is owned by
[`specs/workflows/releasing.md`](workflows/releasing.md) — read that for release-pipeline
detail; it isn't duplicated here.

## 7. Local verification

After running `uv run scripts/build.py`:

```bash
# 1. Manifest validates and strips marketplace leakage
jq '{name, version, mcpServers}' dist/aops-claude/.claude-plugin/plugin.json

# 2. Hooks payload structure
jq '.hooks | keys' dist/aops-claude/hooks/hooks.json

# 3. Install locally, then in a fresh interactive `claude` session run `/hooks`
claude plugin install ./dist/aops-claude
# in the new session, `/hooks` should list `Plugin Hooks (aops@academicOps)`
# and a session-hooks.jsonl should appear under ~/.claude/projects/<slug>/
```

`make build-dev` additionally runs `claude plugin validate dist/aops-claude` /
`dist/aops-tools-claude` and `agy plugin validate dist/aops-antigravity` /
`dist/aops-tools-antigravity` when those CLIs are on PATH.

If `/hooks` shows the plugin's events but no `*-session-hooks.jsonl` is written, the router
is crashing. Reproduce in isolation:

```bash
echo '{"hook_event_name":"SessionStart","session_id":"diag","transcript_path":"/tmp/x","cwd":"'$PWD'"}' \
  | bash ~/.claude/plugins/cache/academicOps/aops/<version>/hooks/router.sh --client claude
```

## 8. Common breakage modes

- **Plugin enabled but `/hooks` doesn't list its events.** CC couldn't read
  `hooks/hooks.json` — usually a JSON syntax error or an unresolvable command path. Inspect
  with `python3 -c "import json; json.load(open('hooks/hooks.json'))"`.
- **`/hooks` lists events but no session-hooks log is written.** Router crashes before
  logging. Run the router manually with a synthetic event (see §4/§7).
- **Subagent / isolated-worktree sessions don't run SessionStart.**
  Programmatically-spawned Claude sessions (Agent tool with `isolation: worktree`,
  FleetView-launched sessions) may not invoke SessionStart hooks the way the interactive
  `claude` CLI does. This is a session-kind issue, not a plugin manifest issue.
- **Plugin shows installed but version drifted.** `~/.claude/plugins/installed_plugins.json`
  pins an older version than `marketplace.json` advertises. Run
  `claude plugin update aops@academicOps` (marketplace nickname `academicOps`, plugin name
  `aops`).
- **"Unrecognized keys" validation error on install.** Marketplace-only fields (`source`,
  `category`) leaked into `dist/aops-claude/.claude-plugin/plugin.json`. Check the plugin's
  `templates/aops.template.json` doesn't carry them.
- **A local dev install (`make dev`) "isn't shadowing" a release install, or vice versa.**
  Check `claude plugin marketplace list` for both `aops` (dev) and `academicOps` (release)
  — `marketplace add` never re-points an existing name (§5.1), so a stale one of either can
  silently win. Run `make clean-local` to reset before `make install`.
- **agy shows a plugin installed but edits to `dist/aops-antigravity` never show up.** agy
  installs are **copies** (§5.5) — an edit needs `build-dev` + `install-agy` re-run. If
  `~/.gemini/config/plugins/aops` is a leftover symlink from an older dev workflow, remove
  it (`make clean-local` strips stray symlinks at those paths).
- **Plugins vanish from Cowork after a desktop-app restart.** They were installed from a
  github-source marketplace (`@academicOps`) — Cowork's `RemotePluginManager.syncPlugins`
  nukes those on every restart. Use `make install-cowork` (local `dist/cowork` directory
  marketplace) on machines that run Cowork (§3/§5.4).
- **aops appears twice in a session (double hooks/MCP).** Two copies of the same plugin
  are installed under different marketplace names (e.g. `@academicOps` +
  `@academicOps-cowork`). Every install target tears the other namespaces down first, so
  this only happens after hand-installs — uninstall one copy, or re-run the one `make`
  install target you actually want (§5.4).

## 9. Do not modify

Files under `dist/` are build outputs. Edit `templates/`, the plugin source directories
(`aops/`, `aops-tools/`, `aops-ts/`, `aops-cowork/`), or `scripts/build.py` and rerun the
build. PRs that touch `dist/` will be reverted.
