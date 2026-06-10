---
title: Session Digest — scheduled intra-day narrative consolidation
type: spec
status: draft
date: 2026-06-11
priority: P1
tags: [sessions, narrative, context-recovery, scheduled, cheap-model]
---

# Session Digest

Scheduled, cheap-model routine that reads the day's session evidence (session-summary JSONs + the user-prompt timeline) every hour or two and maintains a **referenced narrative digest** of what Nic directed, where each thread ended up, what corrections he made, and what facts went unrecorded.

## User Story

**As** an academic with ADHD running dozens of agent sessions in parallel,
**I want** a continuously-maintained, citation-backed narrative of what I've been directing and where it ended up,
**So that** I (via the overwhelm dashboard) and any agent can answer "what did we do?", "where are we up to?", and "what did I start but forget yesterday?" in seconds — without anyone re-parsing a day of transcripts.

> **Coherence check**: This is the "nothing lost" pillar applied to the _day itself_. Session summaries are mostly null (sessions rarely end via `/dump`), so the day's story currently exists only in raw transcripts. The digest converts cheap, abundant evidence into durable, queryable working memory.

## Acceptance Criteria

**USER-OWNED — draft, pending Nic's ratification.** Agents cannot modify, weaken, or reinterpret.

### Success Criteria (ALL must pass)

1. [ ] Within one cycle (≤2h) of any interactive session activity, today's digest file exists and covers it: every narrative claim carries at least one reference (session ID + transcript path, task ID, or PR/issue link) that resolves to a real artifact.
2. [ ] A fresh agent given only the last two digest files correctly answers "what did I start but forget yesterday?" — naming dropped threads with their references — in a dogfood test, without reading any transcript.
3. [ ] User corrections present in the period's prompts (e.g. "no, stop, you should have…", "why didn't you…", explicit /learn requests) are detected and dispatched to `/learn` (survey retro mode) with the transcript path; resulting GitHub issues are deduplicated by /learn's existing process.
4. [ ] Facts stated by the user but absent from the PKB (people, decisions, preferences, project state) are surfaced in the digest's **Unrecorded facts** section with provenance quotes; in supervised phase they are proposals, not writes.
5. [ ] Each cycle runs on a cheap model (Haiku-class or Flash-Lite-class) and completes incrementally — the unit of increment is the **prompt timestamp**, not the session: only prompts/events newer than the watermark are processed, so a still-open session with new prompts IS revisited, and a cycle with no new prompts anywhere is a no-op costing ~nothing.
6. [ ] The overwhelm dashboard's narrative panel can render the digest's narrative directly (file is parseable: stable headings + frontmatter), satisfying dashboard US-D3 ("a narrative, not a list of accomplishments").

### Failure Modes (If ANY occur, implementation is WRONG)

1. [ ] **Hallucinated references** — digest cites a session ID, transcript path, or task ID that does not exist.
2. [ ] **Secret leakage** — digest reproduces credentials/tokens that appear in captured tool output inside prompt extracts (observed in `summaries/user-prompts-2026-06.txt`: pasted env dumps contain live API keys). The digest quotes _user intent_, never raw tool output, and redacts anything matching a credential shape.
3. [ ] **Duplicate issue spam** — the same correction filed as a new GitHub issue on every cycle. Dispatch must be once-per-correction (watermark + /learn's own dedup).
4. [ ] **Silent death** — cron stops producing digests and nothing notices. The daily note's progress-sync must flag a stale digest (no update in >3h during waking hours).
5. [ ] **Autonomous PKB pollution** — unverified cheap-model facts written directly to the PKB before the supervised phase has been ratified (see Rollout).
6. [ ] **Silent thread loss** — a thread present in cycle N's digest is absent from cycle N+1 without having moved to Completed threads. For a context-recovery artifact this is the catastrophic case: it converts the tool into a context-_loss_ amplifier, and the user is the person least able to notice. Every update must be monotone over threads.

## Problem Statement

**What problem does this solve?**

- Session-summary JSONs (`$AOPS_SESSIONS/summaries/`) carry `summary: null`, `accomplishments: []` for most sessions — only `/dump`/`/end_session` populates them, and most sessions never get there. The richest signal — what Nic actually typed — is recoverable (`aops-core/scripts/user_prompts.py` produces a threaded, transcript-linked timeline) but nothing consumes it on a schedule.
- "Today's Story" is reconstructed from scratch by `/daily` progress-sync (expensive, frontier-model, runs a few times a day at most) and by the dashboard client-side from mostly-empty summaries. Both re-derive what could be accumulated incrementally.
- Corrections — the highest-value framework feedback — get a `/learn` retro only when Nic remembers to ask (see 2026-06-11 brain session: stale Charles task surfaced only because Nic manually dispatched a retro). Detection should be routine, not memory-dependent.
- Facts Nic states in passing ("they're the same Charles… now he's at Google with Zoe") evaporate unless the live session happens to `/remember` them.

**Why does this matter?**

Context recovery is the dashboard's entire job and currently its weakest input. A ~hourly cheap-model pass converts ~$0.01–0.05/cycle into: a precomputed narrative for the dashboard, cheaper `/daily` syncs (read the digest, not 30 JSONs), automatic correction capture, and a safety net under as-you-go memory capture.

## Scope

### In Scope

- A `/digest` skill (aops-core) defining the consolidation procedure — platform-agnostic, runnable by any headless agent CLI.
- A cron entry/runner script invoking it headless on a cheap model, hourly during waking hours.
- The digest artifact: `$AOPS_SESSIONS/digests/YYYYMMDD-digest.md` (one per day, updated in place each cycle; synced by existing repo-sync cron).
- Correction detection → `/learn` dispatch (flag-and-hand-off only).
- Unrecorded-fact surfacing (propose-only in supervised phase).
- Consumer wiring contracts: dashboard narrative panel and `/daily` progress-sync read the digest.

### Out of Scope

- Replacing `/daily` — the daily note remains the human-facing SSoT artifact; the digest is the machine-facing intermediate. `/daily`'s editorial "Today's Story" voice is unchanged; it just gets a cheaper input.
- Replacing `/remember`/`/sleep` — inline capture and deep consolidation are unchanged; the digest is a catch-net that _feeds_ them.
- Classifying or legislating on corrections — recusal applies (AXIOMS § recusal): the digest **flags**; `/learn` retro does forensics; `sweep` does cross-incident judgment.
- Dashboard rendering changes themselves (tracked under epic `task-ebba9ea1`; this spec only defines the file contract).
- Multi-day retrospectives / trend analysis (`/survey trend` owns that).

**Boundary rationale**: One feature = one artifact (the digest file) plus the routine that maintains it. Everything downstream consumes a stable file contract.

**Prior art and explicit supersession**: This spec **reintroduces a synthesis intermediary, which a prior decision forbade** — naming that squarely: the session-handover-contract model (task-1598bd4c, PR #707; recorded in kb-4e4feb21) cancelled task-4eb9c193 with "dashboard reads `$AOPS_SESSIONS/summaries/*.json` directly; no intermediary synthesis step needed," and the handover-contract spec said _do not reintroduce a synthesis intermediary_. That decision's premise — that summaries would carry the story — has failed empirically: sessions rarely reach `/dump`, so summaries are mostly null (Problem Statement). This spec therefore **formally supersedes** the no-intermediary rule for the narrative use-case, on that evidence. Landing checklist: update kb-4e4feb21 and the handover-contract's successor doc (now in the brain PKB, moved in commit a311b670) to point here. Two further differences from the failed attempt: the old intermediary was a mechanical script (`synthesize_dashboard.py`, deleted in task-4270206e) — here judgment lives in an agent per P#49; and the removed `/recap` skill (PR #857) proved the summaries→narrative shape but was on-demand and frontier-priced — this is its scheduled, referenced, cheap-model successor, which is what the dashboard epic (task-ebba9ea1, US-D3) was waiting on.

## Dependencies

### Required Infrastructure

- `aops-core/scripts/user_prompts.py` — threaded user-prompt timeline with transcript links (verified working 2026-06-11). Filtering of injected noise (`<task-notification>`, scheduled-task wrappers, hook output) happens here or in the skill prompt.
- `$AOPS_SESSIONS` repo + existing 5-min/hourly repo-sync cron (commit/push of digests is free-riding on this).
- Headless agent CLI with cheap model: `claude -p --model claude-haiku-4-5` (default) or `gemini` with a Flash-Lite-class model. The skill must not depend on which.
- `/learn` (= `/survey` retro mode) accepting a transcript path argument — already supported (`/survey retro [transcript path]`).
- PKB MCP **not** required by the digest itself in supervised phase (propose-only); required for Phase-3 direct writes — note GHA runners have no PKB MCP, which is one reason the runner is **local cron**, not GHA.

### Data Requirements

- `$AOPS_SESSIONS/summaries/YYYY-MM/*.json` — session metadata, token metrics; `summary` frequently null (must not be assumed present). Note: aops-efffc1f7 (merge_ready) adds incremental enrichment in `transcript.py` so summaries gain `initial_prompt` and timeline descriptions _without_ waiting for `/end_session` — this partially erodes the "mostly null" premise and is welcome: it improves the digest's _inputs_ but replaces none of its jobs (narrative synthesis, correction dispatch, fact surfacing remain agent judgment over those inputs).
- `$AOPS_SESSIONS/transcripts/YYYY-MM/*-abridged.md` / `*-full.md` — reference targets; abridged versions used for spot-verification of claims.
- Prior digest file — watermark + thread continuity (yesterday's digest seeds "carried over / dropped" detection).
- Missing/malformed inputs: skip the session, record it in the digest's `gaps` frontmatter list — never fabricate, never crash the whole cycle.

## Design

### Pipeline

```
cron (hourly, 07–22)
  └─ scripts/session-digest-cron.sh
       ├─ 1. gather: uv run aops-core/scripts/user_prompts.py --period today
       │           → filter to prompts with timestamp > watermark
       │           + summaries with mtime > watermark (metadata only)
       ├─ 2. no new prompts anywhere (incl. still-open sessions)? → exit 0 (no agent invocation)
       └─ 3. invoke headless cheap-model agent with /digest skill
              ├─ (a) update $AOPS_SESSIONS/digests/YYYYMMDD-digest.md
              ├─ (b) corrections → dispatch /learn retro per flagged transcript
              └─ (c) unrecorded facts → "Unrecorded facts" section (propose-only)
   (commit/push handled by existing repo-sync cron)

consumers:
  overwhelm dashboard SynthesisPanel  → reads digest Narrative (US-D3)
  /daily progress-sync (step 4.2)     → reads digest instead of re-parsing all JSONs
  any agent ("what did we do?")       → reads last 1–2 digest files
```

Division of labour per P#49: the **shell script** does only deterministic gathering (globs, watermark check, CLI invocation). All judgment — narrative, correction detection, fact extraction — happens **inside the agent** running the skill. No API-wrapping Python.

### Automation-session exclusion

The digest consumes **interactive sessions only**. Excluded entirely from narrative and correction inputs: the digest's own headless cycles, the `/learn` sessions it dispatches, scheduled-task runs, polecat workers, and GHA sessions (classifiable from filename conventions and surface metadata; precedent: task-46e0b027 made automation sessions observability-only for the dashboard). Two reasons this is load-bearing, not cosmetic:

1. **Quote-requote loop**: a dispatched `/learn` session's transcript quotes the correction verbatim. If automation transcripts were inputs, every cycle would re-flag the quoted correction from the _new_ transcript (the `learn_dispatched` ledger keys on the original ref, so it wouldn't catch the requote) → infinite re-dispatch. Exclusion breaks the loop at the source.
2. **Narrative pollution**: "the digest ran" ×15 is not the day's story.

Automation sessions may still be _referenced_ by the narrative when an interactive thread dispatched them (e.g. "Nic dispatched a /learn retro [ref]") — the exclusion is about what the digest reads, not what it may mention.

### Digest file contract

`$AOPS_SESSIONS/digests/YYYYMMDD-digest.md`:

```markdown
---
date: 2026-06-11
updated: 2026-06-11T14:05:00+10:00
cycles: 6
model: claude-haiku-4-5
watermark: 2026-06-11T13:58:12+10:00           # last processed PROMPT timestamp — the increment unit
sessions_covered: [469aa856, 1ec4c5ce, ...]    # informational; NOT the watermark (sessions grow across cycles)
gaps: []                                       # skipped/malformed inputs
learn_dispatched: ["transcripts/2026-06/...-abridged.md#L198"]  # dedup ledger
status: ok | stale | error
---

# Digest — 2026-06-11

## Narrative

<chronological prose, one paragraph per thread-shift; EVERY claim referenced:
"Morning started with the scheduled /daily run [469aa856], then Nic picked up
the Charles co-authorship confusion — a sent reply had been captured to memory
but task-88f27ffd was never updated [transcript L280–298] — and dispatched a
/learn retro that traced it to a reconciliation gap...">

## Threads

### Ongoing threads / where we're up to

- <thread> — <state, next step if stated> [refs]

### Completed threads

- <thread> — <outcome> [refs]

### Started but not picked back up

- <thread> — <last seen, what's dangling> [refs] ← the "forgot yesterday" answer

## Corrections flagged

- <verbatim-ish user quote> [transcript ref] → /learn dispatched <cycle timestamp>

## Unrecorded facts (proposed — not yet in PKB)

- <fact> — source: <quote> [transcript ref]
```

Heading names and frontmatter keys are the **contract**; consumers parse these and nothing else. Yesterday's digest is read each cycle so "Started but not picked back up" survives the midnight rollover.

### Correction detection (b)

The digest agent flags moments where the user redirects, rebukes, or repairs agent behaviour — including implicit forms ("i expected you to remember that"). For each _new_ flag (not in `learn_dispatched`):

1. Append the quote + transcript ref to **Corrections flagged**.
2. Dispatch `/learn` with that transcript path (headless, fire-and-forget; /learn owns classification, GH issue filing, and dedup against existing issues).
3. Record the ref in `learn_dispatched` so subsequent cycles skip it.

The digest never files issues itself and never proposes framework changes — flag-and-hand-off only (recusal).

### Fact capture (c)

The digest agent compares user-stated facts against what it can see was captured in-session (a `/remember` call, a task update visible in the timeline). Anything plausibly uncaptured goes in **Unrecorded facts** with a provenance quote. Persistence is staged — see Rollout. When Phase 3 lands, writes go through the canonical PKB MCP tools — `mcp__pkb__create_memory` for new facts, `mcp__pkb__append` to add to an existing note — tagged `digest, unverified` for `/sleep` to QA, per the existing consolidation-QA rule (consolidation output requires qualitative QA before merge).

### Redaction rule

The digest quotes **user prompts only**, never tool output embedded in prompt extracts. Any token matching a credential shape (`sk-…`, `key=`, `Bearer …`, etc.) is replaced with `[REDACTED]`. This is a hard rule in the skill, tested in the dogfood run.

Consumer-side redaction is defense-in-depth, **not** the fix for the standing leak that motivated it: live credentials already sit in `summaries/user-prompts-2026-06.txt` in the synced sessions repo, and every consumer of the prompt timeline re-propagates them until the _producer_ (`user_prompts.py`) redacts at extraction time. Remediation (audit, scrub, rotate, producer-side redaction) is tracked as **aops-f2a57c5c** (P1) and is not gated on this spec.

### Cadence & cost

- Hourly at :20 (offset from repo-sync at :00), 07:00–22:00 local, via crontab alongside the existing repo-sync entries.
- Incremental: input = prompts/summaries newer than watermark + the current digest + yesterday's digest. Typical cycle ≪ 50k input tokens on Haiku 4.5 → ~$0.01–0.05; idle cycles exit before any agent spawns.
- "Same cadence as the daily note" is satisfied by `/daily` progress-sync _reading_ the digest whenever it runs — the two stay in step by construction rather than by synchronized schedules.

## Integration Test Design

Tests implement the acceptance criteria above. All run against a fixture day assembled from real (sanitised) session artifacts in `tests/fixtures/digest/`.

| Test                           | Validates | Method                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1 reference integrity         | AC1 / FM1 | Run one cycle on fixtures; extract every `[ref]`; assert each session ID exists in fixtures, each path exists, each task ID matches fixture task list.                                                                                                                                                                                  |
| T2 context recovery            | AC2       | Dogfood: fresh headless agent + two fixture digests + question "what did I start but forget yesterday?"; PASS iff named dropped thread matches fixture ground truth.                                                                                                                                                                    |
| T3 correction dispatch + dedup | AC3 / FM3 | Fixture transcript with two corrections; run two cycles; assert exactly two /learn dispatches (mock), zero on second cycle. Then add the dispatched /learn session's own transcript (quoting the correction) to fixtures and run a third cycle: assert zero new dispatches (quote-requote loop broken by automation-session exclusion). |
| T4 fact surfacing              | AC4 / FM5 | Fixture with an uncaptured fact; assert it appears under Unrecorded facts with quote; assert zero PKB writes in supervised phase.                                                                                                                                                                                                       |
| T5 incremental + idle          | AC5       | Second run with no new prompts — including a fixture session that is still open but has no prompts past the watermark — exits 0 without invoking the agent CLI (assert via mock). Then append a new prompt to the still-open session and assert the next cycle DOES process it.                                                         |
| T6 redaction                   | FM2       | Fixture prompt containing a planted fake API key; assert digest contains `[REDACTED]` and not the key.                                                                                                                                                                                                                                  |
| T7 staleness flag              | FM4       | progress-sync fixture run with digest `updated` >3h old; assert daily note flags it.                                                                                                                                                                                                                                                    |
| T8 thread monotonicity         | FM6       | Two-cycle run over fixtures; assert every thread present in cycle N's Threads section appears in SOME Threads subsection (Ongoing / Completed / Started-but-dropped) at cycle N+1.                                                                                                                                                      |

Each test must fail before implementation (fixtures + assertions land first).

## Failure Modes — detection & recovery

1. **Hallucinated references** — Detection: T1 in CI + each cycle self-verifies refs before writing (cheap glob/grep). Recovery: claim demoted to `gaps`, cycle continues.
2. **Cron rot / silent death** — Detection: digest `status`/`updated` checked by `/daily` (T7) and visible on dashboard. Recovery: manual run of the cron script; log at `/tmp/session-digest.log`.
3. **Cheap-model narrative drift** (vague, unreferenced, or wrong-thread prose) — Detection: periodic `/verify` pass against the digest rubric (see Rollout phase gates); the digest is regenerable from transcripts at any time, so quality failures are recoverable, not fatal.
4. **Double-truth divergence** (digest says X, daily note says Y) — Prevention: daily note _consumes_ the digest (single derivation chain); digest carries references so conflicts resolve by following them.
5. **Silent thread loss (FM6)** — Detection: T8 in CI + each cycle mechanically diffs the prior digest's thread list against its rewrite before saving (cheap string check, not model judgment); any missing thread is restored or the cycle aborts with `status: error`. Recovery: digests are regenerable from transcripts; the prior version is one `git log` away (sessions repo is versioned).

## Rollout

Maturity ladder (Manual → Assisted → Supervised → Autonomous):

- **Phase 1 — Assisted (manual trigger)**: `/digest` runs on demand; Nic reviews output for ~3 days of real use. Corrections section populated but `/learn` dispatch is listed-not-fired. Gate to proceed: T1–T6 and T8 pass; Nic rates 3 consecutive digests as accurate ("would have answered my morning question").
- **Phase 2 — Supervised (cron, propose-only)**: hourly cron live; `/learn` dispatch live; facts remain propose-only; dashboard + `/daily` consume the digest. Gate: 1 week with zero FM1/FM2/FM3 occurrences; /learn issues spot-checked as non-duplicative.
- **Phase 3 — Autonomous fact writes**: PKB writes tagged `digest, unverified`, QA'd by `/sleep`. Gate: Nic explicitly ratifies after reviewing a week of proposed-facts precision.

**Rollback**: remove the crontab line; consumers fall back to current behaviour (dashboard client-side reconstruction, `/daily` re-parsing JSONs). Digest files are inert markdown — nothing depends on them existing.

## Monitoring

- Frontmatter `cycles`, `updated`, `status`, `gaps` make every digest self-reporting.
- `/daily` reports digest health in Work Log (`digest: 6 cycles, last 14:05, 0 gaps`).
- Weekly: count corrections flagged vs corrections Nic remembers making (recall check); precision of Unrecorded facts (Phase-3 gate input).

## Open Questions

1. **Model default** — `claude-haiku-4-5` headless assumed (stays inside existing Claude auth). Gemini Flash-Lite is cheaper but adds a second auth/CLI surface to the cron. Confirm default. _Working assumption: Haiku._
2. **Waking-hours window** — 07–22 local assumed; confirm.
3. **`/learn` dispatch mode** — fire-and-forget headless dispatch per flagged transcript (assumed) vs. queueing into a single end-of-day retro batch. Working assumption: per-flag dispatch, since /learn already processes one transcript at a time.
4. **Digest retention** — keep all daily digests forever (they're small, and `/sleep` can consolidate weekly), or prune after N days once consolidated? Working assumption: keep; revisit at first annoyance.

## Notes and Context

- Dashboard epic: `task-ebba9ea1` (US-D3 narrative panel) — this spec provides its missing input; implementation task for consumers should land under it.
- Related: `/daily` spec series (`specs/workflows/daily/`), `/remember`/`/sleep` (consolidation), `/survey` (retro/trend/sweep), `specs/workflows/feedback-loops.md`.
- Evidence base for the problem: 2026-06-11 brain session `469aa856` (manual retro dispatch for the Charles task); `summaries/2026-06/*.json` null-summary rate; ad-hoc `user-prompts-catchup-*` files Nic generated by hand on 2026-06-01/06-09 — this routine is the automation of exactly that manual practice.
