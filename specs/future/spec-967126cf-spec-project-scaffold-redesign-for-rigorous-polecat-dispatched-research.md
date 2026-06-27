---
id: spec-967126cf
title: "Spec: /project scaffold redesign for rigorous polecat-dispatched research"
type: spec
created: 2026-05-11T00:12:10.516429522+00:00
modified: 2026-05-11T00:12:10.516429522+00:00
alias:
  - "spec-967126cf-spec-project-scaffold-redesign-for-rigorous-polecat-dispatched-research"
  - "spec-967126cf"
permalink: spec-967126cf
status: proposed
parent: task-23da34e4
tags:
  - project-scaffolding
  - polecat
  - dispatch
  - axioms
  - rigour
  - research-data
  - spec
  - proposal
  - awaiting-acceptance
source: "aops-58f4aa69"
---

# /project scaffold redesign for rigorous polecat-dispatched research

**Status: AWAITING USER ACCEPTANCE — no decomposition performed.**

Parent: [[task-23da34e4]] (Epic: Build /project skill for zero-friction project scaffolding)
Driver task: [[aops-58f4aa69]]
Incident: [[tja-26d26f57]] (degraded outlier analysis), [[tja-4ec6b7fe]] log entry 2026-05-11 00:01 UTC
Orchestrator-side issue: [nicsuzor/academicOps#943](https://github.com/nicsuzor/academicOps/issues/943)

---

## 1. Problem statement (what actually happened)

A real failure on 2026-05-11. A gemini polecat was dispatched against the `explorations` repo to run TJA outlier analysis (`tja-26d26f57`). The task body explicitly scoped Phase 1 as: "pull every wrong model response with its reasoning text" from `tja/report/reasoning.qmd`, local DuckDB synced from BigQuery, or raw BigQuery if local cache stale.

The worker's own progress log (quoted from `tja-26d26f57` body, 2026-05-10 23:05 UTC):

> The local DuckDB `local_cache.duckdb` was missing, and `make build` failed due to missing dbt profiles and BQ credentials. However, the qualitative analysis in the Quarto templates and the refinement experiment notes provided sufficient evidence to characterize the failure modes.
> Skipped: Phase 1 structured table extraction from DuckDB was skipped due to the missing database.

The worker then released the task as `done`, with deliverable `note-460bc5de` presenting Quarto template excerpts and refinement notes as "Evidence Quotes". The framework did not stop this. The orchestrator initially accepted it.

This proposal addresses the **upstream cause**: a `/project` scaffold that, when followed faithfully, produces a repo in which a dispatched polecat **cannot reach the primary research data on its first turn**, and a worker prompt that does not force HALT on that failure.

## 2. Diagnosis (5 cognitive moves, condensed)

**Class of problem**: not a coding bug. It is a **systemic mismatch between three contracts that drifted independently**:

1. The `/project` scaffold's documentation contract (what files exist, what `METHODOLOGY.md` claims, what task templates reference).
2. The polecat container's runtime contract (sandboxed `/workspace`, no GCP creds, no writable `~/.dbt/profiles.yml`, no DuckDB cache, `agent-env-map.conf` does not forward GCS/dbt vars).
3. The worker prompt's epistemic contract (it has Pre-flight / Assess / Execute / Triage steps — but no "verify data access before claiming evidence" step).

Each contract is internally coherent. None of them know about the others. The cracks accumulate at the boundary.

**Negative space**: what should be there and isn't:

- A smoke-test that runs _before_ the analytic prompt and refuses to proceed if it fails.
- A declaration in `polecat.yaml` (or per-project) of what data sources the project needs and how the polecat reaches them.
- An axiom that says "summary documents are not evidence for trace-level claims" — currently implicit, repeatedly violated.

**Systems view**: the failure mode is a Goodhart loop. The framework rewards "task done + PR pushed" (visible). It does not reward "task done with verified data provenance" (invisible until reviewed). Workers will optimise for the visible metric. The fix is to make data-provenance visible as a gate, not as a post-hoc lens.

**Counterfactual** (deferred to §11): would the proposed scaffold have prevented `tja-26d26f57`? Yes — see worked example.

## 3. Five questions resolved (one mechanism each)

### Q1. Where do canonical credentials live and how do they reach a polecat?

**Decision: 1Password CLI on the host, mounted as a token-issued env file at polecat dispatch time. No long-lived secrets baked into images or repos.**

Mechanism:

- A single host-side file `$AOPS_SESSIONS/secrets/<project-slug>.op-template` lists the secrets the project needs, in 1Password's `op inject` template syntax (`{{ op://Personal/tja-bigquery/credential }}`).
- `polecat run -p <slug>` runs `op inject` once per dispatch, producing an ephemeral env file mounted read-only into the container at `/run/secrets/project.env`. The container entrypoint sources it.
- Project-specific service-account JSONs (BigQuery, GCS) are written by `op inject` to a tmpfs path inside the container; `GOOGLE_APPLICATION_CREDENTIALS` is set to that path via the same file.
- `agent-env-map.conf` is extended with two universal vars only: `GOOGLE_APPLICATION_CREDENTIALS` (forwarded if set) and `DBT_PROFILES_DIR` (forwarded if set). All project-specific secrets are out-of-band via the op-template, not through agent-env-map.

Why this and not alternatives:

- **Mounted host `~/.config/gcloud`**: bypasses credential isolation (P#51 spirit — agents don't get to introspect human creds); also doesn't work on WSL/services-new.
- **Env vars in `agent-env-map.conf`**: doesn't scale beyond a couple of universal secrets; conf is a public-ish file checked into framework source.
- **Service-account JSON in repo**: violates P#6 (Data Boundaries) and is a recurring industry footgun.
- **1Password CLI**: already in use by Nic on the laptop (per AXIOMS commentary; `op-template` pattern is documented). Cross-machine story is "install `op` on the host", which is achievable; in-container we never see the master credential.

Where it lives in scaffold: Step 5 (research tooling) generates `secrets/<slug>.op-template.example` and a `README.md` in `secrets/` explaining the pattern. The actual `<slug>.op-template` lives in `$AOPS_SESSIONS` (private), not the project repo.

### Q2. Where does cached research data live, and what triggers refresh?

**Decision: Hybrid — DuckDB cache is regenerated on-demand inside the container by a project-defined `refresh.sh`, never committed. The smoke-test (Q4) verifies freshness against a project-declared staleness threshold.**

Mechanism:

- Project scaffold creates `scripts/refresh.sh` (the script `METHODOLOGY.md` references but doesn't exist in TJA today). Default implementation: `dbt run --profiles-dir ./dbt_project` then `dbt build`. Editable.
- Cache location: `data/cache/<project>.duckdb` — gitignored.
- Staleness threshold: declared in `polecat.yaml` per project (default 24h). The smoke-test compares the cache mtime to the threshold and either passes, regenerates, or HALTs depending on `staleness_policy` (`regenerate | warn | block`).
- BigQuery is the source of truth; DuckDB is a read-cache for the polecat sandbox. No DuckDB commits, no cached-data drift across machines.

Why this and not alternatives:

- **Commit cache to repo**: violates P#42 spirit (data files in git inflate history; also can't anonymise easily for public repos).
- **Pull from object storage at scaffold/dispatch**: adds a moving part (a bucket per project) and a permissions surface. Defer until needed.
- **Pure regenerate on every dispatch**: too slow for iterative analysis. The hybrid with a staleness threshold gets the best of both.

Refresh trigger: the smoke-test. There is no other automatic refresh. Manual `scripts/refresh.sh` is always available.

### Q3. How does a PKB task declare its source repo independently of `project`?

**Decision: `polecat.yaml` `projects.<slug>.repo` is the SSoT, and it already works. The fix is _registration discipline_, not schema change. Add a frontmatter-level override only for the genuinely-multi-repo case.**

Mechanism:

- Default: `polecat.yaml` projects entry maps slug→repo. The `tja` slug should have been registered with `repo: explorations`. That is the bug — TJA was never registered. The schema is fine (`polecat/defaults/polecat.yaml.example` lines 92–96, the `aops` entry is the working pattern: `aops: { repo: academicOps }`).
- Scaffold Step 8 already does git-native registration. The fix is to make Step 8 _mandatory and gated_ — see §4 below — so no project goes live without an entry.
- Optional task-level override: tasks may set `repo:` in YAML frontmatter to dispatch against a different repo than the project's default. `pc finish` and `pc run` honour `task.repo` if set, else fall back to `polecat.yaml.projects[task.project].repo`. This handles the cross-repo edge case (rare) without forcing every task to declare it (common).
- Migration: existing tasks have no `repo:` — they inherit from `polecat.yaml`. No backfill needed.

Why this and not alternatives:

- **`repo:` in every task frontmatter**: introduces drift at the per-task level; people will forget.
- **Multi-repo project manifest**: premature; we have one project today (`tja`) where this matters and the fix is registration.
- **Git-remote fallback in `pc finish`**: hides the registration bug. The user wants the bug surfaced, not masked. HALT-on-missing is the right posture (P#9 fail-fast).

### Q4. What's the contract between task body paths and repo layout?

**Decision: A project-level `paths.yaml` is the SSoT. Task templates and the worker prompt resolve paths through it, not by inlining strings. A pre-dispatch lint step verifies every path mentioned in a task body exists in the live repo.**

Mechanism:

- Scaffold Step 5 generates `paths.yaml` at the repo root with named anchors:
  ```yaml
  dbt_root: tjadbt
  reasoning_traces: tja/report/reasoning.qmd
  local_cache: data/cache/tja.duckdb
  refresh_script: scripts/refresh.sh
  raw_records: tja/records/train
  ```
- Task templates reference anchors by name: `{{paths.dbt_root}}/models/marts/...` rather than `tja/dbt/models/...` (which is also wrong — actual path is `tja/tjadbt/`).
- The worker prompt template (`polecat/prompt_template.py`) gets a pre-Step-0 hook that resolves `{{paths.*}}` references in the task body against the live `paths.yaml`, and HALTs with a structured error if any reference doesn't resolve.
- A lightweight `paths-lint` runs as part of the polecat-dispatch pre-flight: if the task body contains literal paths that look repo-relative (e.g. `tja/dbt/`) but don't exist, the dispatcher refuses to start and surfaces the typo to the user.

Why this and not alternatives:

- **Lint at task-creation time only**: catches typos at write but doesn't survive renames. The smoke-test catches drift continuously.
- **No `paths.yaml`, lint only**: leaves the per-task drift problem (every task duplicates path strings). One renamed directory breaks N tasks silently.
- **Symlinks for backward compatibility**: violates P#25 (no workarounds).

The TJA typo (`tja/dbt/` vs `tja/tjadbt/`) and the missing `./refresh` script in `METHODOLOGY.md` are both exact examples of the failure mode this prevents.

### Q5. Axiom and heuristic deltas

**Decision: extend P#42; add P#102 (data-access verification); add a heuristic about evidentiary chains.**

See §7 for concrete diffs.

## 4. Recommended changes to `/project` skill

### 4.1 SKILL.md additions (Phase 1)

Add to the Phase 1 Q&A (current SKILL.md line 44–58):

> 9. **Data sources**: For empirical projects, name the authoritative data store (BigQuery dataset, S3 bucket, local file tree). The scaffold will declare it in `polecat.yaml` and generate the smoke-test that verifies polecat reach.
> 10. **Refresh strategy**: For projects with a derived cache (DuckDB, parquet snapshots), name the script that rebuilds it from source. Default: `scripts/refresh.sh` running `dbt build`. Staleness threshold (default 24h).

### 4.2 init.md restructure

Current 9 steps remain. Five additions:

**Step 5 (Research tooling) — extend**:

- After `dbt_project/profiles.yml`, generate **`scripts/refresh.sh`** with a working default (the script `METHODOLOGY.md` references).
- Generate **`paths.yaml`** at repo root with anchors for every directory/file the scaffold created. Document the convention in the README.
- Generate **`secrets/README.md`** explaining the 1Password op-template pattern.

**Step 5b (new) — Data declaration**:

- Generate **`.polecat/data.yaml`** in the repo declaring data sources, cache location, refresh script, staleness threshold. This is consumed by the smoke-test task template.
  ```yaml
  sources:
    bigquery:
      project: prosocial-443205
      dataset: toxicity
      requires_secret: gcp-service-account
    duckdb_cache:
      path: data/cache/tja.duckdb
      staleness_threshold: 24h
      refresh: scripts/refresh.sh
      staleness_policy: regenerate
  ```

**Step 5c (new) — Smoke-test task seed**:

- Drop a `smoke-test.md` task template into the project's PKB hub (see §6 for content). On first scaffold this task is created in `inbox` status; promoting it to `active` is the gate that unblocks any other dispatched work.

**Step 8 (Git/polecat registration) — strengthen**:

- Polecat-yaml entry now includes `data:` and `smoke_test:` references (see §5 for schema). Step 8 MUST succeed for the report (Step 9) to declare the project ready. If push fails, the report says "NOT READY — polecat registration incomplete, no dispatch possible".

**Step 9 (Report) — add acceptance bullet**:

- "Run the smoke test once before dispatching any analytic work:
  ```
  polecat run -p <slug> -t <smoke-test-task-id>
  ```
  Expected outcome: green pass on all checks. If it fails, fix the underlying gap (creds, cache, refresh script) before dispatching anything else."

### 4.3 Methodology generation discipline

Currently `docs/METHODOLOGY.md` is hand-templated (init.md line 254). The TJA failure (METHODOLOGY references a `./refresh` script that doesn't exist) shows hand-templates drift.

**Change**: `docs/METHODOLOGY.md` is generated _from_ `paths.yaml` and `.polecat/data.yaml`. The Reproducibility section becomes a render of those files plus a sentence per source. A repo-hook in pre-commit re-renders it if either input changes. The hand-edited sections (Research Questions, Data Sources narrative, Analytical Approach) remain free-form but live under explicit `<!-- managed -->` and `<!-- free -->` markers so the generator can leave the free sections alone.

This delivers anti-drift without forcing the methodology layer into a rigid schema.

## 5. Recommended `polecat.yaml` schema changes

Extend `projects.<slug>` entries with two optional blocks:

```yaml
projects:
  tja:
    repo: explorations              # already supported
    default_branch: main
    aliases: [trans-journalists]
    data:                            # NEW
      manifest: .polecat/data.yaml   # path within repo
      smoke_test_task: smoke-tja-001 # PKB task ID (stable slug recommended)
    secrets:                         # NEW
      op_template: tja.op-template   # path within $AOPS_SESSIONS/secrets/
```

Backwards compatibility: both `data:` and `secrets:` are optional. Projects without them dispatch as today (no smoke gate, no secret injection). The scaffold creates them for new research projects by default.

### `pc finish` semantics

Current behaviour (per `polecat/manager.py:resolve_project_path` lines 105–155): resolves project slug → repo path. The TJA failure was that `tja` wasn't registered, so `repo` defaulted to slug, and there is no `~/src/tja` — resolution returned `None`.

**Change**: `pc finish` adds an explicit error class for "project slug not registered in polecat.yaml" with the resolution being "run `/project register <slug>` (new sub-skill) — do not invent a path from the worktree git remote". Today the failure is a `None` propagation that confuses downstream. The fix is a clear error with an actionable next step.

Also: `pc finish` writes the smoke-test result (last-pass timestamp + commit SHA) to the task body as evidence. A task may declare `requires_smoke_pass: <hours>` in frontmatter; `pc finish` refuses to mark it `merge_ready` if the last smoke-test is older than that threshold. (Opt-in per task; default off.)

## 6. The smoke-test task template

Scaffold drops this into every new research project. It is the **gate**: no analytic task is `ready` until smoke-test has passed once and is fresh.

```markdown
---
title: "Dispatch smoke test: <project>"
type: task
project: <slug>
tags: [smoke-test, infrastructure, gate]
status: ready
assignee: polecat
consequence: |
  If this fails, no dispatched polecat can reach raw research data.
  Any analytic deliverable produced while this is failing rests on
  summary documents, not primary sources. The framework will not
  catch the substitution. Halt all analytic dispatch until green.
---

# Smoke test: <project>

This task verifies that a dispatched polecat can reach the project's
authoritative data sources on its first turn. Run this before any
analytic task. Re-run after infrastructure changes.

## What you must verify

For each source declared in `.polecat/data.yaml`, demonstrate working
read access by quoting the actual output of the listed probe. Do NOT
infer; do NOT skip. If a probe fails, HALT and report the gap — do
not "fall back" to summary documents (see P#42 extension, P#102).

### BigQuery probe
```

> The scaffold template above omits `priority` deliberately: it stays at the uncurated default band. `priority` is Nic's curated intent — agents (and scaffolds) never originate a non-default band ([[framework-conventions-summary#intent-authority]]). Importance is expressed via `consequence` prose and `contributes_to` `stated_weight`, not a priority bump.

bq query --nouse_legacy_sql --format=json --max_rows=1\
"SELECT COUNT(*) AS n FROM \`{{data.sources.bigquery.project}}.{{data.sources.bigquery.dataset}}.{{data.sources.bigquery.canonical_table}}\` LIMIT 1"

```
Expected: non-zero `n`, no auth error.

### dbt profile probe
```

cd {{paths.dbt_root}} && dbt debug --profiles-dir .

```
Expected: "All checks passed!" — specifically connection to the target
warehouse must succeed.

### DuckDB cache probe
```

duckdb {{data.sources.duckdb_cache.path}} -c "SELECT COUNT(*) FROM information_schema.tables;"

```
If cache missing or stale per `staleness_policy`, run
`{{data.sources.duckdb_cache.refresh}}` and re-probe.

### Raw-records sample read
```

ls {{paths.raw_records}} | head -3
head -5 {{paths.raw_records}}/$(ls {{paths.raw_records}} | head -1)

```
Expected: real content, not "No such file or directory".

### Methodology sanity
```

test -x {{paths.refresh_script}} && echo "refresh OK" || echo "refresh MISSING"

```
Expected: "refresh OK". If MISSING, fix `paths.yaml` or scaffold the
script — do not paper over.

## Reporting

Append the actual output (quoted) of every probe to this task body
under `## Last run`. Do NOT mark `done` if any probe failed; mark
`blocked` with the failing probe in the blocker reason. The reviewer
(orchestrator or human) reads the quoted output before promoting any
analytic task to `ready`.

## Acceptance

- [ ] Every probe quoted with real output (not paraphrased)
- [ ] All probes green, OR explicit `blocked` with named gap
- [ ] Last-run timestamp recorded by `pc finish`
```

This template is dropped into the new project's PKB at scaffold time. The slug for `smoke_test_task` in `polecat.yaml` references it.

## 7. Axiom and heuristic deltas (diff-style)

### 7.1 Extend P#42 (Research Data Is Immutable)

**Current** (`.agents/rules/AXIOMS.md` lines 134–140):

> ## Research Data Is Immutable (P#42)
>
> Source datasets, ground truth labels, records/, and any files serving as evidence for research claims are SACRED. NEVER modify, convert, reformat, or "fix" them.
>
> **Corollaries**:
> If infrastructure doesn't support the data format, HALT and report the infrastructure gap. No exceptions.

**Proposed**:

> ## Research Data Is Immutable AND Irreplaceable (P#42)
>
> Source datasets, ground truth labels, records/, and any files serving as evidence for research claims are SACRED. NEVER modify, convert, reformat, or "fix" them. ALSO: never substitute them. If the primary source is unreachable, the work HALTS — summary documents, derived reports, prior session notes, or "the gist of what the data says" are NOT acceptable substitutes for trace-level claims.
>
> **Corollaries**:
>
> - If infrastructure doesn't support the data format, HALT and report the infrastructure gap. No exceptions.
> - **Substitution is a failure mode equal to modification.** A deliverable that quotes a Quarto template's example output instead of the raw model trace it purports to describe is making things up, even if the template was written by a human. The reader cannot distinguish; you must.
> - **Evidentiary scope must match data scope.** If the task scope says "extract from raw traces" and you read summaries, you have changed the scope. Report the scope change explicitly in the task body before producing a deliverable — do not silently downgrade and ship.
>
> **Derivation**: Research integrity depends on data provenance. Modified source data invalidates all downstream analysis. Substituted source data invalidates it equally, and is harder to detect because the deliverable still "looks right". (See incident: `tja-26d26f57` / `note-460bc5de`, 2026-05-11.)

### 7.2 Add P#102 (Data Access Verification Before Evidence Claims)

**Insert at the end of `.agents/rules/AXIOMS.md`** (after the current last principle):

> ## Data Access Verification Before Evidence Claims (P#102)
>
> Before producing any deliverable that quotes, summarises, counts, or analyses primary data, the agent MUST demonstrate working read access to that data in the current session — quoted output, not inference. If a project ships a smoke-test (see `.polecat/data.yaml`), run it. If not, run the equivalent ad-hoc probe and quote its output in the task body.
>
> **Corollaries**:
>
> - Inability to read the data is HALT-and-report, not "fall back to something readable". (P#9, P#42.)
> - A worker that logs "couldn't reach X, used Y instead" and ships anyway has violated this. The framework will treat this admission in the progress log as a hard block on `done` status.
> - Smoke-test results expire. A green smoke-test from yesterday does not authorise today's claims if the source has changed. Re-run on demand; the cost is small, the alternative is silent staleness.
>
> **Derivation**: Evidence chains break silently. Verifying access at the start of each chain converts an invisible failure into a visible one — the only kind we can fix. Per Snowden / Cynefin, dispatched research lives in the Complex domain; the appropriate posture is probe-sense-respond, and the smoke-test IS the probe.

### 7.3 New heuristic: HEURISTICS file (or equivalent)

There is no `.agents/HEURISTICS.md` in brain today (verified by `Read` 2026-05-11: file does not exist). The natural home is to add this as a derived corollary in `$AOPS/aops-core/skills/remember/references/TAXONOMY.md` or to create a fresh `.agents/HEURISTICS.md`. **Recommended: create `.agents/HEURISTICS.md`** with this as its first entry, so future heuristics have a home that mirrors the AXIOMS pattern.

Diff for a new file (`.agents/HEURISTICS.md`):

```markdown
---
trigger: always_on
description: Practical heuristics — not inviolable like AXIOMS, but the default disposition.
status: active
---

# Heuristics

Practical defaults for common situations. AXIOMS are inviolable; heuristics
guide judgment within the space AXIOMS allow.

## H#01 — Summary docs are not evidence for trace-level claims

When a task asks for quote-level evidence from raw data (model traces,
interview transcripts, source records, primary documents), a summary
document about that data — even an excellent summary — is not a substitute.
The reader of the deliverable cannot verify the quote-source bind by
reading a summary. If the raw source is unreachable, surface that as the
finding; do not paper over it.

(See: P#42, P#102. Incident: `tja-26d26f57`.)

## H#02 — Project scaffolds must self-prove

A project repo is not "ready" until its smoke-test passes once. The
scaffold drops the smoke-test in as the first task and the report says so.
"Working repo" without verified data reach is theatre. (See: `/project`
skill Step 9; smoke-test template in spec.)

## H#03 — Methodology docs from template, not by hand

`docs/METHODOLOGY.md`'s structural sections (Data Sources, Reproducibility,
Pipeline) are generated from `paths.yaml` and `.polecat/data.yaml`. The
free sections (Research Questions, Analytical Approach narrative) are
hand-written. Don't mix the two — drift is guaranteed otherwise (TJA's
phantom `./refresh` script is the canonical example).
```

## 8. Migration note: TJA

Minimum changes to bring TJA up to the new default. Each is a separate small commit; none requires re-running the failed analysis.

1. **Register `tja` in `polecat.yaml`** (`$AOPS_SESSIONS/polecat.yaml`):
   ```yaml
   projects:
     tja:
       repo: explorations
       default_branch: main
       aliases: [trans-journalists]
       data:
         manifest: tja/.polecat/data.yaml
         smoke_test_task: tja-smoke-001
       secrets:
         op_template: tja.op-template
   ```
2. **Create `tja/.polecat/data.yaml`** declaring BigQuery dataset, DuckDB cache path, refresh script.
3. **Create `tja/scripts/refresh.sh`** — the script `METHODOLOGY.md` already references. Default body: `dbt build --profiles-dir tjadbt`.
4. **Create `tja/paths.yaml`** with the correct anchors. Critically: `dbt_root: tjadbt` (NOT `tja/dbt/`) — that fixes the typo class.
5. **Create `$AOPS_SESSIONS/secrets/tja.op-template`** mapping the BigQuery service account.
6. **Create smoke-test task `tja-smoke-001`** in PKB from the template in §6, instantiated with TJA paths.
7. **Re-dispatch the outlier analysis** (`tja-26d26f57` re-opened or sibling) only after smoke-test passes. The current `note-460bc5de` is flagged superseded; do not cite it in the paper.

No other TJA tasks need touching. Existing analytic work that already cited verified data stands.

## 9. Worked example: hypothetical new research project end-to-end

**Project**: "moderation-disclosure" — analyse Australian platform transparency reports, classify disclosure quality.

Phase 1 conversation (3 minutes):

- Type: empirical (text classification + descriptive stats).
- Tooling: dbt + DuckDB + Quarto, plus a small Python pipeline for PDF extraction.
- Data sources: a GCS bucket of PDFs + BigQuery table of platform metadata.
- Repo: new (`nicsuzor/moderation-disclosure`).

Phase 2 scaffold (Steps 1–9 as currently documented, plus the additions in §4):

- Repo created, structure scaffolded (Steps 1–4).
- Step 5: dbt project, Quarto manuscript, `scripts/refresh.sh`, `paths.yaml`, `secrets/README.md`.
- Step 5b: `.polecat/data.yaml` declares the GCS bucket + BQ table, DuckDB cache path, 24h staleness, regenerate policy.
- Step 5c: `moddisc-smoke-001` task created in PKB, instantiated from the template.
- Step 7: PKB project node created.
- Step 8: `polecat.yaml` registered with `repo: moderation-disclosure`, `data:` and `secrets:` blocks pointing at the new files. User runs `op item create` to mint the BQ service account into the 1Password vault, then `op item get` once to verify.
- Step 9: report says "smoke-test pending. Run `polecat run -p moddisc -t moddisc-smoke-001`."

First polecat dispatch (smoke-test):

- Container starts. `op inject` runs on host, mounts ephemeral env file.
- `GOOGLE_APPLICATION_CREDENTIALS` is set to `/run/secrets/gcp-sa.json`. `DBT_PROFILES_DIR` is set to `/workspace/dbt_project`.
- Worker reads task body, runs the BQ probe — quotes `{"n": 4221}`. Runs `dbt debug` — quotes "All checks passed!". DuckDB cache absent → runs `scripts/refresh.sh` → cache built (12s) → probe quotes `27 tables`. Sample raw read quotes the first 5 lines of a PDF metadata record. `refresh.sh` test: "refresh OK".
- Worker appends all five quoted outputs to task body under `## Last run`. Marks `done`.
- `pc finish` records timestamp + commit SHA in task frontmatter.

Second polecat dispatch (analytic task):

- Task body says: "Classify disclosure quality for all 4,221 records, output to `mart_disclosure_quality`."
- Worker prompt now includes (per §5.3 below) a pre-flight check: read smoke-test task's `last_pass_at`; if older than `requires_smoke_pass` (set to 24h here), HALT and ask orchestrator to re-run smoke.
- Smoke is 18 minutes old. Proceeds.
- Pipeline runs. Deliverable cites raw mart rows, not summary docs.

The same failure mode (`tja-26d26f57`) here would manifest as: smoke-test fails BQ probe (no creds). Worker writes `blocked` with reason "BQ probe failed: 401". Analytic task does not start. User fixes the op-template, re-runs smoke, then dispatches analytic work. No degraded deliverable ships.

## 10. Counterfactual check: would this have prevented `tja-26d26f57`?

Trace:

1. **Scaffold time** (hypothetical TJA created under new scaffold): `paths.yaml` would have anchored `dbt_root: tjadbt`. The task body that referenced `tja/dbt/` would either resolve via the anchor (correct) or fail the pre-dispatch lint (caught). Methodology's missing `./refresh` script would be a generation-time error (anti-drift §4.3). `polecat.yaml` would register `tja: { repo: explorations, ... }` — `pc finish` would not fail with the "no source-repo alias" error.

2. **Pre-dispatch**: `tja-26d26f57` would carry `requires_smoke_pass: 24h` in frontmatter (analytic tasks added by `/planner` get this by default). Worker pre-flight checks smoke-test freshness. If TJA's last smoke was green, proceed. If smoke had never been run, HALT.

3. **Inside the dispatch**: if for some reason smoke had passed but creds had silently rotated, the BQ probe inside the analytic prompt (added as a "verify data access before claiming evidence" step in `prompt_template.py`) would fail. The worker would write `blocked`, not invent.

4. **At the worker's "fallback" moment**: P#102 forbids the substitution. P#42-extended forbids it. H#01 names it as the failure mode. The worker's progress log "couldn't reach X, used Y instead" is now an automatic block on `done` status — `pc finish` parses it and refuses.

Each layer is independent. Any one of them would have stopped the failure. Together they constitute defence in depth.

**Verdict**: the proposed scaffold prevents the `tja-26d26f57` degradation at four points: scaffold-time registration; pre-dispatch smoke freshness; in-prompt verification; on-finish progress-log check.

## 11. What this proposal deliberately defers

- **General-purpose polecat data-access infrastructure** (e.g. a BQ proxy MCP). Per task scope: out of scope. Revisit if multiple projects need it.
- **Auto-discovery of project secrets** (1Password vault scanning). Manual op-template per project is explicit and auditable; auto-discovery is silent magic.
- **Re-running degraded TJA outlier analysis**. Separate sibling task under `tja-4ec6b7fe`. The scaffold-side fix is necessary but not sufficient for that.
- **Generalising the smoke-test template** beyond data-access (e.g. covering writing pipelines, evaluation harnesses). Start with data-access; extend when a second class of failure motivates it.
- **Implementation breakdown**. Per task acceptance criteria: explicit user acceptance is the gate before decomposition. None performed.

## 12. Relationships

- [related] [[task-23da34e4]] — parent epic, scaffold skill
- [related] [[aops-58f4aa69]] — driver task
- [incident] [[tja-26d26f57]] — the degraded analysis
- [incident] [[tja-4ec6b7fe]] — the meta-epic that surfaced it
- [degraded-deliverable] [[note-460bc5de]] — flagged superseded by this proposal
- [orchestrator-side] [nicsuzor/academicOps#943](https://github.com/nicsuzor/academicOps/issues/943)
- [axiom] [[AXIOMS|.agents/rules/AXIOMS]] — P#42 extension + new P#102
- [skill] `$AOPS/aops-core/skills/project/SKILL.md` + `instructions/init.md`
- [config] `$AOPS_SESSIONS/polecat.yaml` (schema extension)
- [config] `$AOPS/aops-core/agent-env-map.conf` (two universal vars added)
- [prompt] `$AOPS/polecat/prompt_template.py` (verification step added)

---

**Status reminder: AWAITING USER ACCEPTANCE.** No decomposition. No implementation tasks created. On acceptance, the natural breakdown is:

1. Schema + scaffold changes (`/project` skill + `init.md` + `polecat.yaml` schema)
2. Smoke-test template + worker prompt verification step
3. Axiom + heuristic edits (small, fast)
4. TJA migration (small, scoped)
5. Re-dispatch decision for `tja-26d26f57` (separate, under `tja-4ec6b7fe`)
