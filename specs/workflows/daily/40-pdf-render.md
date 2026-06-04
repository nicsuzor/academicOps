# `/daily-pdf` — daily PDF bundle render

**Status**: draft (cowork-sandbox), proposed 2026-05-19. Spec to land at `projects/aops/specs/daily/40-pdf-render.md`. Skill to land at `aops-tools/skills/daily-pdf/SKILL.md` (new).

**Inherits**: [00-architecture.md](00-architecture.md) — persona, shared types (`DailyNote`, `NewsBriefing`, `DailyPDF`).

**Plugin**: `aops-tools`. Built on top of existing `aops-tools/skills/pdf/`.

## Responsibility

Render the day's `DailyNote` + `NewsBriefing` into a single printable PDF at `$ACA_DATA/daily/YYYYMMDD-daily.pdf`.

The bundle is **for reading away from the laptop** — morning coffee on the deck, weekend overview, the train. It is not a record or archive — the markdown daily note is the SSoT. The PDF is a convenience format that becomes stale the moment it's generated.

## Invocation forms

| Form                    | Behaviour                                                                   |
| ----------------------- | --------------------------------------------------------------------------- |
| `/daily-pdf`            | Render today's PDF from the existing daily note. Fails if no note.          |
| `/daily-pdf YYYY-MM-DD` | Render a specific past day's PDF.                                           |
| `/daily-pdf --bundle`   | Called by `/daily --pdf` — renders after the orchestrator updates note.     |
| `/daily-pdf --open`     | Render then open in the system PDF viewer (macOS `open`, Linux `xdg-open`). |

## Pipeline

1. **Locate inputs**:
   - Daily note: `$ACA_DATA/daily/YYYYMMDD-daily.md` (required — fail with clear message if absent)
   - News briefing markdown: already inlined in the daily note's `## News briefing` section (per 00-architecture.md). No separate fetch needed.
2. **Pre-process**:
   - Strip the `## Work log` section if it's empty or just template scaffolding (don't print blank pages).
   - Resolve any `[[wikilinks]]` to either footnotes or strip them (PDF readers can't follow them).
   - Convert relative paths in image references to absolute paths.
3. **Render**:
   - Invoke `aops-tools/skills/pdf` with the pre-processed markdown.
   - Page size: A4 (Nic prints occasionally). Margins: 20mm.
   - Fonts and styling: inherit the academic PDF profile from the `pdf` skill (Roboto, academic-typography). See [aops-tools/skills/pdf/SKILL.md](../../../../aops-tools/skills/pdf/SKILL.md).
   - Header: "Daily — YYYY-MM-DD".
   - Footer: page X of Y, generated timestamp.
4. **Write to**: `$ACA_DATA/daily/YYYYMMDD-daily.pdf`. Overwrite without prompt — the PDF is regenerable.
5. **Emit summary**: One line to chat — `PDF: <path> (N pages, news briefing: yes/no)`.

## Bundle composition

The PDF mirrors the daily-note section order from 00-architecture.md:

1. **Cover line** — date, weather (optional, if calendar workflow surfaces it)
2. **Today's calendar**
3. **What needs attention** — actionable email captures + mobile captures
4. **News briefing** — the full editorial briefing, inline
5. **Active work** — PRs by state, top 10 ready tasks
6. **Work log** — appended through day; included if non-empty at render time

**No section is omitted** for PDF render even if empty in the markdown (other than work-log) — empty sections print as "_(none today)_". Stable layout aids skimming.

## What this skill does NOT do

- **Does not re-curate**. The PDF reflects whatever the markdown note says. To refresh content, run `/daily --pdf` (orchestrator regenerates note, then renders) — not `/daily-pdf` alone.
- **Does not archive**. PDFs are ephemeral. No retention policy here.
- **Does not push** to any device, cloud, or print queue. Nic opens the file himself.

## Fitness contract

Minimal — this is plumbing on top of an existing tool:

- File exists at expected path post-render
- All sections from the markdown daily note appear in section-order
- No layout breakage (orphaned headings, image-missing markers, overlong code blocks)
- News briefing section renders with the synthesised thread visible at the top

## Migration notes

- New skill — no existing implementation to relocate.
- Depends on `aops-tools/skills/pdf` being usable as a library (it is — invoked programmatically by `/diagram`, `/extract`, etc.).
- `/daily --pdf` flag needs to be added to the `/daily` skill simultaneously. See [10-daily-orchestrator.md](10-daily-orchestrator.md) § Invocation table.

## Open questions

- **Dark mode for the PDF when read on phone late at night**? Probably no — academic typography is light-mode-only by convention. Defer until requested.
- **Email-to-self for backup**? Tempting but adds Outlook MCP dependency to a skill that otherwise only needs file I/O. Defer.
- **Auto-generate at end-of-day** via scheduled task? Possible later. Manual invocation in v1.
