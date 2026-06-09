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

# Release & Publish Pipeline — merge → tag → artifacts

> Status: **operative-target**. This is the single owner-approvable contract for the
> **whole** pipeline: merge → release → publish → version-sync. The merge-gate detail
> lives in [[pr-pipeline-v2]] and is cross-referenced here, not duplicated. Most of this
> is **live on `origin/dev`**; the gaps are tracked fixes in §9. Every claim below is
> flagged **LIVE** (in production on `origin/dev` today) or **SPEC-ONLY** (the v2 target,
> not yet wired) so the document never overstates reality.
>
> **Decision record (2026-06-09).** Maintainer reviewed this spec and approved proceeding
> to implementation, settling three forks: (1) complete the v2 merge gate (§9 C); (2)
> delete `academicOps` `main` after the first clean release verifies `@dist` + Cowork
> delivery (§9 D1); (3) publish Docker on stable tags only (§6). Implementation is
> direct-to-`dev`, no PRs. **Three items the maintainer explicitly left OPEN are recorded
> honestly in §8 (type checker, alignment, advisory-finding tracking) — this spec
> documents current reality and the open questions; it does not invent resolutions.**

## 1. Shape of the whole pipeline

```
author opens PR ──► STAGE-1 TRIAGE (every push, cheap, no dev) ──► ADMIT GATE (human)
                                                                       │ approve
                                                                       ▼
                       STAGE-2 FIX LOOP (post-admit, real dev) ──► auto-merge squash to dev
                                                                       │
               push to dev ──► release-please opens a Release PR on dev (the per-release gate)
                                                                       │ owner approves + merges
                                                                       ▼
                           vX.Y.Z tag ──► build-extension.yml (tag-only) ──► plugins→dist,
                                                         Docker→ghcr (:vX.Y.Z + :latest),
                                                         archives→GitHub Release
```

There are exactly **two human gates**, both owned by the maintainer:

1. **Admit** a PR into the Stage-2 fix loop — the per-PR gate (§3.3, detail in
   [[pr-pipeline-v2]] §3.2/§5). Live today as the `pr-fix-loop` Environment approval.
2. **Approve + merge** the Release PR — the per-release gate (§5).

Everything between those two clicks is mechanical or agent-driven.

## 2. Topology (the model)

The repo de-inverted its branch topology (PR #1616, 2026-06-06): the **default branch is
the source trunk**, and built artifacts live on a non-default **orphan branch**.

| Ref                          | Role                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `dev`                        | **default branch**, source trunk — all work lands here; release-please runs here. **LIVE.**                                                                                                                                                                                                                                          |
| `dist`                       | orphan **artifacts** branch — `.claude-plugin/marketplace.json` + `dist/aops-*`; installed via `claude plugin marketplace add nicsuzor/academicOps@dist`. **LIVE.**                                                                                                                                                                  |
| Cowork (`aops-cowork` + ZIP) | **Cowork delivery** — ships via the published `aops-cowork` plugin on `dist` **plus** a manual-upload `aops-coworklocal-v{version}.zip` emitted by `scripts/build.py` (Cowork nukes github-source marketplaces on restart, so it needs the ZIP/local path). The old `nicsuzor/aops` full-mirror was retired in `20549c70`. **LIVE.** |
| `ghcr.io/nicsuzor/aops-crew` | **worker/crew container** — polecat pulls it (`polecat/cli.py:_ensure_docker_image`). Published on stable tags (§6). **LIVE.**                                                                                                                                                                                                       |
| `academicOps` `main`         | **deprecated** — stale orphan from the pre-migration topology; deleted after the first clean release verifies `@dist` + Cowork delivery (§9 D1). **PENDING deletion.**                                                                                                                                                               |

> **Cowork delivery, precisely.** There is no longer a `nicsuzor/aops` mirror. Cowork
> gets the framework two ways: (a) the published `aops-cowork` plugin on the `dist`
> branch (the same channel as every other plugin), and (b) a hand-uploaded
> `aops-coworklocal-v{version}.zip` that `build.py` produces, because Cowork wipes
> github-source marketplaces on restart and needs a local/ZIP marketplace to survive. The
> mirror-removal landed in `cf5320de` (drop the orphaned `nicsuzor/aops` mirror step) and
> is **on `origin/dev`**.

## 3. Merge gate (PR → merged on dev) — LIVE, v2

The merge half is owned by [[pr-pipeline-v2]]; this section is the **current-reality
summary** and the authoritative list of what the live ruleset requires. For the
convergence mechanics, per-agent contract, and loop-skip protocol, read
[[pr-pipeline-v2]] §3–§10 — they are not duplicated here.

### 3.1 Required checks (LIVE)

The ruleset `.github/rulesets/pr-review-and-merge.yml` (ID `13762049`, applied to
`refs/heads/dev`) was just synced by the owner. Required status checks, **live today**:

| Required check    | Source                               | Role                                |
| ----------------- | ------------------------------------ | ----------------------------------- |
| `Lint / Lint`     | `lint.yml` via `pr-pipeline.yml`     | mechanical CI — style/format        |
| `Pytest / Pytest` | `pytest.yml` via `pr-pipeline.yml`   | mechanical CI — test suite          |
| `enforcer-status` | `agent-enforcer.yml` (rbg)           | axiom review (AND-gate slot)        |
| `qa-status`       | `agent-qa.yml` (marsha)              | runtime QA (AND-gate slot)          |
| `admit-status`    | Stage-2 admission job (Env approval) | **the one human merge gate** (§3.3) |

- **`required_approving_review_count: 0`.** There is no bot approval to count and no
  separate human review-approval — the Environment approval **is** the human decision.
  The drop `2 → 0` was made in the **same** ruleset change that added `admit-status` to
  required checks (otherwise green checks alone would permit a gate-bypassing manual
  merge — see [[pr-pipeline-v2]] §5 sequencing note).
- **Not required (deliberately):** `Type Check / Type Check` (advisory — §8.1),
  `alignment-status` (does not exist — §8.2), the old `merge-prep-status` (removed,
  replaced by `admit-status`).

### 3.2 Stage-1 triage (every push) — LIVE

On `pull_request` (`opened`, `synchronize`, `ready_for_review`, `reopened`), the triage
orchestrator runs the committing agents in **cost order with a short-circuit**:

```
lint (autofix) ──► enforcer / rbg ──► qa / marsha
```

A pass stops at the first agent that commits; its push starts the next pass from the
cheapest agent. **Convergence** = a full pass with zero commits, leaving every status
fresh on HEAD. Read-only checks (pytest, and typecheck — §8.1) post status, never commit.
Cost-ordered short-circuit means a heavy agent never re-runs "on every lint fix"
([[pr-pipeline-v2]] §3.4 is normative).

### 3.3 The one human gate — `pr-fix-loop` admit (LIVE)

On Stage-1 convergence a Stage-2 run is dispatched and **parks** at the `pr-fix-loop`
GitHub Environment (required reviewer = the maintainer). The maintainer reads the triage
statuses, the agents' reviews, and any alignment input, then **Approves (admit) or
Rejects**. Approving the pending deployment is the button: _this is a good idea — make it
mergeable._ Approval (a) sets the required `admit-status` to `success` on HEAD and (b)
arms `gh pr merge --auto --squash --delete-branch`. **Alignment/pauli is advisory input
to this decision, never a required check** (§8.2).

### 3.4 Stage-2 fix loop + merge (LIVE)

The admitted run reuses the same orchestrator + short-circuit + convergence, now with the
dev/mechanic agent appended last (real development to clear red the autofixers couldn't)
and conflict resolution when the PR is `CONFLICTING`. Required-green to merge = cheap
checks + `enforcer` + `qa` + no conflicts (**not** alignment). Converged + all-green →
the armed auto-merge **squash-merges to `dev`**. Converged + still-red → the dev agent
could not fix it → rejection/escalation review, stop.

## 4. Release (dev → tag) — LIVE

`release-please.yml` (trigger: `push: [dev]`; token: `AOPS_DIST_PAT`):

1. On each push to `dev`, release-please opens/updates a **Release PR targeting `dev`**
   (not `main` — `main` is deprecated). It accumulates conventional commits into:
   - `CHANGELOG.md` (sectioned per `release-please-config.json`),
   - the version in `pyproject.toml` (`$.project.version`) and the four templates
     (`templates/aops-{core,tools}.{gemini-extension,plugin}.json`) via `extra-files`,
   - a **regenerated `uv.lock`** — the workflow checks out the PR branch, runs `uv lock`,
     and commits it (`release-please.yml` lines 44–56).
2. The maintainer **approves + merges** the Release PR. release-please then creates the
   `vX.Y.Z` tag (with `AOPS_DIST_PAT`, so the tag push triggers `build-extension.yml`).

This Release-PR approve+merge is the **second** (per-release) human gate of §1.

## 5. Publish (tag → artifacts) — LIVE

`build-extension.yml` (trigger: **`push: tags: ['v*']` only**). Triggering on the tag —
not on `release: published` — is deliberate: a `release` event runs the _default
branch's_ copy of the workflow and would double-fire against the tag run (the install
break fixed in `2fcf8c2f`). The tag SHAPE selects the channel:

- **Stable `vX.Y.Z`** — build from the tagged commit, then:
  - publish plugins to the **`dist` branch** (fast-forward push; `dist/aops-*` + root
    `.claude-plugin/marketplace.json`),
  - build & push **`ghcr.io/nicsuzor/aops-crew:vX.Y.Z` and `:latest`** (LIVE,
    `build-extension.yml:212–221`),
  - upload archives to the **GitHub Release `vX.Y.Z`** (the upload globs `dist/*.tar.gz`,
    `build-extension.yml:239`).

  Cowork is served by the published `aops-cowork` plugin on `dist` (above) plus the
  manual-upload `aops-coworklocal-v{version}.zip` that `build.py` emits (§2). ⚠️ **Known
  caveat:** the Release upload step globs `dist/*.tar.gz` **only**, so the `.zip` is
  **not** auto-attached to the Release — it is genuinely a manual upload until/unless the
  glob is widened. Documented, not yet changed.
- **Prerelease `vX.Y.Z-rc.N` / `-dev.N` / …** — build, cut a `--prerelease` GitHub
  Release with installable assets (`build-extension.yml:236,249`). The `dist` branch and
  the published Docker tags are **left untouched** (the stable install channels must
  never receive a prerelease).

## 6. Docker (`ghcr.io/nicsuzor/aops-crew`) — LIVE

The crew/worker image (root `Dockerfile`) is the polecat runtime: Claude Code + Gemini +
agy + the aops framework. It is published on **stable tags only** (`:vX.Y.Z` + `:latest`,
`build-extension.yml:212–221`), from the tagged `dev` commit. The Dockerfile installs the
framework **from the published `dist` distribution, not from source** — `dev` is the
source trunk and carries no built `dist/`, so the framework is cloned from the `dist` ref
(`Dockerfile:114–121`). No pkb binary is baked: PKB ships as a remote MCP server
(`Dockerfile:158–159`; [[project_no_dist_build]]).

## 7. Version & uv.lock — never out of sync (the technique) — LIVE

The standard release-please + uv discipline; release-please is the single source of truth
and CI is fail-closed on drift.

1. **release-please owns the version** — `.release-please-manifest.json` is the SSoT.
2. **It propagates that version into every version-bearing file** in the Release PR via
   `extra-files` (pyproject + 4 templates). Committed files always equal the next release.
3. **It regenerates `uv.lock` in the same PR**, so the lockfile's embedded project version
   tracks `pyproject.toml`.
4. **`uv sync --frozen` is the CI gate** (`build-extension.yml:83`, plus the container
   venv pre-bake). A lockfile that disagrees with `pyproject.toml` cannot build, so it
   cannot release.
5. **By construction**, the instant the Release PR merges, `dev`'s committed version ==
   the tag == the published release. Between releases `dev` shows the last release; the
   next Release PR is the only thing that advances it. Build-time `X.Y.Z-dev.N+sha`
   strings (`scripts/build.py`) are ephemeral display metadata, never committed — they
   cannot drift the files.

**Hardening — so it is _never_, not _usually_, in sync (all LIVE):**

- **G1 — stable version comes from the tag (LIVE).** A stable build sets the version from
  `${tag#v}` and explicitly does **not** run `scripts/version.py --get`, which would run
  `git describe --dirty` on a tree the build has already dirtied and emit
  `…-dev.0+gSHA.dirty` (`build-extension.yml:92–98`).
- **G2 — publish-time assertion (LIVE).** Before publishing a stable release, the workflow
  asserts `tag == pyproject $.project.version == manifest`; aborts otherwise, fail-closed
  (`build-extension.yml:111–123`).
- **G3 — local lockfile guard (LIVE).** A pre-commit `uv lock --check` catches lockfile
  drift before CI (`.pre-commit-config.yaml:132–134`, hook `uv-lock-check`).

## 8. Open reality — three things the maintainer left OPEN

These are documented as **current reality + honest open questions**. The maintainer has
**not** decided the resolutions; this spec does **not** invent them.

### 8.1 Type checker — RUNS but is NOT a gate (advisory, by decision)

`typecheck.yml` ("Type Check", basedpyright) **runs** — it is wired both as a
`workflow_call` reusable (via the triage orchestrator) and on `push: [dev]`
(`typecheck.yml:10–12`). But `Type Check / Type Check` is **deliberately NOT a required
gate**: it is commented out of the ruleset's required checks
(`.github/rulesets/pr-review-and-merge.yml:104`), disabled `2026-05-17` pending the
basedpyright burn-down. The gate was hollowed out by 10+ prior suppression commits and
emits 236 pre-existing errors on every PR; re-adding it would gate on noise.

- **Status:** advisory until debt task **`aops-1c3de214`** closes.
- **Acceptance to re-gate (recorded in the ruleset):** basedpyright returns **0 errors on
  a clean clone**. DO NOT re-add `Type Check / Type Check` to required checks before then.

### 8.2 Alignment (pauli) — NOT wired into CI; manual stand-in only

Alignment is **SPEC-ONLY (Phase 6 of [[pr-pipeline-v2]])**. As of today:

- **There is no `alignment-status` check, no alignment workflow, no host dispatch** wired
  into CI. [[pr-pipeline-v2]] §6 describes the eventual light host-side dispatch; none of
  it is live.
- **The live way to run an alignment check is the MANUAL `/strategic-review` skill**
  (`aops-core/skills/strategic-review/SKILL.md`); `--critic` runs a fast pauli-only
  pre-hoc critique. The maintainer invokes it by hand when they want alignment input
  before admitting a PR.
- **Current model:** alignment is **advisory input to the human admit gate** (§3.3),
  produced manually via `/strategic-review --critic`, until Phase 6 wires the host-side
  dispatch. A host outage degrades advice; it never deadlocks a merge (there is nothing to
  deadlock on, because there is no required alignment status).

### 8.3 Advisory / non-fatal findings are NOT tracked to closure — OPEN design question

**Fatal findings are robustly tracked. Non-fatal/advisory findings are not.** This is a
real, currently-open gap.

- **Fatal (tracked, LIVE).** A `CHANGES_REQUESTED` review turns a required status red; a
  new SHA auto-re-reviews; and `agent-merge-prep.yml`'s success path **refuses to approve
  while any `CHANGES_REQUESTED` review stands undismissed** (it counts the latest review
  per author, sets `merge-prep-status: failure`, and `exit 1` — see the success-path
  guard, `agent-merge-prep.yml` ≈ lines 293–311). So a fatal finding cannot merge
  silently.
- **Non-fatal (NOT tracked).** `COMMENT`-level reviews, "Deferred" rows in merge-prep's
  triage table, and alignment notes have **no machine mechanism** ensuring they are
  addressed. They can merge silently. The **only** safety net is the human reading
  merge-prep's triage table at the admit gate.

**Status: OPEN — the maintainer has NOT decided whether to close this.** One candidate
middle-path is to **require every non-"Fixed" triage row to carry a PKB task id** (so a
deferred/advisory finding becomes a tracked task rather than vanishing). This is recorded
as a **candidate only — UNDECIDED, not adopted.** Do not implement it as if settled.

## 9. Fixes — the gap between this contract and current reality

Status legend: **LIVE** (on `origin/dev`) · **PENDING** · **DONE-by-owner**.

**A · Release/publish (`build-extension.yml`)**

- **A1 — LIVE.** Stable build derives version from the tag, not dirty `version.py --get`
  (G1).
- **A2 — LIVE.** `tag == pyproject == manifest` assertion before publish (G2).
- **A3 — LIVE.** Docker build+push of `ghcr.io/nicsuzor/aops-crew:vX.Y.Z` + `:latest` on
  stable tags.

**B · Docker image (`Dockerfile`)**

- **B1 — LIVE.** No pkb-binary install step — pkb is a remote MCP since PR #1615
  ([[project_no_dist_build]]); `Dockerfile:158–159` documents this.
- **B2 — LIVE.** The framework install clones the `dist` ref (`dev` = source, no built
  `dist/`), not the default branch (`Dockerfile:114–121`).

**B-mirror · Cowork mirror retirement**

- **LIVE.** The orphaned `nicsuzor/aops` full-mirror step was removed in `cf5320de` (and
  the cowork build that replaced it landed in `20549c70`); both are on `origin/dev`.
  Cowork now ships via `aops-cowork` on `dist` + the `aops-coworklocal` ZIP (§2).

**G · Version/uv.lock hardening**

- **G1 / G2 / G3 — LIVE** (see §7). G1+G2 in `build-extension.yml`; G3 in
  `.pre-commit-config.yaml` (`uv-lock-check`).

**C · Complete v2 merge gate** (see [[pr-pipeline-v2]] §11, Phases 4–6)

- **C1 — DONE-by-owner.** The v2 ruleset is applied to live `13762049`: `0` approvals +
  required `Lint / Lint`, `Pytest / Pytest`, `enforcer-status`, `qa-status`,
  `admit-status`, in ONE atomic change (no bypass window). Synced by the owner this
  session (§3.1).
- **C2 — DONE-by-owner (part of C1).** `admit-status` is required and is set only by the
  Environment-gated admission job on maintainer approval.
- **C3 — PENDING.** Repurpose `agent-merge-prep.yml` into the Stage-2 dev agent; retire
  the v1 retire-mechanic / per-PR no-op dispatch (`merge-prep-cron.yml`).
- **C4 — PENDING.** Remove the duplicate enforcer/qa invocation (orchestrator +
  `trigger-*.yml` both fire on `pull_request`).
- **C5 — PENDING.** `merge-prep.agent.md` hardcodes `origin/main` as the PR base
  (confirmed: `git merge origin/main`, lines 35/55/60); change to `dev`.

**D · gh state / branches / stale files**

- **D1 — PENDING.** Delete `academicOps` `main` after one clean stable release verifies
  `@dist` + Cowork delivery.
- **D2 — PENDING.** Delete `auto-retarget-pr.yml` — its rationale (keep default = `main`)
  is obsolete now that `dev` is default. (Until removed, it auto-retargets PRs off `main`;
  see [[project_release_pipeline_default_branch]].)
- **D3 — PENDING.** Fix the stale `origin/HEAD → origin/main` pointer; prune dead local
  branches.

## 10. Cross-references

- [[pr-pipeline-v2]] — the merge half (PR → merged on `dev`): convergence mechanics,
  per-agent contract, the `pr-fix-loop` admit gate, the loop-skip protocol. **Read it for
  merge-gate detail; this spec does not duplicate it.**
- [[project_dist_branch_migration]] — the de-inversion decision (#1616).
- [[project_release_pipeline_default_branch]] — the default-branch-trigger bug class the
  migration dissolves (and D2's rationale).
- [[project_no_dist_build]] — pkb-is-a-remote-MCP (B1).
- `.github/workflows/{release-please,build-extension,typecheck}.yml`,
  `.github/rulesets/pr-review-and-merge.yml`, `.github/agents/merge-prep.agent.md`,
  `.github/workflows/agent-merge-prep.yml`, `Dockerfile`, `.pre-commit-config.yaml`,
  `scripts/build.py`.
