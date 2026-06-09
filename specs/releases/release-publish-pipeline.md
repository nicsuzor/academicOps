---
id: release-publish-pipeline
title: "Release & Publish Pipeline"
type: spec
created: 2026-06-09T00:00:00.000000000+00:00
modified: 2026-06-09T00:00:00.000000000+00:00
permalink: release-publish-pipeline
status: operative-target
tags:
  - workflow
  - release
  - publish
  - versioning
  - docker
---

# Release & Publish Pipeline — dev → tag → artifacts

> Status: **operative-target**. This is the contract for the release half of the
> pipeline (the merge half is [[pr-pipeline-v2]]). Most of it is live; the gaps in
> §6 are tracked fixes that bring reality to this contract.
>
> **Decision record (2026-06-09).** Maintainer reviewed this spec and approved
> proceeding to implementation, settling three forks: (1) complete the v2 merge
> gate (§6 C); (2) delete `academicOps` `main` after the first clean release
> verifies `@dist` + the mirror (§6 D1); (3) publish Docker on stable tags only
> (§5). Implementation is direct-to-`dev`, no PRs.

## 1. Topology (the model)

The repo de-inverted its branch topology (PR #1616, 2026-06-06): the default branch
is the **source trunk**, built artifacts live on a non-default **orphan branch**.

| Ref                          | Role                                                                                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dev`                        | **default branch**, source trunk — all work lands here; release-please runs here                                                                         |
| `dist`                       | orphan **artifacts** branch — `.claude-plugin/marketplace.json` + `dist/aops-*`; installed via `claude plugin marketplace add nicsuzor/academicOps@dist` |
| `nicsuzor/aops` `main`       | **Cowork mirror** of `dist` — Cowork can't pin a non-default ref, so it installs the same payload from this repo's default branch                        |
| `ghcr.io/nicsuzor/aops-crew` | **worker/crew container** — polecat pulls it (`polecat/cli.py:_ensure_docker_image`)                                                                     |
| `academicOps` `main`         | **deprecated** — stale orphan from the pre-migration topology; deleted after the first clean release verifies `@dist` + the mirror (§6 D1)               |

There are exactly **two human gates**, both owned by the maintainer:

1. **Admit** a PR into the fix-loop ([[pr-pipeline-v2]] §3.2) — the per-PR gate.
2. **Approve + merge** the Release PR — the per-release gate.

## 2. Release (dev → tag)

`release-please.yml` (trigger: `push: [dev]`; token: `AOPS_DIST_PAT`):

1. On each push to `dev`, release-please opens/updates a **Release PR targeting `dev`**
   (not `main` — `main` is deprecated). It accumulates conventional commits into:
   - `CHANGELOG.md` (sectioned per `release-please-config.json`),
   - the version in `pyproject.toml` (`$.project.version`) and the four templates
     (`templates/aops-{core,tools}.{gemini-extension,plugin}.json`) via `extra-files`,
   - a **regenerated `uv.lock`** — the workflow checks out the PR branch, runs
     `uv lock`, and commits it (`release-please.yml` lines 44–56).
2. The maintainer **approves + merges** the Release PR. release-please then creates the
   `vX.Y.Z` tag (with `AOPS_DIST_PAT`, so the tag push triggers `build-extension.yml`).

## 3. Publish (tag → artifacts)

`build-extension.yml` (trigger: **`push: tags: ['v*']` only**). Triggering on the tag —
not on `release: published` — is deliberate: a `release` event runs the _default
branch's_ copy of the workflow and would double-fire against the tag run (the install
break fixed in `2fcf8c2f`). The tag SHAPE selects the channel:

- **Stable `vX.Y.Z`** — build from the tagged commit, then:
  - publish plugins to the **`dist` branch** (fast-forward push; `dist/aops-*` + root
    `.claude-plugin/marketplace.json`),
  - mirror the identical tree to **`nicsuzor/aops`** `main` (Cowork channel),
  - build & push **`ghcr.io/nicsuzor/aops-crew:vX.Y.Z` and `:latest`** (§6 A3),
  - upload archives to the **GitHub Release `vX.Y.Z`**.
- **Prerelease `vX.Y.Z-rc.N` / `-dev.N` / …** — build, cut a `--prerelease` GitHub
  Release with installable assets. The `dist` branch, the mirror, and the published
  Docker tags are **left untouched** (the stable install channels must never receive a
  prerelease).

## 4. Version & uv.lock — never out of sync (the technique)

The standard release-please + uv discipline; release-please is the single source of
truth and CI is fail-closed on drift.

1. **release-please owns the version** — `.release-please-manifest.json` is the SSoT.
2. **It propagates that version into every version-bearing file** in the Release PR via
   `extra-files` (pyproject + 4 templates). Committed files always equal the next
   release.
3. **It regenerates `uv.lock` in the same PR**, so the lockfile's embedded project
   version tracks `pyproject.toml`.
4. **`uv sync --frozen` is the CI gate** (`build-extension.yml` "Install dependencies",
   and the container venv pre-bake). A lockfile that disagrees with `pyproject.toml`
   cannot build, so it cannot release.
5. **By construction**, the instant the Release PR merges, `dev`'s committed version ==
   the tag == the published release. Between releases `dev` shows the last release; the
   next Release PR is the only thing that advances it. Build-time `X.Y.Z-dev.N+sha`
   strings (`scripts/build.py`) are ephemeral display metadata, never committed — they
   cannot drift the files.

**Hardening (so it is _never_, not _usually_, in sync):**

- **G1 — stable version comes from the tag.** A stable build must set the version from
  `${tag#v}` (as the prerelease branch already does), **not** `scripts/version.py --get`,
  which runs `git describe --dirty` on a tree the build has already dirtied and emits
  `…-dev.0+gSHA.dirty`.
- **G2 — publish-time assertion.** Before publishing a stable release, assert
  `tag == pyproject $.project.version == manifest`; abort otherwise (fail-closed).
- **G3 — local lockfile guard.** A pre-commit `uv lock --check` catches lockfile drift
  before CI.

## 5. Docker (`ghcr.io/nicsuzor/aops-crew`)

The crew/worker image (root `Dockerfile`) is the polecat runtime: Claude Code + Gemini +
agy + the aops framework. It is published on **stable tags only** (`:vX.Y.Z` + `:latest`),
in `build-extension.yml`, from the tagged `dev` commit. The Dockerfile installs the
framework from the published distribution, not from source (§6 B2).

## 6. Fixes — the gap between this contract and current reality

**A · Release/publish (`build-extension.yml`)**

- **A1** — Stable build: derive version from the tag, not dirty `version.py --get` (G1).
- **A2** — Add `tag == pyproject == manifest` assertion before publish (G2).
- **A3** — Add Docker build+push of `ghcr.io/nicsuzor/aops-crew:vX.Y.Z` + `:latest` on
  stable tags.

**B · Docker image drift (`Dockerfile`)**

- **B1** — Remove the pkb-binary install step — pkb is a remote MCP since PR #1615
  ([[project_no_dist_build]]).
- **B2** — The framework install clones the default branch (`dev` = source, no built
  `dist/`); install from `@dist` (or the mirror) instead. Verify on first CI build.

**C · Complete v2 merge gate** (see [[pr-pipeline-v2]] §11, Phases 4–6)

- **C1** — Apply the v2 ruleset to live `13762049`: `0` approvals + required
  `Lint / Lint`, `Pytest / Pytest`, `enforcer-status`, `qa-status`, `admit-status` — in
  ONE atomic change (no bypass window).
- **C2** — Confirm `pr-fix-loop` Environment requires the maintainer; make `admit-status`
  required (part of C1).
- **C3** — Repurpose `agent-merge-prep.yml` into the Stage-2 dev agent; retire
  `merge-prep-cron.yml`'s per-PR no-op dispatch.
- **C4** — Remove the duplicate enforcer/qa invocation (orchestrator + `trigger-*.yml`
  both fire on `pull_request`).
- **C5** — `merge-prep.agent.md` hardcodes `origin/main` as the PR base; change to `dev`.

**D · gh state / branches / stale files**

- **D1** — Delete `academicOps` `main` after one clean stable release verifies `@dist` +
  mirror.
- **D2** — Delete `auto-retarget-pr.yml` — its rationale (keep default = `main`) is
  obsolete now that `dev` is default.
- **D3** — Fix the stale `origin/HEAD → origin/main` pointer; prune dead local branches.

## 7. Cross-references

- [[pr-pipeline-v2]] — the merge half (PR → merged on `dev`), including the `pr-fix-loop`
  admit gate.
- [[project_dist_branch_migration]] — the de-inversion decision (#1616).
- [[project_release_pipeline_default_branch]] — the default-branch-trigger bug class the
  migration dissolves.
- `.github/workflows/{release-please,build-extension}.yml`, `.github/rulesets/pr-review-and-merge.yml`.
