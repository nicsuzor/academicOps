---
id: spec-image-staleness-detection
title: "Polecat Container Image Staleness Detection & Surfacing"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, provenance, staleness]
---

# Polecat Container Image Staleness Detection & Surfacing

Implemented in `lib/polecat/staleness.py`, wired into `lib/polecat/cli.py`,
`plugins/orchestrate/hooks/handlers.py`, `Dockerfile`, `Makefile`, and
`build/build.py`. Tests: `tests/polecat/test_image_staleness.py`,
`tests/polecat/test_run_record.py`.

## The failure mode

A polecat container gets its plugin payload — skills, hooks, agents, MCP wrappers
— **baked into the image at build time**, while the code under test is
**bind-mounted at launch** (`/workspace`). These are two different delivery paths,
and only one of them updates when a file is edited
([polecat-system.md](polecat-system.md), Guarantees 5 and 6).

So an operator who edits plugin code and dispatches without `make docker-build`
runs the _old_ plugins against the _new_ workspace. The stale code usually
executes without error, produces a plausible result, and the field test is graded
a pass. That is a silent false green: the change under test never ran, and nothing
in the output says so.

The detector's whole job is to make that state legible before the run starts.

## Binding constraints

1. **Warn, never refuse.** Detected staleness emits unmissable warnings to both
   operator and agent, and never aborts, refuses to launch, or changes the exit
   code. Hard refusal would break legitimate scenarios: verifying backwards
   compatibility, benchmarking against a frozen release baseline, and running
   offline when a rebuild is unavailable.
2. **Remote-sourced images are not false-stale.** `Dockerfile` builds from two
   sources selected by `AOPS_DIST_SOURCE`: `local` copies this checkout's `dist/`
   (`make docker-build`), `remote` clones the published `dist` branch from
   `AOPS_REPO_URL` at `AOPS_DIST_REF` (CI). A `remote` image is _designed_ to lag
   local unreleased commits, so a detector that treats all difference as staleness
   fires on every CI image. Remote images are identified as a release baseline, not
   flagged.
3. **No log-grepping.** The version and staleness state are legible on the host
   CLI, in the in-container `SessionStart` banner, and in `run.json`. No operator
   or reviewer should need to grep JSONL to learn what plugin version executed.

## Build-time provenance

Comparison has to be instantaneous at dispatch, so provenance is stamped at build
time rather than inspected inside a container.

`build/build.py` writes `.aops-image-metadata.json` into the dist root; the
`Dockerfile` copies it to `/home/worker/.aops-image-metadata.json`:

```json
{
  "schema_version": "1.0",
  "aops_version": "0.9.1",
  "dist_source": "local",
  "commit_sha": "f31ebcf7eb4b8d6dc6f6646a6ad3e9ade45ef1ba",
  "short_sha": "f31ebcf7",
  "is_dirty": false,
  "dist_ref": "dev",
  "repo_url": "https://github.com/nicsuzor/academicOps.git",
  "built_at": "2026-08-29T00:20:00Z",
  "plugins": {
    "aops": "0.9.1+gf31ebcf7",
    "pkb": "0.9.1+gf31ebcf7",
    "orchestrate": "0.9.1+gf31ebcf7"
  }
}
```

The same facts are attached as image labels, which is what the host reads without
starting a container:

```dockerfile
LABEL org.opencontainers.image.revision="${AOPS_BUILD_COMMIT}" \
      org.opencontainers.image.version="${AOPS_VERSION}" \
      aops.dist_source="${AOPS_DIST_SOURCE}" \
      aops.dist_ref="${AOPS_DIST_REF}" \
      aops.build_dirty="${AOPS_BUILD_DIRTY}"
```

`make docker-build` and the CI `build-extension.yml` supply
`AOPS_BUILD_COMMIT=$(git rev-parse HEAD)` and `AOPS_BUILD_DIRTY` from
`git status --porcelain`.

## Evaluation

`inspect_image_provenance(image)` reads the labels via
`docker image inspect --format '{{json .Config.Labels}}'`. Where labels are absent
or `docker inspect` is unavailable, it degrades to a provenance record with an
empty `commit_sha`, inferring `dist_source` from whether the image reference
contains `remote`. An empty `commit_sha` compares as not-stale: an unlabelled
image is unknown, and the constraint is to warn on evidence, not on ignorance.

`evaluate_staleness()` compares that against a workspace baseline, which differs
by dispatch mode:

| Dispatch mode                    | Workspace baseline                                                          |
| -------------------------------- | --------------------------------------------------------------------------- |
| `-d <path>` (direct mount)       | `git -C <path> rev-parse HEAD`, plus `git status --porcelain` for dirtiness |
| `-p` / `--base` (isolated clone) | the `base_sha` resolved by `resolve_isolated_workspace()` — never dirty     |
| default (no `-d`, no `--base`)   | same as `-p`: the resolved base, which is the upstream tracking HEAD        |

SHA comparison is prefix-tolerant in both directions, so a short SHA on either
side still matches.

| Image source | Workspace state                                          | State                     | Output                      |
| ------------ | -------------------------------------------------------- | ------------------------- | --------------------------- |
| `local`      | commit matches, clean                                    | `FRESH_LOCAL_BUILD`       | Header, proceed             |
| `local`      | commit differs, image is at or past the release baseline | `FRESH_LOCAL_BUILD`       | Header, proceed             |
| `local`      | commit differs, image predates the release baseline      | `STALE_LOCAL_BUILD`       | **Warning banner**, proceed |
| `local`      | commit matches, tree dirty                               | `DIRTY_WORKSPACE_UNBAKED` | **Warning banner**, proceed |
| `remote`     | commit matches                                           | `FRESH_REMOTE_BUILD`      | Header, proceed             |
| `remote`     | commit differs                                           | `REMOTE_RELEASE_RUN`      | Header, proceed             |

`DIRTY_WORKSPACE_UNBAKED` fires only where the workspace is dirty and the image
was _not_ built dirty: an image stamped `aops.build_dirty=1` already contains
uncommitted work, so the difference is expected. Neither `remote` state sets
`is_stale`, and neither ever emits the warning banner — that is constraint 2
enforced in one place.

### `STALE_LOCAL_BUILD` compares against a release baseline, not raw HEAD

A raw SHA mismatch between the image and workspace HEAD is not, by itself,
evidence of staleness worth an operator's attention: two commits differing
only by dev-loop churn since the last release (a banner-text tweak, an
em-dash fix) are both correct, and warning on that difference trains the
operator to ignore the banner. `STALE_LOCAL_BUILD` instead fires only when
the image is missing a release checkpoint the workspace has already reached:

1. If `image_commit == workspace_sha` (prefix-tolerant), the image is fresh —
   no baseline lookup is needed.
2. Otherwise, resolve the release baseline: the highest `vX.Y.Z`-tagged commit
   reachable from `workspace_sha` (`git tag --merged <workspace_sha>`,
   filtered to exact `major.minor.patch` tags — pre-release suffixes like
   `-rc.1` or `-beta.2` do not count, and `--merged` already excludes a tag
   cut on a branch that never merged into the workspace's own history, so an
   abandoned release line is never picked up as the baseline). This is
   re-derived on every call: tag and branch topology in this repo is a dated
   observation, never a standing property (`kb_3a091c50`), so nothing here
   trusts a cached ref name.
3. If no release tag is reachable from the workspace (a shallow test
   fixture, or a repo with no tags yet), there is no baseline to measure
   "behind" against — fall back to the plain-inequality signal so detection
   is never silently disabled.
4. If a release baseline is found, the image is stale only when it does
   **not** contain that baseline commit (`git merge-base --is-ancestor
   <release_sha> <image_commit>` fails) — i.e. the image was built before the
   release was cut. An image that already contains the release baseline is
   `FRESH_LOCAL_BUILD` even when its SHA differs from workspace HEAD; its
   `plugins_version_str` and header banner say `local:current` /
   `[local, current release baseline]` rather than `local:match`, since the
   SHAs genuinely differ.

`aops_97952fe5` (whether a detected mismatch should hard-fail or auto-rebuild
rather than warn) and `aops_81849370` (why a successful `make docker-build`
can be immediately followed by a stale-warning launch) are separate, open
concerns about this same detector; neither is resolved by the release-baseline
comparison described here.

## Surfacing

### Host CLI

`run` writes the banner to **stderr**, not stdout, and suppresses it under
`--quiet` — polecat's stream-separation guarantee
([polecat-system.md](polecat-system.md), Guarantee 7) applies to these banners
like any other polecat prose.

Fresh local:

```text
================================================================================
POLECAT DISPATCH: session-9317829f [agy]
Workspace: /home/nic/.aops/worktrees/session-9317829f (commit: f31ebcf7)
Image:     ghcr.io/nicsuzor/aops-crew:latest (local build @ f31ebcf7)
Status:    PLUGINS FRESH [local match]
================================================================================
```

Stale local:

```text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
WARNING: POLECAT IMAGE PLUGINS ARE STALE
The plugins baked into this container image DO NOT MATCH the workspace under test!
- Baked Image Commit:    62456fff (built: 2026-08-20)
- Workspace Test Commit: f31ebcf7
- Impact:                Container agent will execute OLD plugins/skills/hooks.
- Remedy:                Run `make docker-build` to rebuild with current source.
Proceeding with execution (warn-only policy enabled)...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

Remote release:

```text
================================================================================
POLECAT DISPATCH: session-9317829f [claude]
Workspace: /home/nic/.aops/worktrees/session-9317829f (branch: feat/new-api @ b47025df)
Image:     ghcr.io/nicsuzor/aops-crew:v0.9.1 (remote release @ v0.9.1)
Status:    REMOTE RELEASE IMAGE [testing against released plugin baseline]
================================================================================
```

### In-container `SessionStart` hook

`run` sets four container variables (declared in `lib/polecat/env_contract.py`'s
`FORWARDED_ENV`, so their values reach the container through the `docker`
process's own environment rather than on argv): `AOPS_IMAGE_PROVENANCE` (the full
record as JSON),
`AOPS_IMAGE_STALE` (`0`/`1`), `AOPS_IMAGE_PLUGINS_VERSION`, and — only when stale
— `AOPS_IMAGE_STALENESS_WARNING`.

`plugins/orchestrate/hooks/handlers.py` reads them, falling back to
`/home/worker/.aops-image-metadata.json`, and appends the version to the session
metadata line:

```text
session: session-9317829f | time: 2026-08-29 10:25:00 +1000 | host: polecat-worker-01 | cwd: /workspace | plugins: 0.9.1+gf31ebcf7 (local:match)
```

When stale, it injects the warning into the agent's own context, so the agent
grades its own session correctly rather than reporting a pass on payload it did
not test:

```text
[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]
Container plugin payload (commit 62456fff) lags workspace under test (commit f31ebcf7).
Any skill, hook, or MCP behavior verified in this session reflects the BAKED payload, NOT workspace edits.
```

### `run.json`

`run.json` carries a `plugin_provenance` object so automated evaluation can
discriminate a real pass from a stale-payload pass without reading banners:

```json
{
  "plugin_provenance": {
    "image_source": "local",
    "image_commit": "62456fff",
    "workspace_commit": "f31ebcf7",
    "is_stale": true,
    "staleness_reason": "image commit 62456fff behind workspace commit f31ebcf7",
    "staleness_status": "STALE_LOCAL_BUILD"
  }
}
```
