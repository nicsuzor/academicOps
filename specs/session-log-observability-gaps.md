# Session Log Observability — Gap Analysis

**Status:** generated 2026-04-30 for `task-e8647b0c` (parent epic `task-52795d03`).
**Companion doc:** `~/brain/notes/kb-d8f58167-session-log-observability-map.md` (the inventory + flow map this gap analysis builds on).

This document compiles every observability hole found across the artefact × session-type matrix. Each row of the matrix calls out what should exist, what actually exists, and whether the gap is already tracked. Untracked gaps have new PKB tasks filed and linked back here.

## Scope

Six session types, six artefact types. Sources: `aops-core/lib/session_naming.py`, `aops-core/lib/session_paths.py`, `aops-core/scripts/transcript.py`, `aops-core/hooks/router.py`, `aops-core/hooks/hooks.json`, `polecat/defaults/gemini-settings.json`, `scripts/repo-sync-cron.sh`.

## Artefact × Session-Type Matrix

Legend: `OK` = produced & synced under unified naming. `LOCAL` = produced but stays on host (no sync). `LEGACY` = produced & synced but with old/inconsistent name. `MISSING` = expected but not produced. `n/a` = not applicable.

| Artefact \ Session                         | Claude Polecat                                            | Gemini Polecat                                                  | Manual Claude | Manual Gemini               | Crew/Claude (worktree)        | Crew/Gemini (worktree) |
| ------------------------------------------ | --------------------------------------------------------- | --------------------------------------------------------------- | ------------- | --------------------------- | ----------------------------- | ---------------------- |
| **Transcript** (`-full.md`/`-abridged.md`) | OK                                                        | OK                                                              | OK            | OK                          | OK                            | OK                     |
| **Insights JSON** (`summaries/*.json`)     | OK                                                        | OK                                                              | OK            | OK                          | OK                            | OK                     |
| **Hook log** (`hooks/*-hooks.jsonl`)       | OK                                                        | MISSING (G1)                                                    | OK            | MISSING (G1)                | OK                            | MISSING (G1)           |
| **Client log** (`client-logs/*-client.*`)  | LEGACY → now OK on cron host; LOCAL inside container (G2) | LEGACY/LOCAL (G2)                                               | OK            | OK (when cron sees it)      | LEGACY/LOCAL (G2)             | LEGACY/LOCAL (G2)      |
| **Status JSON** (SessionState)             | OK on host, LOCAL in container fallback (G3)              | LOCAL `~/.gemini/tmp/` (G4)                                     | OK            | LOCAL `~/.gemini/tmp/` (G4) | LOCAL container fallback (G3) | LOCAL (G3 + G4)        |
| **Gate / custodiet markdown**              | OK on host, LOCAL in container fallback (G3)              | LOCAL `~/.gemini/tmp/logs/` if dir exists, else MISSING (G1+G3) | OK            | LOCAL                       | LOCAL fallback (G3)           | LOCAL/MISSING (G1+G3)  |

**Cells not represented as a separate session type:** GHA `claude-session` artifacts (synced by `do_gha_sync` into `$AOPS_SESSIONS/github/`) — covered by transcript sync; SSH/remote interactive sessions on `services-new`, `nicwin`, etc. — coverage is unverified (G7).

## Gap Inventory

Each entry: description, impact (what cannot be diagnosed), severity, tracking status.

### G1 — Gemini hook log missing in polecat & manual gemini sessions

- **Description:** `aops-core/hooks/hooks.json` only registers Claude Code hooks (`bash ${CLAUDE_PLUGIN_ROOT}/hooks/router.sh --client claude`). Gemini hook events flow through `polecat/defaults/gemini-settings.json` but the resulting `*-gemini-session-hooks.jsonl` is not produced (logs dir often absent inside container; router not invoked with `--client gemini` for many event kinds).
- **Impact:** No per-tool timing, no gate verdict trail, no PreToolUse/PostToolUse forensics for any gemini session. Caused a misdiagnosis of "hooks not firing" during the 2026-04-16 gemini slowness investigation.
- **Severity:** HIGH.
- **Tracked:** `task-c9667cd0`.

### G2 — Client log sync is best-effort and breaks inside containers

- **Description:** `sync_client_log()` (transcript.py:80) writes to `$AOPS_SESSIONS/client-logs/` and silently returns on `PermissionError/OSError` when the dir is unreachable (typical inside polecat/crew containers whose `AOPS_SESSIONS` points at a host path with no bind-mount). Hardlink path falls back to copy across filesystems but only if the target dir exists. `task-9f5ec636` covered the naming portion (now using `generate_session_filename(..., artifact_type="client")`); the sync-reachability gap is separate.
- **Impact:** Worker client logs never leave the worker host; remote debugging needs an SSH session to grep the worker's `~/.claude/projects/...`.
- **Severity:** MED.
- **Tracked:** _partially_ by `task-9f5ec636` (naming) and `task-da3de090` (git-sync inclusion). The container-reachability fallback itself (silent skip) is **untracked** → new task **G2a** below.

### G3 — Status JSON & gate files use container-local fallbacks that never reach `$AOPS_SESSIONS`

- **Description:** `session_paths.py` falls back to `_polecat_claude_state_dir(...)` under `/tmp` when the polecat sandbox prevents writing to the canonical path; gemini falls back to `~/.gemini/tmp/`. Neither location is swept into `$AOPS_SESSIONS/status/` or the sessions repo on session end.
- **Impact:** Cannot reconstruct gate verdict timeline or token usage for any container-bound session post-hoc; the live SessionState dies with the container.
- **Severity:** HIGH.
- **Tracked (partial):** `task-1ab6b250` covers Gemini status cleanup/archival. The Claude polecat container-local fallback is **untracked** → new task **G3a** below.

### G4 — Gemini status JSON path is non-canonical and not synced

- **Description:** `~/.gemini/tmp/<hash>/...` is the gemini-cli's own working dir. The framework reads from it but does not relocate or copy it on session end. No `summaries/` or `status/` cross-sync.
- **Impact:** Same as G3 for gemini specifically; also blocks any aggregated cross-session gemini state analysis.
- **Severity:** MED.
- **Tracked:** `task-1ab6b250` (existing sibling).

### G5 — `transcript.py git_sync()` only opportunistically adds optional dirs

- **Description:** `git_sync()` (transcript.py:920) adds `transcripts/` + `summaries/` unconditionally; `hooks/`, `client-logs/`, `status/` are added only `if (sessions_root / optional).exists()`. On a fresh sessions checkout where any of those dirs is empty (no commit yet), they remain ungitted.
- **Impact:** Hook logs, client logs, status JSON drift out of the canonical history; first-time-on-machine debugging is blind.
- **Severity:** MED.
- **Tracked:** `task-da3de090`.

### G6 — Naming drift / minutes precision

- **Description:** Some legacy artefacts and external clients still emit `YYYYMMDD-HH-shorthash-*` (no minutes) — collisions for sessions in the same hour. `_sweep_legacy_client_logs()` exists but only sweeps client logs, not hook logs or status JSON.
- **Impact:** Same-hour sessions overwrite each other's hook/status files; transcript joins to the wrong artefact.
- **Severity:** LOW (transitional — most call sites migrated in `task-bbd1b7e3`).
- **Tracked:** `task-bbd1b7e3` epic (in progress).

### G7 — Cross-machine coverage unverified

- **Description:** Audit was conducted on the developer laptop + one polecat container. `services-new`, `nicwin`, GHA runners not empirically walked through. `task-78590a68` exists for inventory but has no analogous gap-filing.
- **Impact:** Unknown unknowns on remote hosts. Cron run on `services-new` may write artefacts that never reach the canonical repo.
- **Severity:** MED.
- **Tracked:** `task-78590a68` (inventory, ready).

### G8 — Stale `session-insights` skill references mislead readers

- **Description:** Specs and code reference a non-existent `aops-core/skills/session-insights/SKILL.md`. The actual pipeline is `transcript.py` + `lib/insights_generator.py`.
- **Impact:** Onboarding agents reading specs commission a skill that does not exist; the wrong file is grep'd when debugging insights generation.
- **Severity:** LOW (docs only).
- **Tracked:** `task-c5fa4dd6`.

### G9 — Common ID alignment across sessions, tasks, PRs

- **Description:** Task ID, session shorthash, branch name, PR number have no shared component. Joining across them is manual.
- **Impact:** No `grep -r task-XXXX $AOPS_SESSIONS` returns the full artefact set; investigations require N joins by hand.
- **Severity:** MED.
- **Tracked:** `task-c36a6b0c`.

### G10 — Hook router does not write a structured log when `--client` is unrecognised or the dispatcher fails before `log_event_to_session`

- **Description:** Inspection of `aops-core/hooks/router.py` shows hook events are logged via `log_event_to_session` / `log_hook_event` after argument parsing. Failures earlier in dispatch (bad client flag, schema validation error, missing env) print to stderr but do not append to any per-session JSONL — so the failure is invisible to anyone reading `$AOPS_SESSIONS/hooks/`.
- **Impact:** Silent hook-router failures look identical to "hooks not firing"; G1's misdiagnosis pattern is reproducible at the dispatcher layer too.
- **Severity:** MED.
- **Tracked:** **untracked** → new task **G10a** below.

### G11 — Subagent / `Task` tool sessions are not separately observable

- **Description:** When the parent agent dispatches a Task subagent, the subagent's tool calls are folded into the parent's hook log and transcript. There is no per-subagent transcript, no per-subagent insights file, and no way to locate the subagent's session ID from the parent transcript.
- **Impact:** Cannot evaluate subagent quality independently; `/retro` cannot read a subagent's transcript; agent-level performance metrics are blended.
- **Severity:** MED.
- **Tracked:** **untracked** → new task **G11a** below.

### G12 — `do_transcript` cron pass uses `--no-sync`; relies on `do_sync` later — race window

- **Description:** `repo-sync-cron.sh do_transcript` runs `transcript.py --recent --no-sync`, then `do_sync` runs `polecat sync` for repos. The sessions-repo `git_sync()` is not called in cron; it only runs when `transcript.py` is invoked without `--no-sync`. So new transcripts/summaries land on disk but the dedicated `git add transcripts/ summaries/ hooks/ client-logs/ status/` step is skipped on every cron tick.
- **Impact:** Sessions-repo only catches up when a human runs transcript.py directly or `polecat sync` happens to pick up the dir. Hook/status/client artefacts may sit local-only for days.
- **Severity:** HIGH.
- **Tracked:** **untracked** → new task **G12a** below.

## New Tasks Filed

- **G2a** — `task-f1545205` — client-log sync silently skips when `$AOPS_SESSIONS` is unreachable inside containers
- **G3a** — `task-e07efd4a` — Claude polecat status/gate fallback under `/tmp` is never synced to `$AOPS_SESSIONS`
- **G10a** — `task-c98b6647` — hook router silent dispatcher failures, write structured failure log per session
- **G11a** — `task-b483e037` — subagent (`Task` tool) sessions emit no independent transcript or insights
- **G12a** — `task-9c0710ae` — cron `do_transcript --no-sync` skips `git_sync()`, sessions-repo lags

All five filed with `parent=task-52795d03`, `status=ready`, `priority=3`, `assignee=null` (judgment needed).

## Cross-References

- Inventory map: `~/brain/notes/kb-d8f58167-session-log-observability-map.md`
- Parent epic: `task-52795d03`
- Naming epic: `task-bbd1b7e3`
- Sibling gap tasks already filed: `task-c9667cd0`, `task-727bdc87`, `task-bbd1b7e3`, `task-c36a6b0c`, `task-9f5ec636`, `task-da3de090`, `task-c5fa4dd6`, `task-1ab6b250`, `task-78590a68`
