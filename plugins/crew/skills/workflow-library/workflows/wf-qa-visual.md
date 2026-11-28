---
alias:
  - wf-qa-visual
description: "Review: how to capture and judge rendered visual output inside a quality review."
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

Fills the quality review's check for anything visual. The criteria and the verdict belong to the review it sits in.

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

Inside a quality review of rendered output.
