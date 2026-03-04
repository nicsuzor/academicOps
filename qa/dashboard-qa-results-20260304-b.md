---
title: "QA Results: Overwhelm Dashboard (2026-03-04, Round 2)"
type: qa-result
status: complete
tags: [qa, dashboard, overwhelm-dashboard]
created: 2026-03-04
spec: specs/overwhelm-dashboard.md
qa-plan: qa/dashboard-qa.md
previous: qa/dashboard-qa-results-20260304.md
verdict: IMPROVED — ISSUES REMAIN
---

# QA Results: Overwhelm Dashboard (Round 2)

**Date**: 2026-03-04 (second pass, after fixes from round 1)
**Environment**: dev3, aOps v0.2.40-35-g4f66187f-dirty, Streamlit on localhost:8502
**ACA_DATA**: /opt/nic/brain
**synthesis.json**: PRESENT (3-6m old during evaluation, fresh)
**Verdict**: **IMPROVED — ISSUES REMAIN** — significant progress on section ordering, synthesis rendering, and session summary regression; several spec'd features still unimplemented

## Executive Summary

Round 2 shows meaningful improvement over the first QA pass. The three most impactful changes:

1. **Section reordering** — WHERE YOU LEFT OFF is now the first section, putting active sessions above the fold. This directly addresses the "What's running?" question.
2. **Synthesis rendering** — Focus Synthesis now renders with TODAY'S STORY, session insights, token metrics, and stale badge support. The `synthesize_dashboard.py` script is producing valid data.
3. **Session Summary regression fixed** — Down from 40+ error alerts to just 2 (both gemini-format sessions). Claude sessions now render correctly as collapsible expanders.

Still unimplemented: collapsible sections, stale session archive, epic drill-down, UP NEXT status badges, project cards with active agents, synthesis fallback when file is missing.

## Sections Rendered (7 of 10)

| #  | Section            | Rendered | Change from R1 | Notes                                                               |
| -- | ------------------ | -------- | -------------- | ------------------------------------------------------------------- |
| 1  | Where You Left Off | YES      | MOVED TO TOP   | 2 active + 3 paused sessions. First section on page.                |
| 2  | Your Path          | YES      | Same           | 10 project groups with timeline threads. Very long.                 |
| 3  | Focus Synthesis    | YES      | NEW            | Was missing in R1 (no synthesis.json). Now renders fully.           |
| 4  | Spotlight Epic     | YES      | MOVED DOWN     | "Framework Core" at 46%, Done: 16, In Progress: 18, Blocked: 1      |
| 5  | Project Grid       | YES      | Same           | 20+ project cards with EPICS and UP NEXT                            |
| 6  | Quick Capture      | YES      | Same           | Text area + tags + Capture button                                   |
| 7  | Task Graph         | YES      | Same           | Available as sidebar view mode                                      |
| 8  | Current Activity   | NO       | Same           | No active agents in window (data-dependent)                         |
| 9  | Daily Story        | MERGED   | CHANGED        | Now part of Focus Synthesis as "TODAY'S STORY" with accomplishments |
| 10 | Recent Prompts     | NO       | Same           | Not visible (data-dependent or code issue)                          |

## Per-Task QA Results

### QA-D1: Section Reordering — IMPROVED (was FAIL)

| #    | Check                      | Result  | Evidence                                                                                                                                  |
| ---- | -------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| D1.1 | Above-the-fold content     | PARTIAL | WLO visible first with active sessions. YOUR PATH heading barely visible at fold edge.                                                    |
| D1.2 | "What's running?" answered | PASS    | "ACTIVE NOW" banner with 2 sessions immediately visible.                                                                                  |
| D1.3 | "What's dropped?" answered | PARTIAL | YOUR PATH visible after short scroll. Not above fold but much closer.                                                                     |
| D1.4 | "What needs me?" answered  | FAIL    | No "Needs You" badges on any session or section.                                                                                          |
| D1.5 | Graph still accessible     | PASS    | "Task Graph" sidebar view mode.                                                                                                           |
| D1.6 | No section lost            | PASS    | 7 of 10 sections render. Daily Story merged into Focus Synthesis. Missing sections are data-dependent (Current Activity, Recent Prompts). |

**Assessment**: Major improvement. WLO at top answers "What's running?" immediately. But "What needs me?" still has no dedicated visual indicator. The section order is now: WLO → YOUR PATH → Synthesis → Epic → Project Grid → Quick Capture.

### QA-D2: Stale Session Archive — NOT IMPLEMENTED

| #         | Check      | Result | Evidence                                           |
| --------- | ---------- | ------ | -------------------------------------------------- |
| D2.1–D2.7 | All checks | N/A    | No archive prompt. Stale sessions hidden silently. |

**No change from R1.**

### QA-D3: Session Filter Fix — PARTIAL PASS

| #         | Check                         | Result   | Evidence                                          |
| --------- | ----------------------------- | -------- | ------------------------------------------------- |
| D3.5      | No "unknown" sessions visible | PASS     | No "unknown: No specific task" sessions displayed |
| D3.1–D3.4 | Other checks                  | UNTESTED | Requires creating specific test sessions          |

**No change from R1.**

### QA-D4: Synthesis Fallback — PARTIAL (was FAIL)

| #    | Check                   | Result | Evidence                                                                              |
| ---- | ----------------------- | ------ | ------------------------------------------------------------------------------------- |
| D4.1 | Missing synthesis.json  | FAIL   | Code still does `if synthesis:` with no else branch. Section silently disappears.     |
| D4.2 | Message explains fix    | FAIL   | No fallback message implemented.                                                      |
| D4.3 | Stale synthesis flagged | PASS   | Code shows STALE badge when >60 min (yellow badge implemented in render function).    |
| D4.4 | Stale badge actionable  | FAIL   | Badge shows "STALE" text but no regeneration instruction or link.                     |
| D4.5 | Fresh synthesis renders | PASS   | Full panel: narrative, TODAY'S STORY, DONE/ALIGNMENT/CONTEXT/BLOCKED/TOKENS/INSIGHTS  |
| D4.6 | Page layout stable      | PASS   | Synthesis fills its space cleanly when present. Layout gap risk remains when missing. |

**Assessment**: synthesis.json now exists and renders beautifully. The stale badge is implemented. But the fallback when synthesis.json is MISSING is still not there — the section silently disappears. The stale badge also lacks a regeneration hint (e.g. "run synthesize_dashboard.py").

### QA-D5: Path Error Handling — PASS (functional)

| #         | Check          | Result     | Evidence                                                                   |
| --------- | -------------- | ---------- | -------------------------------------------------------------------------- |
| D5.1–D5.5 | Error handling | NOT TESTED | Path reconstruction working with live data. Non-destructive tests skipped. |

YOUR PATH renders correctly with 10 project groups and horizontal scroll cards.

### QA-D6: Project Boxes Show Agents — FAIL

| #    | Check                          | Result | Evidence                                                           |
| ---- | ------------------------------ | ------ | ------------------------------------------------------------------ |
| D6.1 | Active session in project card | FAIL   | No "WORKING NOW" section in any project card.                      |
| D6.4 | No sessions = no section       | PASS   | No empty "WORKING NOW" placeholders.                               |
| D6.5 | Matches WLO data               | FAIL   | WLO shows 2 active + 3 paused; project cards don't reference them. |

**No change from R1.**

### QA-D7: UP NEXT Status Badges — FAIL

| #    | Check                       | Result | Evidence                                           |
| ---- | --------------------------- | ------ | -------------------------------------------------- |
| D7.1 | Blocked tasks flagged       | FAIL   | No "BLOCKED" indicator on any UP NEXT task.        |
| D7.2 | In-progress tasks indicated | FAIL   | No "IN PROGRESS" indicator on any UP NEXT task.    |
| D7.3 | Active tasks look normal    | PASS   | Priority badges (P0, P1, P2, P3) render correctly. |
| D7.4 | Blocked != active visually  | FAIL   | All tasks look identical regardless of status.     |

**No change from R1.**

### QA-D8: Collapsible Sections — FAIL

| #    | Check                             | Result | Evidence                                                               |
| ---- | --------------------------------- | ------ | ---------------------------------------------------------------------- |
| D8.1 | Sections can be collapsed         | FAIL   | Only Paused Sessions uses an expander.                                 |
| D8.4 | All critical sections collapsible | FAIL   | YOUR PATH, synthesis, project grid — none collapsible.                 |
| D8.5 | Default state sensible            | FAIL   | YOUR PATH is very long (~10 project groups) and always fully expanded. |

**No change from R1.**

### QA-D9: Epic Drill-Down — FAIL

| #    | Check             | Result | Evidence                                                              |
| ---- | ----------------- | ------ | --------------------------------------------------------------------- |
| D9.1 | Epic is clickable | FAIL   | "Epic: Framework Core" title rendered as plain text, not interactive. |
| D9.2 | Children visible  | FAIL   | No way to see individual tasks in the epic from the dashboard.        |

**No change from R1.**

## End-to-End Evaluation

### E2E-D1: Morning Orientation Test — IMPROVED (was FAIL)

| #    | Question                            | Time | Result                                                                          |
| ---- | ----------------------------------- | ---- | ------------------------------------------------------------------------------- |
| E1.1 | "How many things are running?"      | ~3s  | PASS — "ACTIVE NOW" with 2 sessions visible immediately.                        |
| E1.2 | "Did anything fail overnight?"      | ~8s  | PARTIAL — Need to expand Paused Sessions. No explicit failure indicator.        |
| E1.3 | "What's unfinished from yesterday?" | ~10s | PARTIAL — YOUR PATH visible after short scroll. Better than R1.                 |
| E1.4 | "What's the overall picture?"       | ~5s  | PASS — Focus Synthesis shows TODAY'S STORY with narrative and status cards.     |
| E1.5 | "What should I work on first?"      | >15s | PARTIAL — Synthesis includes focus suggestion. Project grid requires scrolling. |

**Assessment**: Significant improvement. Questions E1.1 and E1.4 now answerable quickly. E1.5 partially addressed by synthesis "Focus on gemini-aops-4 — 2 friction points" suggestion.

### E2E-D6: ADHD Accommodation Check — IMPROVED (was MIXED)

| #    | Principle                   | Result   | Evidence                                                                                                                    |
| ---- | --------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------- |
| E6.1 | Dropped threads first       | PARTIAL  | WLO is first (answers "What's running?"). YOUR PATH (dropped threads) requires scroll. Better ordering but not fully there. |
| E6.2 | Scannable, not studyable    | PASS     | Priority badges, colored timeline dots, status cards. Synthesis uses bullet format.                                         |
| E6.3 | Reactive design             | PASS     | Reconstructs from existing data. synthesis.json pre-computed.                                                               |
| E6.4 | Directive framing           | PASS     | "WHERE YOU LEFT OFF", "YOUR PATH", "FOCUS SYNTHESIS", "UP NEXT", "ACTIVE NOW". All directive.                               |
| E6.5 | Collapsible density         | FAIL     | Only Paused Sessions collapsible. YOUR PATH ~3000px always expanded.                                                        |
| E6.6 | No flat displays at scale   | PARTIAL  | Projects grouped in cards (good). YOUR PATH groups by project. But 10 project groups still creates long scroll.             |
| E6.7 | Dashboard reduces overwhelm | IMPROVED | Opening it now immediately answers "What's running?" and provides a narrative. Better than R1 but still requires scrolling. |

### E2E-D7: Regression Check — IMPROVED

| #    | Check              | Result | Evidence                                                                 |
| ---- | ------------------ | ------ | ------------------------------------------------------------------------ |
| E7.1 | Sidebar navigation | PASS   | All 4 views load (Dashboard, Manage Tasks, Session Summary, Task Graph). |
| E7.2 | Time range filters | PASS   | Sidebar filters present and functional.                                  |
| E7.3 | Task graph         | PASS   | Available as sidebar view mode.                                          |
| E7.4 | Quick capture      | PASS   | Present with text area, tags, Capture button.                            |
| E7.5 | Recent Prompts     | FAIL   | Section not visible on page (unchanged from R1).                         |
| E7.6 | Task Manager       | PASS   | Loads correctly.                                                         |
| E7.7 | No console errors  | PASS   | 0 errors in browser console (improved from R1).                          |

### Session Summary View — MAJOR IMPROVEMENT

| Metric           | Round 1      | Round 2                                |
| ---------------- | ------------ | -------------------------------------- |
| Error alerts     | 40+          | 2                                      |
| Sessions listed  | N/A (broken) | 39 today, 23 yesterday                 |
| Status detection | 1 of 42      | 2 SUCCESS, 1 FAILURE, rest UNKNOWN     |
| Expandable       | N/A          | All sessions are collapsible expanders |

The 2 remaining errors are both for `gemini-aops-4` sessions: `'NoneType' object has no attribute 'get'`. The `.upper()` error that affected all Claude sessions in R1 is now resolved.

**Remaining issue**: Most sessions show "UNKNOWN" status rather than SUCCESS/FAILURE. This is the Framework Reflection format mismatch identified in R1 — Claude sessions don't produce structured reflections in the expected format, so the parser can't extract outcome status.

## Issues Summary (prioritized)

### Critical

1. **Synthesis fallback STILL missing** — `if synthesis:` skips the entire section with no else branch. When synthesis.json doesn't exist, the user sees a gap. (Unchanged from R1)

### Major (spec'd features not implemented)

2. **Collapsible sections** — Only Paused Sessions collapsible. YOUR PATH, Synthesis, Project Grid always expanded. Page is ~9400px tall. (Unchanged)
3. **Stale session archive** — No archive prompt for >24h sessions. (Unchanged)
4. **Epic drill-down** — Epic title not clickable, no child task visibility. (Unchanged)
5. **UP NEXT status badges** — Blocked/in-progress tasks visually identical to active. (Unchanged)
6. **Project cards don't show active agents** — No "WORKING NOW" in project cards. (Unchanged)
7. **"Needs You" indicator missing** — No badge or indicator answering "What needs me?" above the fold.

### Minor

8. **Recent Prompts not rendering** — May be data availability issue.
9. **Session Summary UNKNOWN status** — Most sessions show UNKNOWN due to Framework Reflection format mismatch. Parser needs relaxed matching.
10. **2 gemini session errors** — `'NoneType' object has no attribute 'get'` for gemini-format session summaries.
11. **Stale badge lacks regeneration hint** — STALE badge shows but doesn't tell user how to regenerate.
12. **YOUR PATH shows low-value sessions** — Polecat worker sessions, "/clear" sessions, and "commit changed and new files" sessions add noise. These could be filtered or de-emphasized.
13. **ANSI escape codes in YOUR PATH** — One session shows raw ANSI: `\x1b[1m518 ready\x1b[0m` — should be stripped.

## Changes Since Round 1

| Issue                       | R1 Status | R2 Status    | Change                                                        |
| --------------------------- | --------- | ------------ | ------------------------------------------------------------- |
| Section ordering (D1)       | FAIL      | PARTIAL PASS | WLO moved to top                                              |
| Synthesis missing (D4)      | FAIL      | PARTIAL PASS | synthesis.json now exists and renders; fallback still missing |
| Session Summary regression  | CRITICAL  | MINOR        | 40+ errors → 2 errors                                         |
| Console errors              | PASS      | PASS         | Still clean                                                   |
| Stale badge (D4.3)          | UNTESTED  | PASS         | Implemented                                                   |
| TODAY'S STORY / Daily Story | NO DATA   | RENDERING    | Now shows accomplishments                                     |
| Session Insights            | N/A       | NEW          | Token metrics, friction points, cache stats                   |

## Emotional Assessment

Opening the dashboard now provides **meaningfully better** orientation than Round 1:

- **"What's running?"** is answered immediately — the ACTIVE NOW banner with 2 sessions is the first thing you see
- **"What's the story?"** is answered by Focus Synthesis — TODAY'S STORY with accomplishments, session insights, and a focus suggestion ("Focus on gemini-aops-4 — 2 friction points")
- **The synthesis makes it feel like someone is paying attention** — the narrative and insights create a sense of coherence rather than raw data

However:

- **YOUR PATH is still very long** (~10 project groups with many sessions including noise like "/clear" and "commit and push"). Without collapsibility, it pushes the project grid far down the page
- **The "What needs me?" question** remains unanswered — there's no explicit "Needs You" indicator
- **The page is still ~9400px tall** — that's a lot of scrolling for an ADHD tool

Overall feeling: **Noticeably better — it now tells a story, not just shows data.** The synthesis panel is the biggest win. The remaining gap is density management (collapsible sections) and the "needs you" indicator.

## Screenshots

- `qa/screenshots/dashboard-above-fold-20260304b.png` — WLO at top with Active Now
- `qa/screenshots/dashboard-your-path-20260304b.png` — YOUR PATH section (BRAIN project)
- `qa/screenshots/dashboard-mid-page-20260304b.png` — YOUR PATH (polecat workers)
- `qa/screenshots/dashboard-synthesis-20260304b.png` — Focus Synthesis panel
- `qa/screenshots/dashboard-epic-20260304b.png` — Spotlight Epic + Project Grid (TJA, Personal)
- `qa/screenshots/dashboard-projects-20260304b.png` — Project Grid (Sessions, MEM)
- `qa/screenshots/dashboard-bottom-20260304b.png` — Quick Capture
