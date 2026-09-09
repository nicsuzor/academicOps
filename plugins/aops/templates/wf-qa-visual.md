---
alias:
  - wf-qa-visual
category: process
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

Fills `[[wf-qa]]`'s evaluate slot for visual and rendered artifacts (UI, charts, layouts). Criteria assembly and verdict reporting belong to the parent gate; do not dispatch standalone.

## Capture

1. **Baseline capture**: Capture pre-modification baseline renders to serve as comparative referents.
2. **Verify render artifacts**: Confirm image files exist and contain actual rendered content. A zero-exit code with a blank or truncated image indicates a harness failure; halt rather than failing criteria.
3. Target viewports and capture commands are specified by the instantiating task.

## Judge

1. **Multimodal inspection**: Evaluators must inspect images directly; code diff inspection does not substitute for visual evidence.
2. **Holistic evaluation**: Evaluate all in-scope views together to detect regressions across layouts.
3. **Core dimensions**: Inspect spatial alignment, text contrast, typographic hierarchy, and overflow handling.
4. **Evidence format**: Cite image filenames and specific spatial regions or coordinates.
