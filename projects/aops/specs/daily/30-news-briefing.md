# `/news-briefing` — editorial morning briefing workflow

**Status**: draft (cowork-sandbox), proposed 2026-05-19. Spec to land at `projects/aops/specs/daily/30-news-briefing.md`. Skill to land at `aops-tools/skills/news-briefing/SKILL.md` (supersedes earlier aops-core landing plan).

**Inherits**: [00-architecture.md](00-architecture.md) — persona, time context, shared types (`NewsBriefing`).

**Plugin**: `aops-tools`. Rationale in [50-aops-core-vs-tools.md](50-aops-core-vs-tools.md).

**Fitness rubric**: [../../rubrics/news-briefing.md](../../rubrics/news-briefing.md). Reviewer applies it per-output.

## Responsibility

Scan recent newsletter and mailing-list email; produce a short (~300–500 word) thematic morning briefing of what's interesting and useful. Distinct from:

- `/daily` (orchestrator — does no curation)
- `/email` (action-task extraction — does no editorial synthesis)
- News-feed aggregators (no synthesis, just enumeration)

This is the editorial layer that turns "10 newsletters arrived" into "here is what to know."

## Invocation forms

| Form                     | Behaviour                                                                      |
| ------------------------ | ------------------------------------------------------------------------------ |
| `/news-briefing`         | Interactive — print briefing inline in chat.                                   |
| `/news-briefing --daily` | Daily mode — return `NewsBriefing.markdown` for `/daily` to splice into note.  |
| `/news-briefing --save`  | Write to `$ACA_DATA/daily/YYYYMMDD-news-briefing.md` as a standalone artefact. |

When the caller (e.g. `/daily`) supplies an explicit output path, write to that path. See SKILL.md § Output destination for harness-override clause.

## Workflow phases (named, for cross-reference)

Detail in SKILL.md; this spec carries the contract.

| Phase  | Step                                | Output                                        |
| ------ | ----------------------------------- | --------------------------------------------- |
| **P1** | Inventory newsletter-shaped email   | List of candidate items with metadata         |
| **P2** | Classify (newsletter / noise / amb) | Filtered list, 10–20 newsletter items typical |
| **P3** | Fetch bodies                        | Plain-text bodies for newsletter items        |
| **P4** | Extract items per newsletter        | Per-newsletter: lead + ≤4 secondary items     |
| **P5** | Cluster by theme                    | Topic buckets across newsletters              |
| **P6** | Draft briefing                      | Lead-with-most-interesting; thematic, ~400wd  |
| **P7** | Cut pass                            | Drop weakest item if >550 words               |

## Fitness contract

Briefings must satisfy the [rubric](../../rubrics/news-briefing.md). Summary of the eight dimensions (full definitions in the rubric):

1. Synthesis over enumeration
2. Lead with the most interesting
3. Specificity (numbers, names, dates)
4. Reporterly voice (no marketing adjectives)
5. Field-aware curation (mapped to Nic's research)
6. Length discipline (300–500 target, hard prompt to cut at 550)
7. Traceability (sources named inline + attribution footer)
8. No stenography (synthesis where multiple sources cover the same story)

## Outlook MCP quirks (referenced by 20-email-capture.md)

These are documented here because the news-briefing skill is where they were first discovered and codified. Other email-touching workflows should reference this section rather than restating.

### DASL filter syntax

```
@SQL="urn:schemas:httpmail:datereceived" > '<YESTERDAY-DATE>'
```

- `@SQL=` prefix REQUIRED. Omitting returns `Condition is not valid`.
- Use date-only string (`'2026-05-18'`). Full ISO timestamps (`'2026-05-18T00:00:00'`) sometimes fail.
- `> 'YYYY-MM-DD'` returns mail from start of NEXT day forward. With today=2026-05-19, `> '2026-05-18'` returns ~24–36h.

### Result truncation handling

If query returns `limit` rows exactly, suspect truncation. Re-pull with narrower date filter or higher limit. Verify recent slice with `received >= '<TODAY-DATE>'`.

### Government regulator carve-out for `no-reply@`

`no-reply@humanrights.gov.au`, `*.gov.au`, `*.ohchr.org` often send editorial monthly bulletins. Include when subject reads as content summary; exclude when transactional.

### Substack from-name ambiguity

`<author>@substack.com` may be a real newsletter or a Substack notification. INCLUDE clear editorial headlines; SKIP "New post" / "X liked your post" notifications. Worked examples in SKILL.md.

## Validated by

Dogfood cycle 2026-05-19 (junior coordinator + contextless executor + pauli APPROVE + Marsha PASS). See:

- Skill draft: `/Users/suzor/junior/.dogfood-run/proposed/skills/news-briefing/SKILL.md`
- Sample output: `/Users/suzor/junior/.dogfood-run/news-briefing-output-1.md`
- Friction log: in sample output footer
- Reviewer reports: pauli APPROVE (5 edits applied), Marsha PASS (length tweak applied)
- Migration task: `aops-653897f7` (PKB) — needs amendment to point at aops-tools/, not aops-core/

## Open questions

- **Two accounts vs one**: current draft pulls both QUT and personal accounts. Should `--daily` window vary per account (QUT inbox is high-noise; personal has all the newsletters)? Current answer: yes — already split by account in SKILL.md.
- **Briefing in the daily PDF**: see [40-pdf-render.md](40-pdf-render.md) — does the briefing appear inline in the PDF, or as a separate page break? Current proposal: inline, single bundle.
- **Newsletter follow-list**: should there be a curated allow-list of "always include these senders" maintained in `$ACA_DATA/news-briefing/senders.yaml`? Not in v1; let the heuristics + judgement do it. Add only if false negatives accumulate.
