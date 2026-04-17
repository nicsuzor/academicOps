---
title: Session & Log Observability — Single Source of Truth
type: spec
category: architecture
status: active
tier: observability
created: 2026-04-17
related:
  - specs/framework-observability.md
  - specs/session-naming-convention.md
  - specs/sleep-cycle.md
  - kb-d8f58167-session-log-observability-map
  - task-bbd1b7e3
---

# Session & Log Observability

Single source-of-truth for **which files, from which environments, get archived where, processed by which jobs, and when**. Covers all 6 session types across the full artifact lifecycle.

> **Prior work**: `kb-d8f58167` (empirical audit 2026-04-16), `specs/framework-observability.md` (pipeline architecture), `specs/session-naming-convention.md` (naming spec). This document synthesises and extends all three.

---

## 1. Environment Topology

| Environment           | Description                                         | Provider access        | `$AOPS_SESSIONS` reachable?                    |
| --------------------- | --------------------------------------------------- | ---------------------- | ---------------------------------------------- |
| **host**              | Developer machine running `polecat` CLI             | Yes                    | Yes (it's set here)                            |
| **polecat container** | Docker container spawned by `polecat run`           | Via volume mounts only | Often NO — host path inaccessible in container |
| **crew container**    | Docker container spawned by `polecat crew`          | Via volume mounts only | Often NO                                       |
| **worker**            | Polecat autonomous worker process inside container  | Same as container      | Same as container                              |
| **host (manual)**     | Developer running `claude` or `gemini` CLI directly | Yes                    | Yes                                            |

Key consequence: `$AOPS_SESSIONS` is a **host-side** path. When hooks/scripts run inside containers, the env var points to a host path that may be unreachable (`PermissionError`/`OSError`). All code that writes to `$AOPS_SESSIONS` must handle this gracefully (fallback to provider-local paths).

---

## 2. Artifact Naming Convention

All canonical artifacts follow the pattern defined in `aops-core/lib/session_naming.py`:

```
{YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}{-variant}.{ext}
```

Where:

- `session_id` = 8-char hash (UUID prefix for Claude; SHA-256 prefix for Gemini; task-ID-embedded for polecat)
- `shortform` = `{crew}-{repo}-{machine}-{provider}` (crew omitted for non-crew sessions)
- `variant` = `-full`, `-abridged`, `-hooks`, `-client` (artifact-specific)

See `specs/session-naming-convention.md` for full derivation rules and migration notes.

---

## 3. Files × Environments Table

All artifact types across all 6 session types. "Current" means what the code actually does now (as of 2026-04-16 audit); "Target" means what task-bbd1b7e3 is building toward.

### 3.1 Claude Client Log (raw session JSONL)

| Attribute          | Value                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| **File type**      | `*.jsonl` (one JSON object per line — tool calls, responses, usage)                                         |
| **Producer**       | Claude Code CLI                                                                                             |
| **Initial path**   | `~/.claude/projects/{project_folder}/{session_id}.jsonl` (host or container `/home/worker`)                 |
| **Session types**  | manual-claude, crew-claude, polecat-claude                                                                  |
| **Archive target** | `$AOPS_SESSIONS/client-logs/{base}-client.jsonl` via `sync_client_log()` in `transcript.py`                 |
| **Naming**         | **Current**: source file stem (not unified). **Target**: unified v4 with `-client` suffix                   |
| **Processor**      | `transcript.py::sync_client_log()` — copies/hardlinks to `client-logs/`                                     |
| **When processed** | Post-session, on manual `transcript.py` run or `/sleep` backfill                                            |
| **Git-tracked**    | No — `client-logs/` is NOT added to git in current `transcript.py` (`git add transcripts/ summaries/` only) |
| **Retention**      | Ephemeral — raw source; transcript is the durable artifact                                                  |

### 3.2 Gemini Chat Log (raw session JSON)

| Attribute                         | Value                                                                                                   |
| --------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **File type**                     | `session-*.json` (Gemini internal format)                                                               |
| **Producer**                      | Gemini CLI                                                                                              |
| **Initial path**                  | `~/.gemini/tmp/{hash}/chats/session-{uuid}.json` (host or container `/home/worker`)                     |
| **Session types**                 | manual-gemini, crew-gemini, polecat-gemini                                                              |
| **Archive target (manual)**       | `$AOPS_SESSIONS/client-logs/{base}-client.jsonl` (converted to JSONL)                                   |
| **Archive target (polecat/crew)** | Extracted via `docker cp` from `/home/worker/.gemini/tmp` → `$AOPS_SESSIONS/polecats/{task_id}/{slug}/` |
| **Naming**                        | Gemini names it; framework renames on sync                                                              |
| **Processor**                     | `transcript.py` (reads + converts); `_extract_gemini_sessions()` in `polecat/cli.py`                    |
| **When processed**                | Post-session / post-container-stop                                                                      |
| **Git-tracked**                   | No (same as Claude client log)                                                                          |
| **Retention**                     | Ephemeral — Gemini tmp dir cleaned on reboot/restart                                                    |

### 3.3 Hook Log

| Attribute                                      | Value                                                                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **File type**                                  | `*-hooks.jsonl` (one JSON object per hook invocation)                                                                          |
| **Producer**                                   | `aops-core/hooks/unified_logger.py` via `session_paths.get_hook_log_path()`                                                    |
| **Initial path (if $AOPS_SESSIONS reachable)** | `$AOPS_SESSIONS/hooks/{base}-hooks.jsonl`                                                                                      |
| **Initial path (Claude fallback)**             | `~/.claude/projects/{project_folder}/{base}-hooks.jsonl`                                                                       |
| **Initial path (Gemini fallback)**             | `~/.gemini/tmp/{hash}/logs/{base}-hooks.jsonl` (dir often missing in containers — Gap #1)                                      |
| **Fallback of last resort**                    | `/tmp/aops-hooks-{uid}/{project_folder}/{base}-hooks.jsonl`                                                                    |
| **Session types**                              | All 6                                                                                                                          |
| **Archive target**                             | `$AOPS_SESSIONS/hooks/` (written directly if reachable; NOT synced otherwise)                                                  |
| **Naming**                                     | **Current**: partial unified (uses `generate_session_filename` but `sync_client_log` uses legacy). **Target**: full unified v4 |
| **Processor**                                  | None — hook logs are not post-processed; they're the raw observation stream                                                    |
| **When processed**                             | Not processed — read directly for debugging                                                                                    |
| **Git-tracked**                                | No — `hooks/` is NOT added to git                                                                                              |
| **Retention**                                  | Debugging value only; safe to delete after session ends without incident                                                       |

### 3.4 Gate Files (custodiet, etc.)

| Attribute          | Value                                                                                         |
| ------------------ | --------------------------------------------------------------------------------------------- |
| **File type**      | `*-custodiet.md` (Markdown audit document)                                                    |
| **Producer**       | `aops-core/hooks/custodiet_gate.py` via `session_paths.get_gate_file_path()`                  |
| **Initial path**   | Same resolution logic as hook log: prefer `$AOPS_SESSIONS/hooks/`, fallback to provider-local |
| **Session types**  | All 6 (wherever custodiet gate is enabled)                                                    |
| **Archive target** | `$AOPS_SESSIONS/hooks/{base}-custodiet.md`                                                    |
| **Naming**         | `{base}-{gate_name}.md` where gate name = `custodiet`                                         |
| **Processor**      | `aops-core:rbg` agent reads on-demand; not batch-processed                                    |
| **When processed** | On compliance check request (periodic within session)                                         |
| **Git-tracked**    | No                                                                                            |
| **Retention**      | Session-scoped; ephemeral                                                                     |

### 3.5 Session Status JSON (SessionState)

| Attribute                 | Value                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------ |
| **File type**             | `*.json` (structured session state for cross-hook coordination)                            |
| **Producer**              | `aops-core/lib/session_state.py` via `SessionState.create()` at session start              |
| **Initial path (Claude)** | `~/.claude/projects/{project_folder}/{base}.json`                                          |
| **Initial path (Gemini)** | `~/.gemini/tmp/{hash}/{base}.json`                                                         |
| **Env override**          | `AOPS_SESSION_STATE_DIR` — set by router hook at SessionStart and persisted                |
| **Session types**         | All 6                                                                                      |
| **Archive target**        | NOT archived — runtime-only coordination file                                              |
| **Naming**                | Uses `generate_session_filename(..., artifact_type="insights")` — naming correctly unified |
| **Processor**             | Read by hooks throughout session; finalized by Stop hook                                   |
| **When processed**        | Continuously during session                                                                |
| **Git-tracked**           | No                                                                                         |
| **Retention**             | Ephemeral runtime artifact; safe to delete after session ends                              |

### 3.6 Polecat Worker Transcript Stub

| Attribute          | Value                                                                                                                |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **File type**      | `{task_id}.jsonl` (captured stdout/stderr of the autonomous worker process)                                          |
| **Producer**       | `polecat/cli.py::save_worker_transcript()` — captures `polecat run` output                                           |
| **Initial path**   | `$POLECAT_HOME/polecats/{task_id}.jsonl`                                                                             |
| **Session types**  | polecat-claude, polecat-gemini                                                                                       |
| **Archive target** | Stays in `$POLECAT_HOME/polecats/` — NOT synced to `$AOPS_SESSIONS`                                                  |
| **Naming**         | `{task_id}.jsonl` — does NOT follow unified naming convention                                                        |
| **Processor**      | `polecat/cli.py::analyze_transcript()` on run completion (failure analysis)                                          |
| **When processed** | Immediately post-container-stop                                                                                      |
| **Git-tracked**    | No                                                                                                                   |
| **Retention**      | Debugging stub; real transcript is the Claude/Gemini client log extracted from container                             |
| **Note**           | This is the "stub" that confused the dogfood session — it's the outer shell output, not the inner Claude session log |

### 3.7 Extracted Container Session Files (polecat/crew)

| Attribute                         | Value                                                                                           |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| **File type**                     | All provider session files extracted from container                                             |
| **Producer**                      | `polecat/cli.py::_run_docker_container()` via `docker cp` post-container-stop                   |
| **Initial path (polecat-claude)** | Container: `/home/worker/.claude/projects/` → Host: `$AOPS_SESSIONS/polecats/{task_id}/{slug}/` |
| **Initial path (polecat-gemini)** | Container: `/home/worker/.gemini/tmp/` → Host: `$AOPS_SESSIONS/polecats/{task_id}/{slug}/`      |
| **Initial path (crew-claude)**    | Container: `/home/worker/.claude/projects/` → Host: `$AOPS_SESSIONS/crew/{crew_name}/{slug}/`   |
| **Initial path (crew-gemini)**    | Container: `/home/worker/.gemini/tmp/` → Host: `$AOPS_SESSIONS/crew/{crew_name}/{slug}/`        |
| **Session types**                 | polecat-claude, polecat-gemini, crew-claude, crew-gemini                                        |
| **Archive target**                | Subdirectory of `$AOPS_SESSIONS` (see above) — treated as raw material for `transcript.py`      |
| **Processor**                     | `transcript.py` discovers these and generates transcripts + insights                            |
| **When processed**                | On next manual or `/sleep`-triggered `transcript.py` run                                        |
| **Git-tracked**                   | No (raw files); transcripts and summaries derived from them are git-tracked                     |
| **Retention**                     | Source material; safe to delete once transcript + insights generated                            |

### 3.8 Transcript — Full

| Attribute          | Value                                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| **File type**      | `*-full.md` (complete session transcript in readable Markdown)                                        |
| **Producer**       | `aops-core/scripts/transcript.py`                                                                     |
| **Path**           | `$AOPS_SESSIONS/transcripts/{base}-full.md`                                                           |
| **Session types**  | All 6 (wherever a client log exists)                                                                  |
| **Archive target** | Already at final destination in `$AOPS_SESSIONS/transcripts/`                                         |
| **Naming**         | **Current**: partially unified (transcript.py uses `generate_base_name`). **Target**: full unified v4 |
| **Processor**      | `/sleep` skill (Pauli) — mines for insights; marks `mined: {date}` in frontmatter                     |
| **When processed** | `/sleep` cycle; also read by `/daily` for session flow reconstruction                                 |
| **Git-tracked**    | Yes — `git add transcripts/` in `transcript.py`                                                       |
| **Retention**      | Permanent (these are the primary session record)                                                      |

### 3.9 Transcript — Abridged

| Attribute          | Value                                                           |
| ------------------ | --------------------------------------------------------------- |
| **File type**      | `*-abridged.md` (abbreviated transcript: prompts + key outputs) |
| **Producer**       | `aops-core/scripts/transcript.py`                               |
| **Path**           | `$AOPS_SESSIONS/transcripts/{base}-abridged.md`                 |
| **Session types**  | All 6                                                           |
| **Archive target** | Already at final destination                                    |
| **Git-tracked**    | Yes (same `git add transcripts/`)                               |
| **Retention**      | Permanent                                                       |

### 3.10 Session Insights JSON

| Attribute          | Value                                                                                               |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| **File type**      | `*.json` (structured: summary, outcome, accomplishments, friction, token metrics, skill_compliance) |
| **Producer**       | `aops-core/lib/insights_generator.py` via `transcript.py::_process_reflection()`                    |
| **Path**           | `$AOPS_SESSIONS/summaries/{base}.json`                                                              |
| **Session types**  | All 6 (requires Framework Reflection in transcript)                                                 |
| **Archive target** | Already at final destination                                                                        |
| **Naming**         | Uses unified naming via `get_insights_file_path()`                                                  |
| **Processor**      | `/daily` skill (reads for session flow); `/sleep` skill (mines for PKB synthesis)                   |
| **When processed** | On each `/daily` and `/sleep` run                                                                   |
| **Git-tracked**    | Yes — `git add summaries/` in `transcript.py`                                                       |
| **Retention**      | Permanent (primary structured session record)                                                       |

### 3.11 Daily Note

| Attribute          | Value                                                 |
| ------------------ | ----------------------------------------------------- |
| **File type**      | `{YYYYMMDD}-daily.md`                                 |
| **Producer**       | `/daily` skill (Pauli)                                |
| **Path**           | `$ACA_DATA/brain/daily/{YYYYMMDD}-daily.md`           |
| **Session types**  | N/A (meta-artifact synthesised from session insights) |
| **Archive target** | Already at final destination in PKB                   |
| **Processor**      | Human review; `/daily` updates it during day          |
| **Git-tracked**    | Yes (PKB is a git repo)                               |
| **Retention**      | Permanent                                             |

### 3.12 RBG Verdicts / Audit Reports

| Attribute          | Value                                                                             |
| ------------------ | --------------------------------------------------------------------------------- |
| **File type**      | Inline in gate files or task bodies; no standalone file convention                |
| **Producer**       | `aops-core:rbg` agent                                                             |
| **Path**           | Delivered as agent output; written to task body via `update_task()` if actionable |
| **Archive target** | PKB task body (if retained at all)                                                |
| **Git-tracked**    | Via PKB                                                                           |
| **Retention**      | Task-scoped; ephemeral unless significant finding                                 |

---

## 4. Summary Matrix (6 session types × key artifacts)

| Artifact                   |           polecat-claude            |                       polecat-gemini                       |       crew-claude        |       crew-gemini        |     manual-claude     |  manual-gemini   |
| -------------------------- | :---------------------------------: | :--------------------------------------------------------: | :----------------------: | :----------------------: | :-------------------: | :--------------: |
| Client log (raw)           |     container→`polecats/{id}/`      |                 container→`polecats/{id}/`                 | container→`crew/{name}/` | container→`crew/{name}/` | `~/.claude/projects/` | `~/.gemini/tmp/` |
| Hook log                   | `$AOPS_SESSIONS/hooks/` or fallback | `$AOPS_SESSIONS/hooks/` or Gemini logs dir (often missing) |           same           |           same           |         same          |       same       |
| Gate files                 |     same resolution as hook log     |                            same                            |           same           |           same           |         same          |       same       |
| Status JSON                | `~/.claude/projects/` in container  |               `~/.gemini/tmp/` in container                |           same           |           same           |         same          |       same       |
| Worker stub                | `$POLECAT_HOME/polecats/{id}.jsonl` |                            same                            |           N/A            |           N/A            |          N/A          |       N/A        |
| Transcript (full/abridged) |    `$AOPS_SESSIONS/transcripts/`    |                            same                            |           same           |           same           |         same          |       same       |
| Insights JSON              |     `$AOPS_SESSIONS/summaries/`     |                            same                            |           same           |           same           |         same          |       same       |
| Client log (synced)        |    `$AOPS_SESSIONS/client-logs/`    |                            same                            |           same           |           same           |         same          |       same       |

Git-tracked: transcripts + summaries only. Everything else is local.

---

## 5. Processes Table

Every scripted and agent-scheduled job that touches session files.

| Process                                                 | Inputs                                                           | Outputs                                                                                                | Cadence                                      | Trigger                        |
| ------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------- | ------------------------------ |
| **`transcript.py`** (single session)                    | Client log (`.jsonl` or Gemini `.json`)                          | `transcripts/*-full.md`, `transcripts/*-abridged.md`, `summaries/*.json`, `client-logs/*-client.jsonl` | On-demand                                    | Manual or Stop hook            |
| **`transcript.py --all`**                               | All client logs in `$AOPS_SESSIONS` and extracted container dirs | Same as above, batch                                                                                   | On-demand                                    | Manual or `/sleep`             |
| **`sync_client_log()`**                                 | Raw client log file + session_id                                 | `$AOPS_SESSIONS/client-logs/{base}-client.jsonl`                                                       | Per-session (called from `transcript.py`)    | Called inside `transcript.py`  |
| **`polecat/cli.py::_run_docker_container()`** (extract) | Running container state                                          | Extracted files in `$AOPS_SESSIONS/polecats/{id}/` or `crew/{name}/`                                   | Post-container-stop                          | Automatic via `docker cp`      |
| **`_extract_gemini_sessions()`**                        | `~/.gemini/tmp/` in container                                    | Host-side session dir                                                                                  | Post-container-stop                          | Called from `polecat run/crew` |
| **`save_worker_transcript()`**                          | `polecat run` captured stdout                                    | `$POLECAT_HOME/polecats/{task_id}.jsonl`                                                               | Per polecat-run session                      | Auto post-run                  |
| **`/sleep` — Phase 1: Backfill**                        | Session client logs missing transcripts                          | Runs `transcript.py` for each                                                                          | `/sleep` cycle                               | Cron / manual `/sleep`         |
| **`/sleep` — Phase 1b: Mining**                         | `$AOPS_SESSIONS/transcripts/*.md` (unmined)                      | PKB knowledge notes (`$ACA_DATA/brain/notes/`)                                                         | `/sleep` cycle                               | Cron / manual `/sleep`         |
| **`/sleep` — Phase 2+: Synthesis**                      | PKB observations                                                 | Synthesis notes in PKB                                                                                 | `/sleep` cycle                               | Cron / manual `/sleep`         |
| **`/daily` — Session Flow**                             | `$AOPS_SESSIONS/summaries/*.json`                                | Daily note section (session flow narrative)                                                            | Once/daily                                   | Manual `/daily`                |
| **`polecat sync`**                                      | Git working repos + bare mirrors                                 | Pushed to remotes                                                                                      | On-demand                                    | Manual `polecat sync`          |
| **`transcript.py` git push**                            | `$AOPS_SESSIONS/transcripts/`, `$AOPS_SESSIONS/summaries/`       | Committed + pushed to sessions git repo                                                                | Per `transcript.py` run (unless `--no-push`) | End of `transcript.py`         |
| **Unified logger hook**                                 | Hook execution events                                            | `*-hooks.jsonl` entries                                                                                | Per hook invocation                          | Every hook fire                |
| **Custodiet gate hook**                                 | Session state + tool calls                                       | `*-custodiet.md` gate file                                                                             | Periodic (every ~25 ops)                     | PreToolUse hook                |
| **`aops-core:rbg`**                                     | Gate file path                                                   | Compliance verdict (OK/WARN/BLOCK)                                                                     | On custodiet trigger                         | Agent invocation               |

---

## 6. Gap Analysis (Current State)

From empirical audit 2026-04-16 (`kb-d8f58167`) and QA sweep 2026-04-14 (`task-bbd1b7e3`):

| Gap                                                        | Description                                                                                                                                              | Task                          |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| **Gemini hook log dir missing**                            | `~/.gemini/tmp/logs/` not created in polecat containers; hook logs silently lost                                                                         | `task-c9667cd0`               |
| **AOPS_SESSIONS unreachable in containers**                | Hook logs + gate files fall back to local provider paths, never sync to host                                                                             | `task-bbd1b7e3`               |
| **`sync_client_log` uses legacy naming**                   | Copies client logs with source filename stem, not unified v4 pattern                                                                                     | `task-56e41c5f` (reopen)      |
| **`session_paths.py` hook/status/gate emit legacy format** | `get_hook_log_path()` and `get_gate_file_path()` still use legacy `YYYYMMDD-HH-shorthash` in some paths                                                  | `task-c3e9823a`               |
| **`client-logs/` + `hooks/` not git-tracked**              | `transcript.py` only stages `transcripts/` and `summaries/`; hook logs and client logs live only on local disk                                           | Open                          |
| **Polecat worker stub ≠ Claude transcript**                | `$POLECAT_HOME/polecats/{id}.jsonl` is outer shell output; actual Claude session lives in container then extracted. Confused multiple debugging sessions | `task-bbd1b7e3`               |
| **Minutes collision**                                      | Some paths still use `HH` (hour only), causing filename collisions for sessions in same hour                                                             | Migrating via `task-3e7d048b` |
| **Orphaned status files**                                  | Status JSONs in container `/tmp` or `~/.gemini/tmp/` not cleaned up or extracted                                                                         | Open                          |
| **No `$AOPS_MACHINE` in env**                              | Shortform requires `AOPS_MACHINE`; fallback to container hostname (`aops-crew`) is useless                                                               | `task-bbd1b7e3`               |

---

## 7. `$AOPS_SESSIONS` Retirement Analysis

### 7.1 What `$AOPS_SESSIONS` currently does

`$AOPS_SESSIONS` (default: `$POLECAT_HOME/sessions`, set to `~/.aops/sessions`) serves three distinct functions:

1. **Git repo** — `transcripts/` and `summaries/` are committed and pushed, providing a versioned, synced record of session history across machines.
2. **Local staging area** — hook logs, gate files, client logs, and extracted container files land here (or try to) before (or instead of) being git-committed.
3. **Named anchor** — `$AOPS_SESSIONS` is the env var that all framework code uses to find session artifacts. It's the single address for "where are my session files?"

### 7.2 Can we retire it and rely on `$ACA_DATA`?

**Short answer: No — not without significant bloat and loss of pre-archival observability. Consolidate rather than retire.**

Analysis by concern:

**A. PKB repo bloat**

`$ACA_DATA` (`/data/brain/`) is the PKB git repo containing notes, tasks, and knowledge. Landing raw session artifacts there would:

- Add JSONL transcripts (often 5–30 MB per session) to a notes repo
- Add hook logs (smaller but numerous) to git history
- Slow `git log`, `git diff`, PKB search, and sync operations significantly

The PKB is structured for human-readable notes (KB, tasks, daily notes). Raw observability artifacts do not belong there.

**Verdict**: Cannot retire to `$ACA_DATA` without creating a separate non-PKB subdirectory within it — which is effectively just renaming `$AOPS_SESSIONS`.

**B. Pre-archival observability**

Several artifacts are written mid-session:

- Hook logs: written on every hook invocation throughout the session
- Gate files: written when custodiet fires
- Status JSON: written at SessionStart and updated throughout

These must be writable by the running agent/hook process in real-time. They cannot be deferred to post-session archival. This requires a fast, locally-writable path — not a PKB sync.

**Verdict**: Mid-session artifacts must remain in a local staging path, not PKB.

**C. "Process before archive" pipeline**

`transcript.py` reads raw client logs, processes them into transcripts + insights, then writes those derived artifacts to `$AOPS_SESSIONS`. If raw logs landed in `$ACA_DATA` directly, `transcript.py` would need to be re-pointed — but more importantly, raw unprocessed JSONL in the PKB would be noise. The pipeline value is in keeping raw material separate from processed output.

**Verdict**: The two-stage pipeline (raw → `$AOPS_SESSIONS` staging; processed → git-tracked transcripts/summaries) is correct architecture. Don't collapse it.

### 7.3 Decision: Consolidate, Don't Retire

**Keep `$AOPS_SESSIONS` as the session artifact store.** The variable name itself is fine. The git-repo requirement, however, warrants re-examination:

**What should be git-tracked (in `$AOPS_SESSIONS` repo):**

- `transcripts/` — processed, human-readable, permanent record → YES
- `summaries/` — structured insights, consumed by `/daily` and `/sleep` → YES

**What should NOT be git-tracked (local-only in `$AOPS_SESSIONS`):**

- `client-logs/` — large raw JSONL; transcript is the derived artifact → NO
- `hooks/` — debugging-only; ephemeral → NO
- `polecats/` — extracted container raw files; transcript is the derived artifact → NO
- `crew/` — same as polecats → NO

**Migration plan (if/when implementing):**

1. Add `client-logs/`, `hooks/`, `polecats/`, `crew/` to `.gitignore` in the `$AOPS_SESSIONS` repo if not already.
2. Consider splitting: `$AOPS_SESSIONS` git repo tracks only `transcripts/` + `summaries/`; a separate `$AOPS_CACHE` or `$POLECAT_HOME/cache/` holds ephemeral staging artifacts.
3. The `$AOPS_SESSIONS` env var continues to point to the git repo; staging artifacts use `$POLECAT_HOME/staging/` or similar.

This is spec-only; implementation is out of scope for this task.

---

## 8. Cross-References

| Document                             | Relationship                                                               |
| ------------------------------------ | -------------------------------------------------------------------------- |
| `specs/framework-observability.md`   | Pipeline architecture; transcript processing internals; insight schema     |
| `specs/session-naming-convention.md` | Canonical naming convention; component derivation; migration plan          |
| `specs/sleep-cycle.md`               | Defines `/sleep` phases and what each phase consumes/produces              |
| `kb-d8f58167`                        | Empirical audit (2026-04-16) — filesystem verification of paths above      |
| `kb-bcfb0dd7`                        | AOPS_SESSIONS directory overview and retention guidance                    |
| `task-bbd1b7e3`                      | Unified naming implementation epic (in progress)                           |
| `task-52795d03`                      | Prior observability audit (done) — gap analysis findings incorporated here |
| `task-c9667cd0`                      | Gemini hook log gap (filed 2026-04-16)                                     |

---

## 9. Key Source Files

| File                                  | Role                                                                                                        |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `aops-core/lib/session_naming.py`     | Canonical filename generation — single source of truth for all naming                                       |
| `aops-core/lib/session_paths.py`      | Path resolution for hook logs, gate files, status files                                                     |
| `aops-core/lib/paths.py`              | Directory resolution (`get_sessions_repo()`, `get_transcripts_dir()`, etc.)                                 |
| `aops-core/lib/session_state.py`      | SessionState: mid-session coordination file                                                                 |
| `aops-core/scripts/transcript.py`     | Transcript + insights generation; git sync; `sync_client_log()`                                             |
| `aops-core/lib/insights_generator.py` | Insights JSON generation and schema validation                                                              |
| `aops-core/lib/session_reader.py`     | `find_sessions()` — discovers all session types for processing                                              |
| `polecat/cli.py`                      | `_get_sessions_base()`, `_run_docker_container()`, `save_worker_transcript()`, `_extract_gemini_sessions()` |
| `polecat/observability.py`            | Polecat-specific metrics (sync latency, queue depth)                                                        |
| `aops-core/hooks/unified_logger.py`   | Writes to hook log                                                                                          |
| `aops-core/hooks/custodiet_gate.py`   | Writes to gate files                                                                                        |
