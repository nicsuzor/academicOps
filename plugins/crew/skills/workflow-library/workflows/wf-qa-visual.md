---
alias:
  - wf-qa-visual
description: "Review: how to capture and judge rendered visual output when selected by the composed workflow."
id: wf-qa-visual
status: ready
tags:
  - wf-template
  - qa
  - visual-qa
title: Visual quality check
type: template
---

## What this step does

Captures and judges rendered visual output whenever the composed workflow selects visual inspection. Criteria and verdict handling follow the composed workflow and task.

## Capture

- Judge an image of the real artifact as rendered at the viewport the criteria name, never the source code.
- Check the image is a real render, not a blank or error page. A broken capture tool is a tool failure to report, not a defect in the work.
- Targets, viewports and capture commands come from the task.

## Judge

- Look at the images directly; an evaluator that cannot read images stops and says so.
- Judge all views together, so a fix in one that breaks another shows.
- Where criteria are silent, judge layout, hierarchy, contrast and legibility.

## Evidence

Cite the region of the image where each criterion holds or fails.

## When to include

Whenever the composed workflow selects visual inspection of rendered output.
