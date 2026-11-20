---
alias:
  - wf-qa-visual
description: Fills evaluate slot for rendered output -- capture artifact images and judge multimodally against criteria.
id: wf-qa-visual
status: ready
tags:
  - wf-template
  - qa
  - visual-qa
title: Visual QA Evaluation
type: template
---

## What this step does

Fills the evaluation slot for rendered visual output: defines how visual evidence is captured and judged multimodally. Criteria assembly and overall verdict contracts belong to the parent review workflow and are not restated here; do not dispatch standalone without parent criteria. Iteration, round caps, and separation between author and judge belong to the composing brief.

## Capture

Source code is not evidence of rendered state. Every criterion is decided against an image of the artifact as actually rendered at the viewport the criteria specify.

- Capture a baseline before any change is drafted; a criterion judged against a missing or stale baseline is `UNMET`.
- A capture tool's zero exit code does not prove a valid render. Verify image files exist and are large enough to be real renders rather than blank or error pages.
- A missing, blank, or truncated image is a capture failure, not a visual failure -- halt and report it rather than sending an author to fix working code for a broken tool.
- Target URLs, viewports, view names, and capture commands come from the instantiating task, never from this template.

## Judge

The evaluator must ingest images directly; an evaluator without multimodal image capability is a capability failure -- halt and report it rather than falling back to reading diffs.

- Judge all in-scope views together in one pass so cross-view regressions are visible.
- Re-judge criteria met in earlier passes, since fixing one view can break another.
- Where criteria are silent, judge layout, alignment, hierarchy, contrast, and legibility.

## Evidence contract

Evidence is a citation into the rendered image (region or coordinates showing where the criterion holds or fails). A described code change, a passing unit test, or a diff imperceptible at the stated viewport decides nothing and leaves the criterion `UNMET`.
