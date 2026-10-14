---
alias:
  - wf-qa-visual
description: Fills wf-qa evaluate slot for rendered output -- capture artifact images and judge multimodally against criteria.
id: wf-qa-visual
status: ready
tags:
  - wf-template
  - qa
  - visual-qa
title: wf-qa-visual
type: template
---

## What this step does

Fills the evaluate slot of [[wf-qa]] for something a person looks at: how the evidence is captured,
and how it is judged. Criteria assembly and the verdict contract belong to the parent and are not
restated here. Do not dispatch it standalone -- without the parent there are no criteria to judge
against.

Iteration is not part of this workflow: the composing brief owns round caps and the separation
between whoever revises and whoever judges.

## Capture

Source code is not evidence of rendered state. Every criterion is decided against an image of the
artifact as actually rendered, at the viewport the criteria are written for.

- Capture a baseline before any change is drafted -- a criterion judged against a missing or stale
  baseline is `UNMET`.
- A capture harness's exit code does not establish that a capture happened. Confirm the image files
  exist and are large enough to be a real render -- a blank or error page still writes a file and
  still exits zero.
- A capture that is missing, blank or truncated is a capture failure, not a visual failure. Halt and
  report it as such, rather than sending someone to fix working code for a broken tool.

Target URLs, viewports, view names and the capture command come from the instantiating task, never
from this template.

## Judge

The evaluator must be able to ingest images -- one that can't is a capability failure: halt and say
so, rather than falling back to reading the diff.

- Judge every in-scope view together in one pass, so cross-view regressions are visible.
- Re-judge criteria already met in earlier passes -- a fix to one view can break another.
- Where criteria are silent, judge layout, alignment, hierarchy, contrast, and legibility.

Evidence is a citation into the image -- the region or coordinates where the thing is or is not. A
described code change, a passing test, or a diff imperceptible at the stated viewport decides
nothing and leaves the criterion `UNMET`.
