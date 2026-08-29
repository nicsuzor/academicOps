# Specification: Polecat Container Image Staleness Detection & Surfacing

- **Task:** [[aops_866c0666]]
- **Epic:** [[aops_1787bc75]]
- **Downstream Review Gate:** [[aops_2dfd22a8]]
- **Downstream Implementation:** [[aops_40a3faa8]]
- **Downstream Verification Gate:** [[aops_7af9c46e]]
- **Status:** Draft / Ready for Review
- **Author Identity:** Antigravity Engineering Agent
- **Target Subsystems:** `lib/polecat/cli.py`, `plugins/orchestrate/hooks/handlers.py`, `Dockerfile`, `build/marketplace.py`

---

## 1. Problem Statement & Root Cause

### 1.1 The Silent False-Green Failure Mode
Polecat executes worker agents inside container environments where plugin payloads (skills, hooks, agents, MCP tool wrappers) are **baked into the Docker image** at build time (`Dockerfile:313-349`). Conversely, the workspace code under test is bind-mounted at container launch (`/workspace` via `-v ${workspace_dir}:/workspace`, `lib/polecat/cli.py:1450`).

When an operator modifies plugin code, hooks, or skills in the host workspace and dispatches a test run via `polecat run` without first executing `make docker-build`, the container runs the **stale plugin code baked into the image** rather than the modified code under test.

Because the stale plugin code often executes without errors, the field test produces a plausible result that is graded as a **PASS**, creating a silent false green:

```
+-------------------------------------------------------------------------------+
| HOST WORKSPACE                                                                |
| Modified plugin/skill under test (e.g. v0.9.1 HEAD @ f31ebcf7)                |
+-------------------------------------------------------------------------------+
                                |  (bind mounted to /workspace)
                                v
+-------------------------------------------------------------------------------+
| POLECAT CONTAINER                                                             |
| /workspace (mounted): contains new source                                      |
| ~/.claude/plugins/cache (baked): contains OLD build (e.g. 0.8.0-g62456fff)    |
| -> Agent loads baked cache; new skill/hook changes NEVER execute              |
| -> Result: SILENT FALSE GREEN                                                 |
+-------------------------------------------------------------------------------+
```

### 1.2 Historical Evidence
- **Observed 2026-08-24 (`aops_1787bc75`):** Field test of the `workflow-library` skill in `polecat run agy -d /home/nic/src/academicOps`.
  - Tool-call grep: `grep -c "workflow-library" /tmp/agy2.jsonl` -> **0** (skill never loaded).
  - Tool-call grep: `grep -c "agents/templates" /tmp/agy2.jsonl` -> **0** (project tier never inspected).
  - Verbatim tool-call execution: `"CommandLine":"ls -la /home/worker/.claude/plugins/cache/academicOps/pkb/0.8.0-g62456fff/workflows/process/"`.
  - The run executed plugins from `0.8.0-g62456fff`, predating the changes under test, yet returned a plausible three-tier listing graded as a pass.

### 1.3 World-State Verification & Lost Commitments
1. **Hook Metadata (`plugins/orchestrate/hooks/handlers.py:55-77`):** `_format_session_metadata()` currently emits only `session`, `time`, `host`, and `cwd`. No plugin or image version field is present.
2. **Superseded Ruling (`mem_724fbde2`):** A 2026-07-15 ruling promised installed-version output in `aops/hooks/router.py`. That file was deleted during the hook-dispatch refactoring (`v0.9.0`), and the version field was not ported to `plugins/orchestrate/hooks/handlers.py`.
3. **Dual Build Sources (`Dockerfile:17-33`):** `Dockerfile` supports two build sources via `AOPS_DIST_SOURCE`:
   - `local`: copies `dist/` from local build context (`make docker-build`). Intended to reflect local development.
   - `remote`: clones the published `dist` branch from `AOPS_REPO_URL` at `AOPS_DIST_REF` (used in CI/CD). Intended to reflect official published releases.
   - A `remote`-sourced image naturally lags local unreleased source commits. A staleness detector that treats all difference as staleness will trigger false positives on every `remote`-sourced image.

---

## 2. Binding Constraints & Invariants

The following constraints are binding on this specification:

1. **Warn, Never Refuse (Parent Assumption `aops_1787bc75:90-93`):**
   - Detecting that an image lags workspace source MUST emit loud, unmissable warnings to both the operator and the agent.
   - Detecting staleness MUST **NEVER abort, refuse to launch, or exit non-zero**.
   - *Rationale:* Hard refusals break legitimate testing scenarios (e.g., verifying backwards compatibility, benchmarking against frozen release baselines, running offline when Docker rebuilds are unavailable).
2. **Distinct Dispatch Mode Baselines:**
   - Staleness must be evaluated against the appropriate reference baseline for each dispatch mode (`-d`, `-p`/`--base`, `remote`).
3. **Remote-Sourced Images Are Not False-Stale:**
   - A container built with `AOPS_DIST_SOURCE=remote` MUST NOT be flagged as a stale build when running against newer local code. It must be explicitly identified as a *Remote Release Build* operating against its declared release ref.
4. **Zero Log-Grepping UX:**
   - Version metadata and staleness state must be immediately legible on host CLI stdout, within the in-container `SessionStart` hook banner, and in machine-readable `run.json`. No operator or reviewer should need to grep JSONL logs to determine what plugin version executed.

---

## 3. Image Build-Time Provenance Architecture

To allow instantaneous, deterministic staleness comparison without running slow in-container inspections, the build pipeline will stamp provenance metadata at image build time.

### 3.1 Build Metadata Schema
During image build, a metadata file `/home/worker/.aops-image-metadata.json` is generated and baked into the image, and corresponding Docker labels are attached to the image configuration:

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

### 3.2 Dockerfile Stamping Implementation
In `Dockerfile`:
```dockerfile
ARG AOPS_DIST_SOURCE=remote
ARG AOPS_REPO_URL
ARG AOPS_DIST_REF
ARG AOPS_BUILD_COMMIT
ARG AOPS_BUILD_DIRTY
ARG AOPS_VERSION

LABEL org.opencontainers.image.revision="${AOPS_BUILD_COMMIT}" \
      org.opencontainers.image.version="${AOPS_VERSION}" \
      aops.dist_source="${AOPS_DIST_SOURCE}" \
      aops.dist_ref="${AOPS_DIST_REF}" \
      aops.build_dirty="${AOPS_BUILD_DIRTY}"
```
`Makefile` (`docker-build` target) and `build-extension.yml` (CI) pass `--build-arg AOPS_BUILD_COMMIT=$(git rev-parse HEAD)` and `--build-arg AOPS_BUILD_DIRTY=$(git status --porcelain | wc -l)` automatically.

---

## 4. Comparison Mechanism per Dispatch Mode

The staleness evaluation algorithm computes two entities at runtime:
1. `ImageProvenance`: Read from image Docker labels via `docker image inspect` or `/home/worker/.aops-image-metadata.json`.
2. `WorkspaceBaseline`: Computed from the target workspace ref and working tree state.

### 4.1 Dispatch Mode 1: Direct Directory Mount (`-d <path>`)

- **Context:** Operator passes `-d /path/to/repo` to mount a host checkout directly into `/workspace`.
- **Values Read:**
  - **Image (Build Time):** `ImageProvenance.dist_source`, `ImageProvenance.commit_sha`, `ImageProvenance.is_dirty`.
  - **Workspace (Run Time):**
    - `workspace_sha`: Computed via `git -C <path> rev-parse HEAD`.
    - `workspace_dirty`: Computed via `git -C <path> status --porcelain`.
- **Comparison Logic:**
  1. If `ImageProvenance.dist_source == "local"`:
     - If `ImageProvenance.commit_sha != workspace_sha`:
       - **State:** `STALE_LOCAL_BUILD`
       - **Detail:** Image baked at `ImageProvenance.short_sha`, workspace at `workspace_sha[:8]`.
     - Else if `workspace_dirty` is True and not `ImageProvenance.is_dirty`:
       - **State:** `DIRTY_WORKSPACE_UNBAKED`
       - **Detail:** Image matches HEAD commit but host workspace has uncommitted changes not baked into the image.
     - Else:
       - **State:** `FRESH_LOCAL_BUILD`
  2. If `ImageProvenance.dist_source == "remote"`:
     - **State:** `REMOTE_RELEASE_RUN`
     - **Detail:** Running against remote release image (`AOPS_DIST_REF`). Informational notice emitted; not flagged as stale local build.

### 4.2 Dispatch Mode 2: Isolated Clone (`-p <name>` / `--base <ref>`)

- **Context:** Polecat creates an isolated per-session clone at `<polecat_home>/worktrees/<session_id>` from the canonical repository using `resolve_isolated_workspace()`.
- **Values Read:**
  - **Image (Build Time):** `ImageProvenance.dist_source`, `ImageProvenance.commit_sha`.
  - **Workspace (Run Time):**
    - `base_sha`: The resolved base commit SHA selected by `resolve_isolated_workspace()` (after remote fetch verification per [[spec-base-ref-resolution.md]]).
- **Comparison Logic:**
  1. If `ImageProvenance.dist_source == "local"`:
     - If `ImageProvenance.commit_sha != base_sha`:
       - **State:** `STALE_LOCAL_BUILD`
       - **Detail:** Image baked at `ImageProvenance.short_sha`, isolated workspace cloned from `base_sha[:8]`.
     - Else:
       - **State:** `FRESH_LOCAL_BUILD`
  2. If `ImageProvenance.dist_source == "remote"`:
     - If `ImageProvenance.commit_sha == base_sha`:
       - **State:** `FRESH_REMOTE_BUILD`
     - Else:
       - **State:** `REMOTE_RELEASE_RUN`
       - **Detail:** Remote image (`AOPS_DIST_REF` @ `ImageProvenance.short_sha`) executing against workspace branch based on `base_sha[:8]`.

### 4.3 Dispatch Mode 3: Remote-Sourced Image (`AOPS_DIST_SOURCE=remote`)

- **Context:** Container image was built from published distribution artifacts in CI/CD.
- **Handling Rule:**
  - A remote image is designed to lag development branches.
  - The detector inspects `ImageProvenance.dist_source == "remote"`.
  - When detected, the detector sets `is_stale = False` and sets `status_category = "REMOTE_RELEASE"`.
  - The CLI outputs a neutral notice: `[INFO] Image source: remote (published ref: <AOPS_DIST_REF> @ <short_sha>)`.
  - It **strictly avoids** emitting `[WARNING: STALE IMAGE]`.

### 4.4 Default Case: No Arguments (Default Workspace, No `--base`)

- **Context:** `polecat run <agent>` with no `-d` and no `--base`.
- **Definition of "Current Source":**
  - Per Rule 1 of [[spec-base-ref-resolution.md]], when `--base` is omitted, the base ref defaults to the upstream tracking HEAD of the canonical repo (e.g. `origin/dev`), or local HEAD if detached/no upstream.
  - `workspace_sha` is resolved to `upstream_head_sha`.
  - Comparison proceeds identically to Mode 2 against `upstream_head_sha`.

---

## 5. Quadrant Analysis Matrix

| Dispatch Mode | Image Source | Workspace State | Evaluated State | Warning Level | Action |
|---|---|---|---|---|---|
| `-d <path>` | `local` | Workspace HEAD == Image SHA, Clean | `FRESH_LOCAL` | None (Green) | Proceed quietly |
| `-d <path>` | `local` | Workspace HEAD != Image SHA | `STALE_LOCAL` | **LOUD WARNING** | Print banner, proceed |
| `-d <path>` | `local` | Workspace HEAD == Image SHA, Dirty | `DIRTY_UNBAKED` | **LOUD WARNING** | Print banner, proceed |
| `-d <path>` | `remote` | Host Repo on Feature Branch | `REMOTE_RELEASE` | Info (Notice) | Print info header, proceed |
| `-p` / `--base` | `local` | `base_sha` == Image SHA | `FRESH_LOCAL` | None (Green) | Proceed quietly |
| `-p` / `--base` | `local` | `base_sha` != Image SHA | `STALE_LOCAL` | **LOUD WARNING** | Print banner, proceed |
| `-p` / `--base` | `remote` | `base_sha` == Image SHA | `FRESH_REMOTE` | None (Green) | Proceed quietly |
| `-p` / `--base` | `remote` | `base_sha` != Image SHA | `REMOTE_RELEASE` | Info (Notice) | Print info header, proceed |
| Default (no args) | `local` | Canonical Upstream != Image SHA | `STALE_LOCAL` | **LOUD WARNING** | Print banner, proceed |
| Default (no args) | `remote` | Canonical Upstream != Image SHA | `REMOTE_RELEASE` | Info (Notice) | Print info header, proceed |

---

## 6. Surfacing Points & UX/API Contracts

Staleness and version information must be surfaced across three distinct tiers:

### 6.1 Tier 1: Host CLI Stdout Banner (`lib/polecat/cli.py`)
Printed directly to terminal stdout before container invocation. Reaches human operators, dispatchers, and CI logs without grepping files.

#### Fresh Local Image Header:
```text
================================================================================
POLECAT DISPATCH: session-9317829f [agy]
Workspace: /home/nic/.aops/worktrees/session-9317829f (commit: f31ebcf7)
Image:     ghcr.io/nicsuzor/aops-crew:latest (local build @ f31ebcf7)
Status:    PLUGINS FRESH [local match]
================================================================================
```

#### Stale Local Image Warning Banner:
```text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
WARNING: POLECAT IMAGE PLUGINS ARE STALE
The plugins baked into this container image DO NOT MATCH the workspace under test!
- Baked Image Commit:    0.8.0-g62456fff (built: 2026-08-20)
- Workspace Test Commit: 0.9.1+gf31ebcf7 (lag: 14 commits behind)
- Impact:                Container agent will execute OLD plugins/skills/hooks.
- Remedy:                Run `make docker-build` to rebuild with current source.
Proceeding with execution (warn-only policy enabled)...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

#### Remote Release Image Header:
```text
================================================================================
POLECAT DISPATCH: session-9317829f [claude]
Workspace: /home/nic/.aops/worktrees/session-9317829f (branch: feat/new-api @ b47025df)
Image:     ghcr.io/nicsuzor/aops-crew:v0.9.1 (remote release @ v0.9.1)
Status:    REMOTE RELEASE IMAGE [testing against released plugin baseline]
================================================================================
```

### 6.2 Tier 2: In-Container SessionStart Hook (`plugins/orchestrate/hooks/handlers.py`)
Injected directly into the agent's context and recorded in `polecat-session-hooks.jsonl` and session transcripts.

#### Metadata Line:
Extended `_format_session_metadata()`:
```text
session: session-9317829f | time: 2026-08-29 10:25:00 +1000 | host: polecat-worker-01 | cwd: /workspace | plugins: 0.9.1+gf31ebcf7 (local:match)
```

#### Injected Hook Warning (if stale):
If `AOPS_IMAGE_STALENESS_WARNING` is passed via container environment:
```text
[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]
Container plugin payload (commit 62456fff) lags workspace under test (commit f31ebcf7).
Any skill, hook, or MCP behavior verified in this session reflects the BAKED payload, NOT workspace edits.
```

### 6.3 Tier 3: Machine-Readable `run.json` Schema
`run.json` (written by `lib/polecat/cli.py` on container completion) records structured provenance for automated evaluation:

```json
{
  "session_id": "session-9317829f",
  "status": "success",
  "exit_code": 0,
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

---

## 7. Implementation Architecture & Data Flow

```
+-----------------------------------------------------------------------------+
| 1. BUILD TIME: make docker-build                                            |
|    - Computes git rev-parse HEAD & git status                               |
|    - Injects labels into Dockerfile & writes .aops-image-metadata.json      |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| 2. DISPATCH TIME: polecat run (lib/polecat/cli.py)                          |
|    - Inspects image labels (docker image inspect --format ...)              |
|    - Resolves workspace commit (direct mount or resolve_isolated_workspace) |
|    - Runs evaluate_staleness(image_meta, workspace_meta, dispatch_mode)     |
|    - Prints stdout banner (Green / Stale Warning / Remote Info)             |
|    - Sets container env: AOPS_IMAGE_PROVENANCE, AOPS_IMAGE_STALE            |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| 3. RUN TIME: Container SessionStart Hook (handlers.py)                      |
|    - Reads AOPS_IMAGE_PROVENANCE & .aops-image-metadata.json                |
|    - Appends plugin version and status to _format_session_metadata()        |
|    - Injects system warning to agent if stale                               |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| 4. EXIT TIME: run.json persistence (lib/polecat/cli.py)                     |
|    - Writes structured plugin_provenance dictionary to run.json             |
+-----------------------------------------------------------------------------+
```

---

## 8. Integration Test Plan (TDD Specification for IMPLEMENT)

Unit and integration tests to be implemented in `tests/polecat/test_image_staleness.py`:

1. **`test_staleness_detection_local_fresh`:**
   - Image commit `f31ebcf7`, workspace commit `f31ebcf7`, source `local`.
   - Asserts `is_stale is False`, status `FRESH_LOCAL_BUILD`, warning banner not printed.
2. **`test_staleness_detection_local_stale`:**
   - Image commit `62456fff`, workspace commit `f31ebcf7`, source `local`.
   - Asserts `is_stale is True`, status `STALE_LOCAL_BUILD`, warning banner printed, returncode unaffected (warn-only).
3. **`test_staleness_detection_local_dirty_workspace`:**
   - Image clean at commit `f31ebcf7`, workspace dirty at commit `f31ebcf7`.
   - Asserts `is_stale is True`, status `DIRTY_WORKSPACE_UNBAKED`, warning banner printed.
4. **`test_staleness_detection_remote_lagging_local_not_flagged_stale`:**
   - Image source `remote` (`AOPS_DIST_REF=v0.9.1` @ `62456fff`), workspace at feature branch `f31ebcf7`.
   - Asserts `is_stale is False`, status `REMOTE_RELEASE_RUN`, warning banner NOT printed, info banner printed.
5. **`test_session_start_hook_surfaces_plugin_version`:**
   - Executes `handlers.session_start(ctx)` with mock provenance context.
   - Asserts metadata string contains `plugins: <version> (<source>:<status>)`.
6. **`test_run_json_records_provenance`:**
   - Executes container run simulation.
   - Asserts `run.json` contains valid `plugin_provenance` object.

---

## 9. Deliverable Summary & Downstream Handover

This specification delivers the complete design resolving all four requirements of `aops_866c0666`:
1. Concrete comparison mechanism defined per dispatch mode (`-d`, `-p`/`--base`, `remote`, and default).
2. Dual surfacing points specified (Host CLI stdout banner + In-container SessionStart hook + `run.json`).
3. Strict enforcement of the "warn, never refuse" invariant.
4. Explicit rule preventing false-positive staleness alerts on `remote`-sourced images.

Upon approval by the review gate [[aops_2dfd22a8]], implementation proceeds under [[aops_40a3faa8]].
