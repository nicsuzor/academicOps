# Daily Note Pipeline — Architecture

**Status**: draft (cowork-sandbox), proposed 2026-05-19. To land at `projects/aops/specs/daily/00-architecture.md` via PR.

**Sibling specs**:

- [10-daily-orchestrator.md](10-daily-orchestrator.md) — `/daily` skill (aops-core)
- [20-email-capture.md](20-email-capture.md) — `/email` workflow (aops-tools)
- [30-news-briefing.md](30-news-briefing.md) — `/news-briefing` workflow (aops-tools)
- [40-pdf-render.md](40-pdf-render.md) — daily PDF render workflow (aops-tools)

## Purpose

Define the daily-note pipeline as a single coherent system: which component owns which slice of the morning briefing, how data flows between them, and which side of the aops-core / aops-tools split each component sits on. This spec is the SSoT for **shared types and pipeline wiring**. Child specs describe individual workflows and inherit the definitions here.

## Pipeline

```
    ┌──────────────────────────────────────────────┐
    │           /daily  (aops-core)                │
    │           orchestrator + composer            │
    │                                              │
    │   1. Pull state (PRs, tasks, calendar)       │
    │   2. Call workflows in parallel:             │
    │        ├── /email --daily                    │
    │        ├── /news-briefing --daily            │
    │        └── /remember mobile-captures         │
    │   3. Compose daily note (markdown)           │
    │   4. (optional) /daily-pdf --bundle          │
    └─┬────────────┬─────────────┬─────────┬───────┘
      │            │             │         │
      ▼            ▼             ▼         ▼
aops-tools    aops-tools    aops-core   aops-tools
/email        /news-briefing /remember  daily-pdf
```

## Components and their homes

| Component        | Plugin     | Why                                                                                                                    |
| ---------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
| `/daily`         | aops-core  | Owns daily-note structure (SSoT). Non-fungible — the daily note is the agent's working memory. Stable across versions. |
| `/remember`      | aops-core  | Memory primitive. Non-fungible epistemic infrastructure.                                                               |
| `/email`         | aops-tools | Outlook-MCP-dependent. Replaceable if better mail integration arrives. Domain workflow on a fungible tool surface.     |
| `/news-briefing` | aops-tools | Outlook-MCP-dependent. Editorial curation is a content workflow, not framework infrastructure. Replaceable.            |
| daily-pdf-render | aops-tools | Built on top of the existing `/pdf` tool. Optional output format.                                                      |

This split applies the [aops-tools convention](../../../../aops-tools/GEMINI.md): aops-core provides non-fungible epistemic infrastructure; aops-tools provides optional domain skills that can be replaced when better external solutions arrive. See [50-aops-core-vs-tools.md](50-aops-core-vs-tools.md) for the migration plan and rationale (separate doc to keep this one focused on the steady-state design).

## Shared types

These types are referenced by all child specs. Defined here once.

### `DailyNote`

The markdown artefact `/daily` produces. Lives at `$ACA_DATA/daily/YYYYMMDD-daily.md`.

```
# Daily Note — YYYY-MM-DD

## Today's calendar
<events from calendar workflow>

## What needs attention
<EmailCapture.actionable + EmailCapture.fyi + mobile-captures>

## News briefing
<NewsBriefing.markdown>

## Active work
<PRs by state, ready tasks, in-progress epics>

## Work log
<timestamped entries appended through the day>
```

The `## News briefing` section is **new in this spec**. Currently absent in the live `/daily`. See [10-daily-orchestrator.md](10-daily-orchestrator.md) § Composition Order for placement rationale.

### `EmailCapture`

Returned by `/email --daily`. Three sub-fields:

```yaml
actionable:
  - task_id: <pkb-id>           # created by /email
    title: <short imperative>
    sender: <name>
    due: <ISO date or null>
fyi:
  - topic: <thread or email subject>
    quote: <verbatim relevant snippet>
    sender: <name>
    date: <ISO>
    relevance: <1 sentence on why Nic should see this>
archive_candidates:
  - entry_id: <outlook id>
    subject: <subject>
    reason: <why safe to archive>
```

See [20-email-capture.md](20-email-capture.md) for the workflow that produces this.

### `NewsBriefing`

Returned by `/news-briefing --daily`. Single field:

```yaml
markdown: |
  <300–500 word thematic briefing>

  ---

  _N newsletters reviewed: <publication list>. Last 24h._
```

The markdown follows the [news-briefing fitness rubric](../../rubrics/news-briefing.md) — lead with most interesting, synthesise across corpus, reporterly voice, no marketing adjectives.

See [30-news-briefing.md](30-news-briefing.md) for the workflow.

### `DailyPDF`

Optional artefact, produced when `/daily-pdf --bundle` is invoked (manually or via a `/daily --pdf` flag). Single PDF file at `$ACA_DATA/daily/YYYYMMDD-daily.pdf`. Combines the markdown daily note + news briefing into a print-readable bundle. Renderer config follows [aops-tools/pdf](../../../../aops-tools/skills/pdf/SKILL.md).

See [40-pdf-render.md](40-pdf-render.md) for the workflow.

## Trigger surfaces

| Trigger phrase / command  | Resolves to                                             |
| ------------------------- | ------------------------------------------------------- |
| `/daily`, "daily note"    | `/daily` skill (aops-core)                              |
| `/email`, "process inbox" | `/email` skill (aops-tools)                             |
| `/email --daily`          | `/email` skill (aops-tools), returns `EmailCapture`     |
| `/news-briefing`          | `/news-briefing` skill (aops-tools), inline markdown    |
| `/news-briefing --daily`  | `/news-briefing` skill, returns `NewsBriefing.markdown` |
| `/daily --pdf`            | `/daily` runs, then `/daily-pdf --bundle` (aops-tools)  |
| `/daily-pdf`              | direct PDF render of existing daily note                |

## DRY discipline

These conventions are defined HERE and not repeated in child specs:

- **Persona**: Nic, Professor (QUT Law), platform-governance researcher. Child specs reference "the persona in 00-architecture.md".
- **Time context**: "Morning routine, 7am, 3–5 minutes." Same.
- **Data location**: `$ACA_DATA` for outputs, `$AOPS_SESSION_ID` for session join key.
- **Quality standard**: Each child spec links to its fitness rubric; rubrics live in `../../rubrics/`.

Child specs should be ~150–300 lines, single responsibility, and reference back here for anything shared.

## Migration

Moving from current state to this design requires three PRs against `academicOps`:

1. **Move `/email`** from `aops-core/commands/email.md` to `aops-tools/skills/email/SKILL.md`. Update any `/daily` references.
2. **Land `/news-briefing`** as new skill at `aops-tools/skills/news-briefing/SKILL.md` (supersedes the original aops-core landing plan).
3. **Add `daily-pdf-render`** workflow at `aops-tools/skills/daily-pdf/SKILL.md` and update `/daily` to invoke it under a `--pdf` flag.

Details in [50-aops-core-vs-tools.md](50-aops-core-vs-tools.md).
