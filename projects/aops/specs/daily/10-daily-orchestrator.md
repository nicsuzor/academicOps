# `/daily` — orchestrator and composer

**Status**: draft (cowork-sandbox), proposed 2026-05-19. To land at `projects/aops/specs/daily/10-daily-orchestrator.md`.

**Inherits**: [00-architecture.md](00-architecture.md) — persona, time context, shared types (`DailyNote`, `EmailCapture`, `NewsBriefing`).

**Plugin**: `aops-core/skills/daily/SKILL.md`. Stays in aops-core because it owns the daily-note structure (SSoT) and is non-fungible.

## Responsibility

`/daily` is the **orchestrator** that produces and maintains the daily note. It does not generate editorial content itself — it composes outputs from worker workflows into the canonical daily-note structure defined in 00-architecture.md.

## Pipeline

When invoked at start-of-day (or on demand):

1. **Resolve note path**. `$ACA_DATA/daily/YYYYMMDD-daily.md`. If exists, read it (append/update mode); if not, create it.

2. **Pull internal state in parallel** (one tool call each, no judgement required):
   - Calendar events for today
   - Open PRs grouped by state (drafted, in-review, mergeable, blocked)
   - Ready tasks (`list_tasks` with `status=ready`, sorted by `focus_score`)
   - In-progress epics and their leaves

3. **Dispatch worker workflows in parallel** (each is an `Agent` call with `run_in_background=true`):
   - `/email --daily` → returns `EmailCapture` (see [20-email-capture.md](20-email-capture.md))
   - `/news-briefing --daily` → returns `NewsBriefing.markdown` (see [30-news-briefing.md](30-news-briefing.md))
   - `/remember mobile-captures` → returns recent mobile capture log

4. **Compose**. Wait for the three workers, then assemble the daily note in the section order from 00-architecture.md § `DailyNote`. Existing user-added content (work-log entries, manual notes) is preserved.

5. **(Optional) Render PDF**. If invoked with `--pdf`, dispatch `/daily-pdf --bundle` to render note + briefing into `YYYYMMDD-daily.pdf`. See [40-pdf-render.md](40-pdf-render.md).

6. **Emit summary to chat**. Short — "Daily note updated. 3 PRs ready to merge, 2 actionable emails, briefing of 12 newsletters. See `<path>`." Do not dump the whole note into chat.

## Composition order

Order of sections in the `DailyNote` is **fixed** because Nic skims top-to-bottom:

| # | Section              | Why this position                                |
| - | -------------------- | ------------------------------------------------ |
| 1 | Today's calendar     | Time-anchored — must see first                   |
| 2 | What needs attention | Email/captures — highest-friction items today    |
| 3 | News briefing        | Editorial — read with coffee, sets context       |
| 4 | Active work          | Reference — checked when planning blocks of work |
| 5 | Work log             | Append-only journal — bottom                     |

The news briefing sits in position 3, between immediate-action items (above) and reference state (below). This placement was decided in the 2026-05-19 design pass — rationale: briefing is _contextual_, not _actionable_; placing it between the two categories signals "this is for orientation, not for tasking".

## What `/daily` does NOT do

- **Does not curate.** Curation belongs to the worker workflows (`/email`, `/news-briefing`). `/daily` composes; workers decide.
- **Does not prioritise.** No "do this first" annotation. The daily note reports; ranking is `/pull`'s job.
- **Does not file tasks.** `/email` files the email-derived tasks; `/daily` just lists their IDs.
- **Does not synthesise the briefing.** That's `/news-briefing`'s job; `/daily` accepts its markdown verbatim.
- **Does not render PDF inline.** PDF rendering is delegated to the `daily-pdf` workflow. `/daily --pdf` is a fan-out, not an inline call.

This is the core/tools split applied: `/daily` (core) is the workflow plumbing; the workers (tools) do the domain-specific curation.

## Invocation

| Form                        | Behaviour                                                     |
| --------------------------- | ------------------------------------------------------------- |
| `/daily`                    | Build/update today's note; print summary line to chat         |
| `/daily --pdf`              | Same + render PDF bundle                                      |
| `/daily --refresh-briefing` | Re-run only the `/news-briefing` step and update that section |
| `/daily --refresh-email`    | Re-run only the `/email --daily` step                         |

## Fitness rubric reference

`/daily` is plumbing — its fitness is binary: did each worker run, did the note structure match the SSoT, was the PDF rendered when requested? No qualitative rubric needed beyond:

- All four sections present and populated (or explicit "none today")
- Worker outputs incorporated verbatim (no /daily-side editing of curated content)
- Work-log + manual edits preserved across re-runs
- Section order matches 00-architecture.md

## Open questions

- **Section 3 ordering when briefing is empty**: if `/news-briefing` returns "no newsletters in window", does the section appear with a placeholder or get omitted? Current proposal: include with "_No newsletter activity in the last 24h._" — keeps the structure stable for diffing.
- **Re-run idempotency**: a second invocation in the same day should update (not duplicate) sections. Worker calls should be re-dispatched (state may have changed). Existing logic in `/daily` handles this — verify after migration.
