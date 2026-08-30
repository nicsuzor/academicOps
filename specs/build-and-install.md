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
[`specs/ARCHITECTURE.md`](ARCHITECTURE.md) — not restated here. Researchers who
just want to _install_ the framework want [`INSTALL.md`](../INSTALL.md) (repo
root) or [`README.md`](../README.md); contributors doing dev setup want
[`CONTRIBUTING.md`](../CONTRIBUTING.md), which points here for design detail.

## 1. Local install (the Makefile)

The root `Makefile` is the single entry point. `build/marketplace.toml` is the
source of truth for the plugin set it installs — one entry per plugin directory
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
before re-adding it. `aops-core`'s `services` MCP server resolves `$PKB_MCP_URL`
from the environment at launch (`ARCHITECTURE.md`, "No defaults" — the URL is
never committed, and there is no fallback).

**Cowork is the exception, and is currently broken on the published artifact.**
Cowork installs a plugin by manual zip upload (desktop app → Customize → Add
plugins → Upload a file), and a plugin installed that way launches its MCP
servers with a bare environment: `$PKB_MCP_URL` expands to the empty string,
`fastmcp run ""` exits, and the client reports "Connection closed". The upload
path has no `--config` equivalent to supply the endpoint afterwards, so the URL
has to travel inside the artifact. `build.marketplace._bake_cowork_mcp_json`
resolves it into the zips' `.mcp.json` — swapping the server for the
`plugins/aops-core/scripts/run-mcp.sh` stdio launcher with the URL in its `env`
block, since that bare environment also routinely lacks `uvx` on `PATH` — **when
`PKB_MCP_URL` is set in the build environment**. It reads that value from the
environment; it is never committed. An unset variable is not a build failure:
CI has no `PKB_MCP_URL`, so **published zips ship with no endpoint and their
`services` MCP does not work in Cowork**, and will not until there is a way to
configure it post-install. Only a local `make build-cowork` with `PKB_MCP_URL`
exported produces a usable zip. The `dist/cowork/<name>` directory copy is never
rewritten — a directory-marketplace install can still use `--config`.

Both Claude Code and `agy` install by **copying** the built plugin content into
their own plugin caches — an edit to `plugins/` is invisible to an installed
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
   This step runs for both stable and prerelease tags — prerelease builds ship
   to `dist` too, as a semver prerelease version, so a client chooses whether to
   install one rather than being force-upgraded.
6. **Docker (stable tags only).** Builds and pushes
   `ghcr.io/nicsuzor/aops-crew:v<version>` and `:latest` from the `Dockerfile`,
   cloning the `dist` branch just published.
7. **GitHub Release.** Uploads every `dist/*.tar.gz` archive to a release tagged
   `v<version>`, `--prerelease` for a testing build.

A manual rebuild against a specific commit: push a prerelease tag at that
commit — e.g. `git tag v<next>-rc.1 <sha> && git push origin v<next>-rc.1`.

## 3. Common breakage modes

- **Plugin enabled but `/hooks` doesn't list its events.** Claude Code couldn't
  read `hooks/hooks.json` — usually a JSON syntax error or an unresolvable
  command path. Inspect with `python3 -c "import json; json.load(open('hooks/hooks.json'))"`.
- **A local dev install (`make install-dev`) isn't shadowing a release install,
  or vice versa.** Check `claude plugin marketplace list` for both `aops` (dev)
  and `academicOps` (release) — a stale one of either can silently win. Run
  `make uninstall-dev` before `make install` to reset.
- **Stable release aborted with a version mismatch.** The pushed tag, the
  committed `pyproject.toml` version, and `.release-please-manifest.json`
  disagree — `release-please` owns all three; don't hand-edit one without the
  others.

## 4. Do not modify

Files under `dist/` are build outputs. Edit `plugins/`, `lib/`, or `build/` and
rerun `make build`. PRs that touch `dist/` will be reverted.
