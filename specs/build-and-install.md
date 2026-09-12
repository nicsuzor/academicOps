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

| Target               | Effect                                                                                                           |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `make build`         | Assembles `dist/` for every plugin, clients (Claude, agy, openclaw) and channels (cowork, openclaw).             |
| `make install-dev`   | `build`, then registers `dist/` as the local `aops` marketplace and installs every plugin from it (`aops@aops`). |
| `make uninstall-dev` | Removes the local marketplace and its installs, then restores the released `academicOps` marketplace.            |
| `make install`       | Registers `nicsuzor/academicOps@dist` as the `academicOps` marketplace and installs every plugin from it.        |
| `make test`          | `uv run pytest tests/`.                                                                                          |
| `make lint`          | `ruff check .`.                                                                                                  |
| `make format`        | `ruff format .` + `dprint fmt`.                                                                                  |
| `make clean`         | Removes `dist/`.                                                                                                 |
| `make docker`        | Alias for `make docker-build`.                                                                                   |
| `make docker-build`  | `make build`, then `docker build --build-arg AOPS_DIST_SOURCE=local` from this checkout's own `dist/`.           |
| `make docker-shell`  | `docker-build`, then an interactive shell in the image.                                                          |
| `make docker-push`   | Pushes the built image to `ghcr.io/nicsuzor/aops-crew`.                                                          |

`aops` (dev, local-directory source) and `academicOps` (release, GitHub-source)
are separate marketplace names specifically so one install can never silently
shadow the other: `claude plugin marketplace add` is a no-op when a name already
exists, so both `install-dev` and `install` remove their own marketplace name
before re-adding it. `pkb`'s `services` MCP server takes its endpoint from an
install-time placeholder, never a committed default (`.agents/CORE.md`, "No
defaults") -- see "MCP server configuration" below for the form each client
takes.

**MCP server configuration:**
The PKB `services` MCP server ships in `plugins/pkb`: a FastMCP stdio launcher
(`uvx --from fastmcp-slim[server] fastmcp run <endpoint>`). Every surface needs
the literal endpoint in place before first use; which mechanism supplies it
differs by client, because only Claude Code has an install-time substitution
feature:

1. **`claude` client -- `userConfig` + `--config`.**
   `plugins/pkb/manifest/mcp.template.json` declares a `pkb_mcp_url` userConfig
   option and the launcher reads `"${user_config.pkb_mcp_url}"`. Claude Code
   substitutes that at install time from whatever `--config pkb_mcp_url=<url>`
   supplies (`claude plugin install pkb@<marketplace> --config
   pkb_mcp_url=<url>`), storing the value the same way `/plugin configure`
   would -- no shell export needed afterwards, on any surface that goes
   through `claude plugin install`: `make install-dev` (passes `--config` when
   `$PKB_MCP_URL` is set in the installing shell) and `.claude/setup.sh` (the
   Claude Code web bootstrap, which already calls `--config pkb_mcp_url=`).
2. **`agy` client -- literal placeholder, rewritten post-install.**
   agy has no `--config`/userConfig substitution: `agy plugin install <dir>`
   copies a plugin's built `mcp_config.json` verbatim. Its `services` server
   therefore ships the literal text `YOUR_PKB_URL` in place of the URL.
   `build.install patch-agy-mcp` rewrites that placeholder to the concrete
   value in `~/.gemini/config/plugins/<name>/.mcp.json` right after the copy
   -- `make install-dev` runs it once, after installing every plugin for agy.
   With `$PKB_MCP_URL` unset it is a no-op, not a failure: the plugin installs
   with the placeholder left in place, unusable until reconfigured.
3. **Cowork bakes the URL at build time.**
   Cowork does not expand environment variables at runtime and has no
   userConfig either, and neither install path (directory marketplace or
   manual zip upload) can supply a value afterwards. `build.marketplace`
   therefore collapses every server that defers to `$PKB_MCP_URL` or
   `${user_config.pkb_mcp_url}` into one `services` server of the form
   `{"type": "http", "url": <literal>}` in `dist/cowork/<name>/.mcp.json` (and
   so in the zip, which is that directory verbatim), with the literal read
   from `PKB_MCP_URL` in the build environment. A literal `type: http` url is
   the one form Cowork connects with; the stdio launcher is not used in this
   channel. With `PKB_MCP_URL` unset the build warns and ships the channel
   unrewritten -- the published channel is built that way and its `services`
   MCP does not work in Cowork. `dist/<name>-claude` and `dist/<name>-agy` are
   never rewritten by this step: they keep their own placeholder for (1) or
   (2) above to resolve.
4. **`make install-dev`'s Cowork-session dev workaround.**
   `build.install patch-dev-mcp` substitutes `$PKB_MCP_URL` with the concrete
   value from the user's host environment in any existing Cowork GUI session
   directories, which hold their own copy of a plugin's `.mcp.json` from
   whenever it was installed. It never touches `dist/`.
5. **`make clean` Cowork package pruning**:
   `make clean` (and `make clean-plugins`) invokes `scripts/clean_plugins.py`, which
   cleans uninstalled Cowork session packages and removes session-level plugin data caches.

Both Claude Code and `agy` install by **copying** the built plugin content into
their own plugin caches -- an edit to `plugins/` is invisible to an installed
session until `make install-dev` rebuilds and reinstalls.

## 2. Release path (`dev` → tag → publish)

`release-please` manages version bumps from conventional commits; merging the
release PR it opens creates the stable `vX.Y.Z` tag. Pushing any `v*` tag fires
`.github/workflows/build-extension.yml`, run from the tagged commit:

1. **Resolve build context.** A tag shaped `vX.Y.Z-<suffix>` (`-rc.N`, `-dev.N`,
   `-beta.N`, …) is a prerelease/"testing" build; a plain `vX.Y.Z` tag is stable.
2. **Checkout.** The tagged commit, plus the `dist` branch (the publish target)
   at a separate path.
3. **Compute version.** The tag, verbatim, with the leading `v` stripped. For a
   stable tag, the workflow asserts the tag, `pyproject.toml`'s `version`, and
   `.release-please-manifest.json` all agree, and aborts the release if they
   don't.
4. **Build.** `uv run python -m build.build --set-version <version>`.
5. **Publish to `dist`.** Every built plugin directory under `dist/` is mirrored
   to the root of the `dist` branch (an orphan branch; plugin dirs and
   `.claude-plugin/marketplace.json` live at its root), along with
   `pr-pipeline.yml` and the workflow files it references, so external
   consumers can pin `uses: nicsuzor/academicOps/.github/workflows/pr-pipeline.yml@dist`.
   This step runs for both stable and prerelease tags -- prerelease builds ship
   to `dist` too, as a semver prerelease version, so a client chooses whether to
   install one rather than being force-upgraded.
6. **Docker (stable tags only).** Builds and pushes
   `ghcr.io/nicsuzor/aops-crew:v<version>` and `:latest` from the `Dockerfile`,
   cloning the `dist` branch just published.
7. **GitHub Release.** Uploads every `dist/*.tar.gz` archive to a release tagged
   `v<version>`, `--prerelease` for a testing build.

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
