# Daily Note Pipeline — spec series

Connected specs describing the morning daily-briefing pipeline: `/daily` orchestrator, the worker workflows it composes (`/email`, `/news-briefing`), and the optional PDF render. Drafted 2026-05-19 in the cowork sandbox; to land at `projects/aops/specs/daily/` via PR (see [50-aops-core-vs-tools.md](50-aops-core-vs-tools.md) § Migration 4).

| # | Spec                                                | Plugin          | Owns                                    |
| - | --------------------------------------------------- | --------------- | --------------------------------------- |
| 0 | [Architecture](00-architecture.md)                  | (cross-cutting) | Pipeline, shared types, DRY conventions |
| 1 | [`/daily` orchestrator](10-daily-orchestrator.md)   | aops-core       | Daily-note structure + composition      |
| 2 | [`/email` capture](20-email-capture.md)             | aops-tools      | Email → PKB tasks + FYI                 |
| 3 | [`/news-briefing` editorial](30-news-briefing.md)   | aops-tools      | Newsletters → thematic briefing         |
| 4 | [`/daily-pdf` render](40-pdf-render.md)             | aops-tools      | Daily note → PDF bundle                 |
| 5 | [aops-core vs aops-tools](50-aops-core-vs-tools.md) | (cross-cutting) | Split rationale + migration plan        |

## How to read these

Read **0 first** — it carries the shared types and DRY conventions all child specs inherit. Then:

- For **what each component does**, read its individual spec (1–4).
- For **why each lives where it does**, read 5.
- For **how to land all this in canonical**, read 5 § Migration plan.

## Related artefacts

- Sample news-briefing output (Marsha-reviewed PASS): `/Users/suzor/junior/.dogfood-run/news-briefing-output-1.md`
- News-briefing fitness rubric: `/Users/suzor/junior/.dogfood-run/proposed/rubrics/news-briefing.md`
- News-briefing skill draft: `/Users/suzor/junior/.dogfood-run/proposed/skills/news-briefing/SKILL.md`
- Original promotion task (needs amendment): PKB `aops-653897f7`
