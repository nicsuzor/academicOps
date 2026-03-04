---
title: "QA Results: Overwhelm Dashboard (2026-03-04)"
type: qa-result
status: complete
tags: [qa, dashboard, overwhelm-dashboard]
created: 2026-03-04
spec: specs/overwhelm-dashboard.md
qa-plan: qa/dashboard-qa.md
verdict: ISSUES
---

# QA Results: Overwhelm Dashboard

**Date**: 2026-03-04
**Environment**: dev3, aOps v0.2.40-24-g1ac2d9c0, Streamlit on localhost:8501
**ACA_DATA**: /opt/nic/brain
**synthesis.json**: MISSING (no dashboard/ directory exists)
**Verdict**: **ISSUES** — dashboard renders and provides value, but multiple spec'd features are unimplemented or silently failing

## Executive Summary

The dashboard loads without crashes and provides useful project-level context recovery through the YOUR PATH section and project grid. However, several critical ADHD accommodation features from the spec are not implemented: sections are not collapsible, synthesis fails silently when missing, above-the-fold content doesn't answer the three critical questions, and the session summary view is broken by a regression. The dashboard is functional but does not yet meet its spec.

## Sections Rendered (5 of 10)

| #  | Section            | Rendered            | Notes                                                                                 |
| -- | ------------------ | ------------------- | ------------------------------------------------------------------------------------- |
| 1  | Spotlight Epic     | YES                 | "Framework Core" at 46%, Done: 16, In Progress: 18, Blocked: 1                        |
| 2  | Task Graph         | YES (separate view) | Moved to sidebar view mode — 640 nodes, 1154 links                                    |
| 3  | Current Activity   | NO                  | `render_agents_working()` called but no output (likely no active agents in last hour) |
| 4  | Focus Synthesis    | NO                  | synthesis.json missing; section silently disappears                                   |
| 5  | Daily Story        | NO                  | `extract_daily_story()` returns nothing (no data)                                     |
| 6  | Where You Left Off | YES                 | 3 paused sessions shown (collapsed). No active sessions.                              |
| 7  | Your Path          | YES                 | Dropped threads grouped by 10 projects. Very long section.                            |
| 8  | Recent Prompts     | NO                  | Not visible in page — may have no data to render                                      |
| 9  | Project Grid       | YES                 | 20+ project cards with EPICS and UP NEXT                                              |
| 10 | Quick Capture      | YES                 | Text area + tags + Capture button                                                     |

## Per-Task QA Results

### QA-D1: Section Reordering — FAIL

| #    | Check                      | Result  | Evidence                                                                                         |
| ---- | -------------------------- | ------- | ------------------------------------------------------------------------------------------------ |
| D1.1 | Above-the-fold content     | FAIL    | Only Spotlight Epic visible (counts). No sessions, no synthesis, no dropped threads.             |
| D1.2 | "What's running?" answered | FAIL    | No agent count or active session visible without scrolling.                                      |
| D1.3 | "What's dropped?" answered | FAIL    | YOUR PATH requires scrolling past WLO section.                                                   |
| D1.4 | "What needs me?" answered  | FAIL    | No "Needs You" badges visible above fold.                                                        |
| D1.5 | Graph still accessible     | PASS    | Available as "Task Graph" sidebar view.                                                          |
| D1.6 | No section lost            | PARTIAL | Focus Synthesis, Daily Story, Current Activity, Recent Prompts not rendered (data dependencies). |

**Assessment**: The above-the-fold content shows Spotlight Epic counts (Done/In Progress/Blocked) which answers "what's the epic status?" but NOT the three critical questions: "What's running?", "What's dropped?", "What needs me?" The spec explicitly requires these above the fold.

### QA-D2: Stale Session Archive — NOT IMPLEMENTED

| #         | Check      | Result | Evidence                                                                    |
| --------- | ---------- | ------ | --------------------------------------------------------------------------- |
| D2.1–D2.7 | All checks | N/A    | No archive prompt exists. Stale sessions (>24h) are simply hidden entirely. |

### QA-D3: Session Filter Fix — PARTIAL PASS

| #         | Check                         | Result   | Evidence                                          |
| --------- | ----------------------------- | -------- | ------------------------------------------------- |
| D3.5      | No "unknown" sessions visible | PASS     | No "unknown: No specific task" sessions displayed |
| D3.1–D3.4 | Other checks                  | UNTESTED | Requires creating specific test sessions          |

### QA-D4: Synthesis Fallback — FAIL

| #    | Check                   | Result   | Evidence                                                                                |
| ---- | ----------------------- | -------- | --------------------------------------------------------------------------------------- |
| D4.1 | Missing synthesis.json  | FAIL     | synthesis.json does not exist. No fallback message shown — section silently disappears. |
| D4.2 | Message explains fix    | FAIL     | No message at all.                                                                      |
| D4.3 | Stale synthesis flagged | UNTESTED | No synthesis to test staleness against.                                                 |
| D4.6 | Page layout stable      | FAIL     | Layout gap where synthesis should be — jumps from Spotlight Epic to WLO.                |

**Assessment**: This is the most critical UX failure. When synthesis.json is missing, the code path `if synthesis:` simply skips the entire panel with no feedback. The spec requires an informative fallback message with regeneration instructions.

### QA-D5: Path Error Handling — PASS (functional)

| #         | Check          | Result                   | Evidence                                                 |
| --------- | -------------- | ------------------------ | -------------------------------------------------------- |
| D5.1–D5.5 | Error handling | NOT TESTED (destructive) | Path reconstruction is working correctly with live data. |

YOUR PATH section renders successfully with dropped threads grouped by 10 projects. The section is functional. Data source is the git-synced sessions repo (`/opt/nic/.aops/sessions/summaries/`), which includes sessions from **all machines** — not local-only.

### QA-D6: Project Boxes Show Agents — FAIL

| #    | Check                          | Result | Evidence                                                            |
| ---- | ------------------------------ | ------ | ------------------------------------------------------------------- |
| D6.1 | Active session in project card | FAIL   | No "WORKING NOW" section visible in any project card.               |
| D6.4 | No sessions = no section       | PASS   | No empty "WORKING NOW" placeholders shown.                          |
| D6.5 | Matches WLO data               | FAIL   | WLO shows 3 paused sessions but project cards don't reference them. |

### QA-D7: UP NEXT Status Badges — FAIL

| #    | Check                       | Result | Evidence                                        |
| ---- | --------------------------- | ------ | ----------------------------------------------- |
| D7.1 | Blocked tasks flagged       | FAIL   | No "BLOCKED" indicator on any UP NEXT task.     |
| D7.2 | In-progress tasks indicated | FAIL   | No "IN PROGRESS" indicator on any UP NEXT task. |
| D7.3 | Active tasks look normal    | PASS   | Priority badges (P0, P1, P2) render correctly.  |
| D7.4 | Blocked != active visually  | FAIL   | All tasks look identical regardless of status.  |

### QA-D8: Collapsible Sections — FAIL

| #    | Check                             | Result | Evidence                                                                                |
| ---- | --------------------------------- | ------ | --------------------------------------------------------------------------------------- |
| D8.1 | Sections can be collapsed         | FAIL   | Only Paused Sessions uses an expander. All other sections always expanded.              |
| D8.4 | All critical sections collapsible | FAIL   | Graph (separate view), synthesis (missing), project grid, YOUR PATH — none collapsible. |
| D8.5 | Default state sensible            | FAIL   | YOUR PATH section is very long (~3000px) and cannot be collapsed.                       |

**Assessment**: YOUR PATH is the longest section on the page (10 project groups with timeline threads) and has no collapse/expand mechanism. This directly contradicts the "Collapsible density" ADHD design principle.

### QA-D9: Epic Drill-Down — FAIL

| #    | Check             | Result | Evidence                                            |
| ---- | ----------------- | ------ | --------------------------------------------------- |
| D9.1 | Epic is clickable | FAIL   | Clicked "Epic: Framework Core" title — no response. |
| D9.2 | Children visible  | FAIL   | No way to see individual tasks in the epic.         |

## End-to-End Evaluation

### E2E-D1: Morning Orientation Test — FAIL

| #    | Question                            | Time | Result                                                                     |
| ---- | ----------------------------------- | ---- | -------------------------------------------------------------------------- |
| E1.1 | "How many things are running?"      | >5s  | FAIL — Must scroll past epic to find WLO section.                          |
| E1.2 | "Did anything fail overnight?"      | >10s | PARTIAL — Failed session visible in paused bucket, but requires expanding. |
| E1.3 | "What's unfinished from yesterday?" | ~10s | PARTIAL — YOUR PATH shows dropped threads but requires scrolling.          |
| E1.4 | "What's the overall picture?"       | N/A  | FAIL — No synthesis narrative (synthesis.json missing, no fallback).       |
| E1.5 | "What should I work on first?"      | >20s | FAIL — Must scroll to project grid to find priorities.                     |

### E2E-D6: ADHD Accommodation Check — MIXED

| #    | Principle                   | Result  | Evidence                                                                                                                                                              |
| ---- | --------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E6.1 | Dropped threads first       | FAIL    | Spotlight Epic is first (shows counts, not actionable). Dropped threads in YOUR PATH require scrolling.                                                               |
| E6.2 | Scannable, not studyable    | PARTIAL | Priority badges are good. YOUR PATH timeline is scannable. But project cards lack status differentiation.                                                             |
| E6.3 | Reactive design             | PASS    | Dashboard reconstructs from existing data. No setup step required.                                                                                                    |
| E6.4 | Directive framing           | PARTIAL | "WHERE YOU LEFT OFF", "YOUR PATH", "UP NEXT" are directive. But "Spotlight Epic" is generic.                                                                          |
| E6.5 | Collapsible density         | FAIL    | Only 1 of 5 visible sections is collapsible. YOUR PATH is very long and always expanded.                                                                              |
| E6.6 | No flat displays at scale   | PARTIAL | Projects grouped in cards (good). YOUR PATH groups by project (good). But 10 project groups in YOUR PATH create a long scroll.                                        |
| E6.7 | Dashboard reduces overwhelm | MIXED   | Provides useful context recovery, but the long page and missing synthesis create cognitive load. Opening it doesn't immediately calm — requires work to find answers. |

### E2E-D7: Regression Check — ISSUES

| #    | Check              | Result | Evidence                                                                     |
| ---- | ------------------ | ------ | ---------------------------------------------------------------------------- |
| E7.1 | Sidebar navigation | PASS   | All 4 views load.                                                            |
| E7.2 | Time range filters | PASS   | Sidebar filters present and functional.                                      |
| E7.3 | Task graph         | PASS   | SVG renders with 640 nodes, 1154 links.                                      |
| E7.4 | Quick capture      | PASS   | Present with text area, tags, Capture button.                                |
| E7.5 | Recent Prompts     | FAIL   | Section not visible on page.                                                 |
| E7.6 | Task Manager       | PASS   | Loads with 49 tasks, column controls, CSV download, search, Create New Task. |
| E7.7 | No console errors  | PASS   | 0 errors in browser console.                                                 |

### CRITICAL REGRESSION: Session Summary View

The Session Summary view shows **40+ error alerts**. Nearly every session summary file fails with:

- `'NoneType' object has no attribute 'upper'` (most files)
- `'NoneType' object has no attribute 'get'` (gemini session files)

Only 1 of 42 session summaries renders successfully (the FAILURE-status aops session from yesterday). This view is **effectively broken**.

## Issues Summary

### Critical (blocks ADHD accommodation goals)

1. **Synthesis fallback missing** — When synthesis.json doesn't exist, the entire Focus Synthesis section silently disappears. No fallback message, no regeneration hint. The user sees a gap with no explanation.

2. **Session Summary view regression** — 40+ error alerts when loading session summaries. `'NoneType' object has no attribute 'upper'` suggests a schema change in session summary JSON that the reader doesn't handle.

3. **Section ordering still wrong for ADHD** — Above-the-fold shows Spotlight Epic (counts) instead of the three critical questions: "What's running?", "What's dropped?", "What needs me?"

### Major (spec'd features not implemented)

4. **Collapsible sections not implemented** — Only Paused Sessions uses an expander. YOUR PATH, Project Grid, and other sections are always expanded, making the page very long.

5. **Stale session archive not implemented** — Sessions >24h are silently hidden instead of showing an archive prompt.

6. **Epic drill-down not implemented** — Spotlight Epic title is not clickable; no way to see child tasks.

7. **UP NEXT lacks status badges** — Blocked and in-progress tasks look identical to active tasks.

8. **Project cards don't show active agents** — "WORKING NOW" section not rendered in project cards.

### Critical (data pipeline)

12. **Framework Reflection format mismatch** — Claude agents output `**Framework Reflection:**` (bold text) with unstructured bullets, but the parser requires `## Framework Reflection` (heading) with structured `**Field**: value` fields. Result: every Claude session summary has `summary: None, accomplishments: [], outcome: None`. Only Gemini sessions parse correctly. This explains why YOUR PATH is sparse — the enrichment pipeline is effectively a no-op for Claude sessions. Fix: relaxed parser regex to accept bold-text variants + added fallback parser for unstructured reflections + strengthened agent instructions with DO/DON'T examples.

### Minor

9. **Recent Prompts section not rendering** — May be a data availability issue rather than a code bug.

10. **Paused session "View" links use file:// URLs** — Links like `file:///opt/nic/.aops/sessions/transcripts/...` won't work in a browser.

11. **Current Activity section not rendering** — Likely no agents active in last hour, but no "no agents running" fallback message.

## Emotional Assessment

Opening the dashboard provides **some** orientation — the YOUR PATH section successfully shows what was happening across projects, and the project grid gives a useful status overview. However:

- The **missing synthesis** means there's no narrative to orient by — you must construct the story yourself by reading through YOUR PATH
- The **long uncollapsible page** creates scroll fatigue — you know the info is there but have to hunt for it
- The **above-the-fold content** (Spotlight Epic) answers a question you didn't ask ("how's the epic?") instead of the ones you did ("what's running?", "what's dropped?")
- The overall feeling is: **useful but effortful** — it reduces overwhelm somewhat but doesn't yet achieve the "opens and immediately calms you down" target

The dashboard is a **good foundation** that needs the ADHD accommodation features (collapsibility, synthesis fallback, section reordering) to fulfill its design goals.
