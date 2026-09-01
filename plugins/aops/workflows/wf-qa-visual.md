---
alias:
- wf-visual-qa-loop-wf-visual-qa-loop
- wf-visual-qa-loop
- wf-qa-visual
category: process
created: 2026-08-19T12:21:20.658336284+00:00
description: Fills the evaluate slot of [[wf-qa]] for rendered output — capture the artifact as an image and judge it multimodally against the locked criteria. Select it when the criteria are about what a user sees (UI, dashboards, graphs, layouts); not for non-visual artifacts, and never standalone, since the criteria and the verdict contract come from the parent.
id: wf-qa-visual
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
permalink: wf-qa-visual
status: ready
tags:
- wf-template
- workflow
- visual-qa
- image-judging
- qa
title: wf-qa-visual
type: template
---

## What this step does

**This workflow fills the evaluate slot of [[wf-qa]].** It supplies only what is particular to
judging something a person looks at: how the evidence is captured, and how it is judged. Criteria
assembly and the per-criterion verdict contract belong to the parent and are not restated here.

Do not dispatch it standalone — without the parent there are no criteria to evaluate against.

A visual defect rarely clears in one pass. Iteration is not part of this workflow: compose
[[wf-loop]] around the parent gate, which owns round caps, no-progress detection and the separation
between whoever revises and whoever judges.

## Capture

Source code is not evidence of rendered state. Every criterion is decided against an image of the
artifact as actually rendered, at the viewport the criteria are written for.

- **Capture a baseline before any change is drafted.** The baseline is the comparative referent for
  the whole evaluation; a criterion judged against a missing or stale referent is `UNMET`.
- **A capture harness's exit code does not establish that a capture happened.** Confirm the image
  files exist at the path the evaluation will read from, and that each is large enough to be a real
  render — a blank page or an error page still writes a file, and still exits zero.
- **A capture that is missing, blank or truncated is a capture failure, not a visual failure.** Halt
  and report it as such. Reporting it as unmet criteria sends someone to revise working code to fix
  a broken tool.

Target URLs, viewports, view names and the capture command itself come from the instantiating task,
never from this template.

## Judge

The evaluator must be able to ingest images. An evaluator that cannot read the captures is a
capability failure — halt and say so, rather than falling back to reading the diff.

- Judge every in-scope view together in one pass, so cross-view regressions and whole-of-product
  incoherence are visible rather than split across separate verdicts.
- Re-judge criteria already met in earlier passes. A change that fixes one view while breaking
  another is a regression, and only re-judging surfaces it.
- Where the criteria are silent, the visual questions worth asking are spatial layout, alignment and
  hierarchy; contrast, typography and legibility; and whether what matters is prominent and what
  does not is suppressed.

Evidence for a visual criterion is a citation into the image — the region or coordinates where the
thing is or is not, in which capture. A described code change, a passing test, or a diff that is
real but imperceptible at the stated viewport decides nothing and leaves the criterion `UNMET`.

## Related

- [[wf-qa]] — the parent gate this fills the evaluate slot of
- [[wf-loop]] — iteration around the parent when defects need more than one pass
