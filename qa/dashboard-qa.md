---
title: "QA Plan: Overwhelm Dashboard"
type: qa
status: active
tags: [qa, dashboard, overwhelm-dashboard, adhd]
created: 2026-02-23
epic: overwhelm-dashboard-7ff36f81
spec: specs/overwhelm-dashboard.md
---

# QA Plan: Overwhelm Dashboard

## Overview

This QA plan covers the overwhelm dashboard improvements specified in [[specs/overwhelm-dashboard.md]] and tracked under epic [[overwhelm-dashboard-7ff36f81]]. It evaluates both individual task completions and the dashboard's overall effectiveness at serving an ADHD user who needs rapid context recovery.

The task map has its own QA plan at [[qa/task-map-qa.md]]. This plan covers everything else: session display, path reconstruction, synthesis, project boxes, layout, and the overall user experience.

## Prerequisites

- Dashboard running: `cd $AOPS && uv run streamlit run lib/overwhelm/dashboard.py`
- Fresh index: `aops reindex` or equivalent
- At least 2-3 active sessions (<4h) and 2-3 paused sessions (4-24h) for realistic testing
- synthesis.json exists (run `synthesize_dashboard.py` if needed)
- Session summaries exist (run `/session-insights` if needed)
- Browser with devtools available

## Per-Task QA

### QA-D1: Section reordering (overwhelm-dashboard-c818a7e1)

**Precondition**: Page layout reordered.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D1.1 | Above-the-fold content | Open dashboard, do NOT scroll | Can see active sessions (WLO) or synthesis narrative without scrolling |
| D1.2 | "What's running?" answered | Look at top of page | Can count active sessions within 5 seconds |
| D1.3 | "What's dropped?" answered | Look at first screen | Dropped threads or unfinished tasks visible without scrolling |
| D1.4 | "What needs me?" answered | Scan for visual indicators | "Needs You" badges visible without scrolling |
| D1.5 | Graph still accessible | Scroll down | Task graph present and functional, just lower on page |
| D1.6 | No section lost | Scroll through full page | All 10 sections still present and rendering |

### QA-D2: Stale session archive (overwhelm-dashboard-4b066b73)

**Precondition**: Archive prompt implemented. Requires some sessions >24h old.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D2.1 | Archive prompt visible | Load dashboard with stale sessions present | "📦 X stale sessions" message appears |
| D2.2 | Count is accurate | Compare displayed count to actual stale sessions | Count matches |
| D2.3 | "Archive All" works | Click Archive All | All stale sessions removed from view |
| D2.4 | "Review & Select" works | Click Review | Stale sessions expand for individual selection |
| D2.5 | "Dismiss" works | Click Dismiss | Prompt hides for this visit |
| D2.6 | Dismiss reappears on reload | Reload page after dismissing | Prompt reappears |
| D2.7 | Archive is non-destructive | Check archived session files still exist | Session data preserved, just moved/flagged |

### QA-D3: Session filter fix (overwhelm-dashboard-a882c9e9)

**Precondition**: Filter logic updated.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D3.1 | TodoWrite sessions not hidden | Create a session with TodoWrite data but no initial prompt | Session appears (with TodoWrite progress info) |
| D3.2 | Short-prompt sessions shown | Create session with 5-char prompt like "help" | Session appears (not filtered by <10 char rule) |
| D3.3 | Truly empty sessions hidden | Check a session with zero context fields populated | Session is hidden (not shown) |
| D3.4 | Filter count logged | Check logs/console | Number of filtered sessions visible for debugging |
| D3.5 | No "unknown" sessions visible | Scan all visible sessions | No session displays "unknown: No specific task" |

### QA-D4: Synthesis fallback (overwhelm-dashboard-512dde26)

**Precondition**: Fallback message implemented.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D4.1 | Missing synthesis.json | Rename/remove synthesis.json, reload | Informative message shown (not blank gap) |
| D4.2 | Message explains how to fix | Read the fallback message | Contains actionable instruction (e.g., "run /session-insights") |
| D4.3 | Stale synthesis flagged | Make synthesis.json >60 min old | STALE badge visible with age |
| D4.4 | Stale badge is actionable | Inspect the STALE indicator | Contains instruction or link to regenerate |
| D4.5 | Fresh synthesis shows normally | Regenerate synthesis.json, reload | Full synthesis panel renders correctly |
| D4.6 | Page layout stable | Toggle between missing/present synthesis.json | No layout jumps or gaps when section appears/disappears |

### QA-D5: Path error handling (overwhelm-dashboard-f54b87ff)

**Precondition**: Error handling improved.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D5.1 | Missing path_reconstructor | Temporarily break the import, reload | Error message shown, not blank space |
| D5.2 | Error message is useful | Read the error | Explains what's wrong and how to fix (not a stack trace) |
| D5.3 | Other sections unaffected | Check synthesis, WLO, project grid | All other sections render normally |
| D5.4 | No data corruption | Check session summary files | No files modified/corrupted by the error |
| D5.5 | Recovers on reload | Fix the import, reload | Your Path section reappears |

### QA-D6: Project boxes show agents (overwhelm-dashboard-1db82b26)

**Precondition**: Active sessions rendered in project cards.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D6.1 | Active session in project card | Have an active session for project X | Project X's card shows the active session |
| D6.2 | Session shows useful info | Read the session entry in the project card | Shows initial prompt or current task, not just session ID |
| D6.3 | Multiple sessions shown | Have 2+ sessions for one project | Both visible (or count shown) |
| D6.4 | No sessions = no section | Check a project with no active sessions | "WORKING NOW" section hidden (not empty placeholder) |
| D6.5 | Matches WLO data | Compare project card sessions to WLO section | Same sessions shown in both places, consistent info |

### QA-D7: UP NEXT status badges (overwhelm-dashboard-8eab2f92)

**Precondition**: Task status indicators added.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D7.1 | Blocked tasks flagged | Have a blocked P1 task in a project | Task shows "BLOCKED" indicator or visual distinction |
| D7.2 | In-progress tasks indicated | Have an in_progress task | Task shows "IN PROGRESS" or agent indicator |
| D7.3 | Active tasks look normal | Have an active (ready) task | Task shows priority badge without extra status noise |
| D7.4 | Blocked != active visually | Compare blocked and active P1 tasks | Immediately distinguishable without reading text |
| D7.5 | Status is accurate | Check PKB task status vs displayed status | Matches current file state |

### QA-D8: Collapsible sections (overwhelm-dashboard-30d81cc6)

**Precondition**: Section collapse/expand implemented.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D8.1 | Sections can be collapsed | Click collapse toggle on each section | Section collapses with animation or immediate hide |
| D8.2 | State persists on reload | Collapse a section, reload page | Section stays collapsed |
| D8.3 | Collapsed sections show summary | Check collapsed section header | Shows summary info (e.g., "5 projects" or "3 active sessions") |
| D8.4 | All critical sections collapsible | Check: graph, synthesis, project grid, your path | Each has a collapse toggle |
| D8.5 | Default state is sensible | Fresh load (no persisted state) | Most important sections expanded; secondary ones collapsed or available |

### QA-D9: Epic drill-down (overwhelm-dashboard-4acc0cb7)

**Precondition**: Epic interaction implemented.

| # | Check | Method | Pass criteria |
|---|-------|--------|---------------|
| D9.1 | Epic is clickable | Click spotlight epic title | Something happens (expand, navigate, or highlight) |
| D9.2 | Children visible | After clicking | Can see individual tasks in the epic with their status |
| D9.3 | Child status matches PKB | Compare displayed statuses | Accurate reflection of task file state |

## Comprehensive End-to-End Evaluation

Execute after the full epic is complete.

### E2E-D1: The Morning Orientation Test

**Scenario**: Nic opens the dashboard at 9am after sleeping. Multiple agents ran overnight. Some succeeded, some failed, some are still running. Yesterday's work is partially complete.

| # | Question | Time limit | Pass criteria |
|---|----------|-----------|---------------|
| E1.1 | "How many things are running right now?" | 5 sec | Can count active sessions from the first screen |
| E1.2 | "Did anything fail overnight?" | 10 sec | Failed or errored sessions are visually flagged (not hidden) |
| E1.3 | "What did I ask for yesterday that isn't done?" | 10 sec | Dropped threads or paused sessions from yesterday visible |
| E1.4 | "What's the overall picture?" | 15 sec | Synthesis narrative tells today's story in 3-5 bullets |
| E1.5 | "What should I work on first?" | 20 sec | Can identify highest-priority actionable task across projects |

### E2E-D2: The Context Switch Recovery Test

**Scenario**: Nic has been working on Project A for 2 hours. Gets pulled into a meeting. Returns and needs to resume Project A work, but also check on Projects B and C.

| # | Step | Pass criteria |
|---|------|---------------|
| E2.1 | Find Project A's active session | Session card shows what was happening (not agent metadata) |
| E2.2 | Identify where Project A left off | Current task and next step visible |
| E2.3 | Check Project B status | Find Project B card in grid, see its state |
| E2.4 | Check Project C status | Find Project C card, see its state |
| E2.5 | Return focus to Project A | Can re-orient without re-reading all sections |

### E2E-D3: The Rabbit Hole Detection Test

**Scenario**: Nic has been working for 3 hours but got distracted partway through. He's lost track of what he originally intended.

| # | Step | Pass criteria |
|---|------|---------------|
| E3.1 | Find Your Path section | Visible without excessive scrolling |
| E3.2 | Identify dropped threads | Unfinished tasks shown first, grouped by project |
| E3.3 | See the deviation | Timeline shows where he went off-track |
| E3.4 | Decide what to resume | Can pick up a dropped thread or continue current work |

### E2E-D4: The Empty State Test

**Scenario**: Fresh machine, no sessions, no synthesis, minimal tasks. Dashboard should still be useful.

| # | Check | Pass criteria |
|---|-------|---------------|
| E4.1 | Dashboard loads without errors | No crashes, no blank page |
| E4.2 | Missing sections explained | Each missing section shows a helpful message, not blank space |
| E4.3 | Quick capture works | Can create a task even with empty dashboard |
| E4.4 | Task graph shows structure | Graph renders from index.json even without sessions |

### E2E-D5: The Scale Test

**Scenario**: 50+ session summaries, 500+ tasks, 10+ projects, synthesis.json exists.

| # | Check | Pass criteria |
|---|-------|---------------|
| E5.1 | Page loads within 3 seconds | Time from navigation to content rendered |
| E5.2 | No freezing during scroll | Smooth scrolling through all sections |
| E5.3 | Session triage works at scale | 50 sessions properly bucketed (active/paused/stale), not a flat list |
| E5.4 | Project grid manageable | Projects sorted by activity, empty ones hidden; grid isn't overwhelming |
| E5.5 | Auto-refresh doesn't disrupt | 5-minute refresh happens without losing scroll position or selection state |

### E2E-D6: The ADHD Accommodation Check

Evaluate the dashboard against its core design principles.

| # | Principle | Check | Pass criteria |
|---|-----------|-------|---------------|
| E6.1 | Dropped threads first | Visual scan top of page | Unfinished/dropped work is the first actionable content |
| E6.2 | Scannable, not studyable | Look at any section | Information communicated via color, icons, progress bars — not dense paragraphs |
| E6.3 | Reactive design | Open dashboard cold | Everything reconstructed from existing data; no setup step required |
| E6.4 | Directive framing | Read section headers and labels | "YOUR PATH", "NEEDS YOU", "UP NEXT" — not "Session History", "Status: waiting", "Task List" |
| E6.5 | Collapsible density | Check page structure | Important stuff above fold; detail available on demand |
| E6.6 | No flat displays at scale | Check all list-type sections | Everything bucketed, grouped, or summarized; no 500-item flat lists |
| E6.7 | Dashboard reduces overwhelm | Emotional check | Opening the dashboard makes you feel *more* oriented, not *more* stressed |

### E2E-D7: Regression Check

Ensure improvements haven't broken existing functionality.

| # | Check | Pass criteria |
|---|-------|---------------|
| E7.1 | Sidebar navigation works | Dashboard, Manage Tasks, Session Summary, Network Analysis all load |
| E7.2 | Time range filters work | Changing completed time range updates displayed data |
| E7.3 | Task graph still works | SVG + interactive tabs render (see task-map-qa.md for detailed checks) |
| E7.4 | Quick capture creates tasks | Submit a task, verify it appears in PKB |
| E7.5 | Recent prompts section works | Expand, verify prompts display |
| E7.6 | Task manager page works | Navigate to Manage Tasks, verify CRUD operations |
| E7.7 | No console errors | Browser devtools clean |
| E7.8 | Auto-refresh works | Wait 5 minutes or check the timer | Page refreshes without losing state |

### E2E-D8: Cross-Section Consistency

Verify that the same data is displayed consistently across sections.

| # | Check | Pass criteria |
|---|-------|---------------|
| E8.1 | WLO sessions match project cards | Active session in WLO also appears in its project card |
| E8.2 | Dropped threads match path | Unfinished tasks in Your Path match what's in the PKB |
| E8.3 | UP NEXT matches index.json | Priority ordering in project cards matches index.json sort |
| E8.4 | Synthesis matches reality | Narrative bullets reflect what other sections show |
| E8.5 | Spotlight epic matches graph | Epic in spotlight has matching nodes in task graph |
| E8.6 | Completed counts consistent | Completed tasks in project cards match task manager filtered view |

## Reporting

For each QA pass, report:

1. **Task ID** being validated
2. **Check results**: Pass/Fail for each numbered check
3. **Screenshots**: Before/after for layout and visual changes
4. **Regressions**: Any broken existing behavior
5. **New issues**: Anything discovered during QA not covered by existing tasks
6. **Emotional assessment**: Does the dashboard feel *calmer* to use? Does it reduce cognitive load or add to it? This is subjective but critical for an ADHD tool.

File QA results as comments on the relevant task, or as a QA summary in a daily note for end-to-end evaluation.
