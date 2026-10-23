---
type: spec
title: Local Install & Release Pipeline
status: ready
tags: [framework, build, install, release, makefile]
---

# Local Install & Release Pipeline

How a developer turns this checkout into installed plugins on their own machine,
and how a tagged commit becomes the published `dist` branch and a GitHub Release.
Repository layout, plugin boundaries, and build stages are
[`specs/ARCHITECTURE.md`](ARCHITECTURE.md) -- not restated here. Researchers who
just want to _install_ the framework want [`INSTALL.md`](../INSTALL.md) (repo
root) or [`README.md`](../README.md); contributors doing dev setup want
[`CONTRIBUTING.md`](../CONTRIBUTING.md), which points here for design detail.

## 1. Local install (the Makefile)

The root `Makefile` is the single entry point. `build/marketplace.toml` is the
source of truth for the plugin set it installs -- one entry per plugin directory
under `plugins/`, mirroring the table in `ARCHITECTURE.md`.

| Target | Effect |
| - | - |
| `make build` | Assembles `dist/` for every plugin, clients (Claude, agy, openclaw) and channels (cowork, openclaw). |
| `make install-dev` | `build`, then registers `dist/` as the local `aops` marketplace and installs every plugin from it (`aops@aops`). |
| `make uninstall-dev` | Removes the local marketplace and its installs, then restores the released `academicOps` marketplace. |
| `make install` | Registers `nicsuzor/academicOps@main` as the `academicOps` marketplace and installs every plugin from it. |
| `make test` | `uv run pytest tests/`. |
| `make lint` | `ruff check .`. |
| `make format` | `ruff format .` + `dprint fmt`. |
| `make clean` | Removes `dist/`. |
| `make clean-plugins` | Prunes stale plugin caches and Cowork packages via `scripts/clean_plugins.py`. |
| `make docker` | Alias for `make docker-build`. |
| `make docker-build` | `make build`, then `docker build --build-arg AOPS_DIST_SOURCE=local` from this checkout's own `dist/`. |
| `make docker-shell` | `docker-build`, then an interactive shell in the image. |
| `make docker-push` | Pushes the built image to `ghcr.io/nicsuzor/aops-crew`. |

`aops` (dev, local-directory source) and `academicOps` (release, GitHub-source)
are separate marketplace names specifically so one install can never silently
shadow the other: `claude plugin marketplace add` is a no-op when a name already
exists, so both `install-dev` and `install` remove their own marketplace name
before re-adding it. The `services` MCP server is installed at user level across all surfaces, never shipped inside a plugin (see "User-level `services` MCP server" below).

**User-level `services` MCP server:**
The PKB `services` MCP server is not shipped inside any plugin. Cloud sessions never load plugin MCP servers (`CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS=1`). The `services` MCP server is installed at user level on every surface:

1. **Local Claude Code**:
   `claude mcp add --transport http --scope user services <PKB_MCP_URL>` (must use `--scope user`; `--scope local` was observed to register nothing).
2. **Claude Code Cloud & Cowork**:
   Configured via the claude.ai account connector named `services`.
3. **Antigravity (agy)**:
   Configured in user-level MCP settings (`~/.gemini/antigravity-cli/settings.json` or `~/.gemini/antigravity-cli/mcp/services.json`).

Inside agent definitions and skills, PKB tools are referenced as `mcp__services__*` (e.g. `mcp__services__portal_codemode_execute`).

4. **`make clean-plugins` Cowork package pruning**:
   `make clean-plugins` invokes `scripts/clean_plugins.py`, which
   cleans uninstalled Cowork session packages and removes session-level plugin data caches.

Both Claude Code and `agy` install by **copying** the built plugin content into
their own plugin caches -- an edit to `plugins/` is invisible to an installed
session until `make install-dev` rebuilds and reinstalls. Concretely, `claude
plugin install <plugin>@<marketplace>` copies the plugin directory the
marketplace's `.claude-plugin/marketplace.json` `source` field points at into
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`
(`installed_plugins.json` records the mapping); a subagent spawned from that
session loads its `agents/*.md` from that cache path, not from the working
tree. The version segment is the git-derived string from `build/version.py`
(`get_current_version`), so an uncommitted or unbuilt change never collides
with an already-installed version -- but nothing re-copies an existing version
directory in place, so the cache only ever reflects whatever the last
`make install-dev`/`make install` run built.
There is no automatic refresh on `git pull`, `git merge`, or `git checkout`.
`make install-dev` is run by hand to rebuild `dist/` and refresh the local
plugin cache whenever plugin definitions, instructions, or dependencies change.
In a `polecat` container, plugin content is baked into the image at build time
(`Dockerfile`, `AOPS_DIST_SOURCE`), and rebuilding the image is the refresh path.

## 2. Release path (`release/*` → `main` → publish)

academicOps `main` holds the current release's source plus the built plugin objects
previously published to the orphan `dist` branch. The build runs on every merge into `main`
and writes its output to `main` only. Publishing to the legacy `nicsuzor/aops` mirror has
stopped as a trial. Merges into `main` are restricted to fully green releases, enforced by
branch protection requiring all checks green (`Lint / Lint`, `Type Check / Type Check`,
`Pytest / Pytest`) with no bypass allowed.

### What changed for installs

- **Marketplace ref**: Users install from `main` of `nicsuzor/academicOps` using
  `claude plugin marketplace add nicsuzor/academicOps` (or `nicsuzor/academicOps@main`).
  The previous orphan `dist` branch (`@dist`) is superseded by `main`.
- **Built plugin resolution**: Claude Code reads `.claude-plugin/marketplace.json` at the root
  of `main`, where each plugin points to `./<plugin>-claude` (also committed to `main`).
- **Discontinued mirrors**: `nicsuzor/aops` is no longer updated or published to.

### How each release candidate is now published

1. **Active development and validation.** Work proceeds on release lines (e.g. `release/v1.0-rc0`).
   Pull requests into release lines run the full `pr-pipeline.yml` suite (Lint, Type Check, Pytest).
2. **Publishing release candidates.** Release candidates are published by pushing an annotated or lightweight tag on the release line (e.g. `v1.0-rc6`). Pushing an rc tag (`v*-*`) triggers `.github/workflows/publish-release.yml`, which runs pytest, builds distribution artifacts, and uploads archives to a GitHub pre-release (`gh release create --prerelease`). Pushing an rc tag publishes a GitHub pre-release only and never writes to `main`.
3. **Merging stable release into `main`.** Once a release candidate is validated and fully green, a pull request is merged from the release line into `main`. Branch protection on `main` requires all status checks to pass before merging, with no bypass allowed.
4. **Build on merge.** Every merge into `main` triggers `.github/workflows/build-extension.yml`.
   The workflow:
   - Computes the version from `build.version`.
   - Runs `uv run python -m build.build --set-version <version>`.
   - Mirrors built plugin directories (`<plugin>-claude/`, `<plugin>-agy/`, `<plugin>-openclaw/`, `cowork/`),
     `.claude-plugin/marketplace.json`, and `.aops-image-metadata.json` directly to the root of `main`.
   - Commits and pushes the built artifacts back to `main` with `[skip ci]`.
   - Writes only to `main` (no writes to `dist` or `nicsuzor/aops`).
5. **Stable GitHub Releases.** Annotated release tags (`vX.Y.Z`) pushed on `main` trigger `.github/workflows/publish-release.yml` to upload tarball archives (`dist/*.tar.gz`) to a stable GitHub Release.

A manual rebuild against a specific commit: push a prerelease tag at that
commit -- e.g. `git tag v<next>-rc.1 <sha> && git push origin v<next>-rc.1`.

## 3. Common breakage modes

- **Plugin enabled but `/hooks` doesn't list its events.** Claude Code couldn't
  read `hooks/hooks.json` -- usually a JSON syntax error or an unresolvable
  command path. Inspect with `python3 -c "import json; json.load(open('hooks/hooks.json'))"`.
- **A local dev install (`make install-dev`) isn't shadowing a release install,
  or vice versa.** Check `claude plugin marketplace list` for both `aops` (dev)
  and `academicOps` (release) -- a stale one of either can silently win. Run
  `make uninstall-dev` before `make install` to reset.
- **Stable release aborted with a version mismatch.** The pushed tag, the
  committed `pyproject.toml` version, and `.release-please-manifest.json`
  disagree -- `release-please` owns all three; don't hand-edit one without the
  others.

## 4. Do not modify

Files under `dist/` are build outputs. Edit `plugins/`, `lib/`, or `build/` and
rerun `make build`. PRs that touch `dist/` will be reverted.
