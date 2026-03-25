# Bundle Template

Overall structure for the briefing bundle file written to `$ACA_DATA/daily/YYYYMMDD-bundle.md`.

## Template

```markdown
---
type: bundle
date: YYYY-MM-DD
generated: YYYY-MM-DDTHH:MM:SS
source_daily: YYYYMMDD-daily.md
item_counts:
  decisions: N
  calendar: N
  emails: N
  fyi: N
  carryover: N
  total: N
qa_issues: []
---

# Morning Brief -- YYYY-MM-DD

## Executive Summary

[Max 10 lines]

1. **Item counts**: N decisions, N emails, N FYIs, N carryover
2. **Most urgent**: **[item description]** -- [why]
3. **Calendar**: N meetings, [free block summary]
4. **Sequence**: [Recommended work order in 1-3 sentences]

Annotations: `approved` | `send` | `decline` | `defer to DATE` | `noted` | `task: [title]`

---

## Decisions

### [Title] -- [[project]]

[Coversheet per [[references/coversheet-template]]]

---

## Calendar

### Today -- [Day, Date]

#### HH:MM -- [Meeting title]

**Attendees**: [Names with brief context]
**Prep**: [What to review or think about beforehand]
**Pre-read**: [[document]] (if applicable)

#### Free blocks

- HH:MM-HH:MM -- [duration] suitable for [deep work / admin / break]

### Tomorrow -- [Day, Date]

[Same format, briefer -- just awareness, not prep]

---

## Emails

### Reply: [Subject] -- to [Recipient]

[Draft per [[references/email-template]]]

---

## FYI

### [Project] -- [Headline]

[2-3 sentence summary. Source: [attribution].]

- [ ] Noted

<!-- @nic: noted -->

### [Project] -- [Headline with task potential]

[2-3 sentence summary. Source: [attribution].]

- [ ] Noted

<!-- @nic: noted / task: [suggested title] -->

---

## Carryover

Items from previous days, oldest first.

- [ ] [Item description] (carried N days) <!-- @nic: act / defer to DATE / cancel -->
- [ ] [Item description] (carried N days)
- [ ] ⚠️ [Item carried 3+ days] (carried N days) -- decide: act, defer, or cancel?
      <!-- @nic: act / defer to DATE / cancel -->

---

## Done

_You've reached the end of today's brief._
```

## Section ordering (fixed)

Energy-intensive first, passive last. Do not reorder:

1. Executive Summary
2. Decisions
3. Calendar
4. Emails
5. FYI
6. Carryover
7. Done (empty finish line)

## Frontmatter fields

| Field          | Required | Purpose                                                    |
| -------------- | -------- | ---------------------------------------------------------- |
| `type`         | Yes      | Always `bundle`                                            |
| `date`         | Yes      | Bundle date (YYYY-MM-DD)                                   |
| `generated`    | Yes      | ISO timestamp of generation                                |
| `source_daily` | Yes      | Filename of the daily note this bundle reads               |
| `item_counts`  | Yes      | Counts by section for quick reference                      |
| `qa_issues`    | Yes      | Empty list `[]` if clean; issues logged during self-review |

## Density targets

- **Total items**: 5-15 (warn if outside, fail if >25)
- **Executive summary**: Max 10 lines
- **Coversheets**: Max 15 non-blank lines above the fold
- **FYIs**: Max 5 lines per item above the fold
- **Carryover**: One line per item plus annotation target
