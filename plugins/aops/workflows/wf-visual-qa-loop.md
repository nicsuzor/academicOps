---
title: Visual QA Loop
type: template
category: gate
description: Automated visual screenshot, judging, and revision loop with hard failsafes. Select when verifying graphical user interfaces, dashboards, or web layouts. Not for non-visual text/code verification (use `wf-qa`).
tags: [visual-qa, screenshots, ui, rendering, loop, gate]
---

# Gate: Visual QA Loop

Convergence loop for user interface styling and visual layout with automated screenshot validation.

## 1. Baseline Capture

- Render target UI in headless browser at specified viewport (`<viewport>`).
- Capture baseline screenshot of `<target-url-or-view>`.
- Confirm screenshot is non-blank and above size threshold.

## 2. Visual Judging (Independent Judge)

- Independent judge inspects screenshot against visual acceptance criteria:
  - Spatial layout, alignment, and hierarchy.
  - Color contrast, typography, and element visibility.
  - Responsiveness and suppression of clutter.
- Emit structured verdict table with binary MET/UNMET status per criterion.

## 3. Visual Remediation (Drafter)

- If unmet criteria exist, drafter modifies CSS/layout code to address specific visual defects.
- Drafter must not modify test harness or judging criteria.

## 4. Re-Capture and Regression Check

- Re-render UI and capture new screenshot.
- Re-evaluate all criteria (both previously passed and newly fixed) to prevent regressions.

## 5. Failsafe Guards

- Enforce iteration cap (`<max-iterations>`, default 5).
- Terminate immediately if unmet criteria count does not decrease between rounds (`FAILSAFE_NO_IMPROVEMENT`).
- Enforce wall-clock cap (`<timeout-minutes>`, default 30m).

## Exit Condition

`SUCCESS_ALL_PASS` on visual criteria, or clean failsafe termination.
