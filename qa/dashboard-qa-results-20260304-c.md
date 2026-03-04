---
title: "QA Results: Overwhelm Dashboard (2026-03-04, Round 3 — Experience-Centered)"
type: qa-result
status: complete
tags: [qa, dashboard, overwhelm-dashboard, adhd, ux]
created: 2026-03-04
spec: specs/overwhelm-dashboard.md
qa-plan: qa/dashboard-qa.md
previous: qa/dashboard-qa-results-20260304-b.md
verdict: ISSUES — useful foundation, but the page itself creates overwhelm
---

# QA Results: Overwhelm Dashboard (Round 3)

**Date**: 2026-03-04
**Verdict**: **ISSUES** — the dashboard has useful pieces but the experience of using it is still too effortful for its intended user

---

## 1. The Cold Open

It's 9am. I slept badly. I have ADHD. I've got agents running across multiple machines, half-finished work from yesterday, and I can't remember what I was doing. I open the dashboard.

**First 3 seconds**: Dark background, "WHERE YOU LEFT OFF" header. Green "ACTIVE NOW" badge. Two cards — both say "academicOps, 2h ago." One says "Successfully completed: GitHub Issue created: [link]." The other says "Successfully completed: [Summary]."

My first feeling is **confusion**. "ACTIVE NOW" means something is running, right? But both cards say "Successfully completed." So nothing is actually running. The label says active, the content says done. Which is it? And "Successfully completed: [Summary]" is meaningless — [Summary] is a placeholder, not a summary. I know _less_ than I did before I read it.

Below that: "PAUSED SESSIONS (3 sessions, 4-24h ago)" — collapsed. Okay, I can expand that later. Fine.

**5-10 seconds**: I see "YOUR PATH" heading at the bottom of the viewport. The word BRAIN in orange. I scroll down.

**10-60 seconds — YOUR PATH**: This is where things go wrong. I start scrolling and I cannot stop scrolling. I see:

- BRAIN: "update my daily note please" — okay. "/q mem: pkb mcp server should error out..." — technical, specific, I remember that. Then "/clear". Then another "/clear". Then another "/clear". Then "@aops-core:effectual-planner review my task tree..." — okay. Then another "/clear". Then "Working..." with raw ANSI escape codes: `\x1b[1m518 ready\x1b[0m`. That's a rendering bug but it's also just... what is this? Why am I looking at this?

- MEM: "the 'aops graph -f all' command seems to be producing..." — real work. "/aops-core:pull aops-fcf2a7c7" — opaque. "review https://github.com/nicsuzor/mem/pull/49..." — real work. "check why the ci/cd release action isn't working" — real work. "/aops-core:pull aops-e2e59eff" — opaque.

- AOPS: Some real work mixed with housekeeping. Fine.

- DOTFILES: "commit changed and new files, pull, fix conflicts, push" — three times. This is pure noise. It tells me nothing about what happened, only that git sync ran.

- BUTTERMILK: Same thing. "commit changed and new files, pull, fix conflicts, push." One entry. Why is this a section?

- ACADEMICOPS: This is where I start feeling overwhelmed. I count **sixteen entries**. Seven of them are "commit changed and new files, pull, fix conflicts, push." Three are "Implement the following plan:" with truncated text. There's a "Successfully completed: [Summary]" — again, a placeholder. There's a "/clear" followed by "run the evaluation QA workflow for the overwhelm dash again" — that's meta, this is me evaluating the thing I'm looking at. More "commit" entries.

  At this point I feel like I'm reading a git log, not a dashboard. The ratio of signal to noise is maybe 1:4.

- GEMINI-AOPS-4: One real session about enforcing `parent` argument in `mcp__pkb__create_task` calls. The prompts shown are system messages ("Waiting for MCP servers to initialize...") — not human-meaningful.

- SESSIONS: "commit changed and new files, pull, fix conflicts, push." One entry. Another noise section.

- E2E59EFF: ". You are a polecat worker. Your task has already been claimed and your worktree is ready." This is a raw system prompt being displayed as if it were something I asked for. It's meaningless to me.

- 83DE7106: Same thing. Another polecat worker system prompt.

**My feeling after YOUR PATH**: Tired. I just scrolled through approximately 3500px of session timelines and most of it was noise — "/clear" commands, "commit and push" housekeeping, polecat system prompts, and ANSI escape codes. I saw maybe 8-10 genuinely useful entries buried in 40+ items. The section that's supposed to help me reconstruct my path is actually the section that makes me want to close the tab.

**Then — FOCUS SYNTHESIS**: I finally reach it. "14m ago." TODAY'S STORY with 4 accomplishments. DONE (11), ALIGNMENT (4/4 successful), CONTEXT (aops, dotfiles), BLOCKED (3), TOKENS (39 sessions). SESSION INSIGHTS. "Focus on gemini-aops-4 — 2 friction points."

This is genuinely useful. The narrative tells me what happened. The status cards give me a quick read. The focus suggestion points me somewhere specific. **This should be the second thing I see, not the thing I find after 60 seconds of scrolling through noise.**

**Spotlight Epic**: Framework Core at 46%. Fine. Passive but calming — a progress bar is always nice.

**Project Grid**: 20+ cards. Some are great — tja with P0 tasks, personal with safety hazard task, ns with probes. But scattered among them: "f1x", "1", "sessions", "t", "017", "brain", "n", "c", "fcf", "cd4", "epic" — these are empty or near-empty cards that just show a name and a colored bar. They're clutter. Finding a specific project means scanning past many empty cards.

**Quick Capture**: At the bottom. Works. Fine.

**When I reach the bottom, can I articulate what I should do next?** Sort of. The synthesis said "Focus on gemini-aops-4 — 2 friction points." The tja card has two P0 tasks. But these were far apart on the page and I had to hold both in working memory across thousands of pixels of scrolling. For an ADHD user, that's the thing you can't do.

---

## 2. The Three Questions

Without scrolling, within 5 seconds:

### "What's running right now?"

**Findable with effort, but confusing.** I see "ACTIVE NOW" with 2 sessions. But they say "Successfully completed" — so are they running or finished? The answer is technically visible but it contradicts itself. **Feeling: confused, slightly anxious.** I can't trust what this section is telling me.

### "What got dropped?"

**Not there at all.** Nothing above the fold mentions dropped threads. YOUR PATH is one scroll away but it doesn't label dropped threads separately — they're mixed into session timelines with everything else. **Feeling: I'd have to go hunting, which I don't have the energy for at 9am.**

### "What needs me?"

**Not there at all.** No "NEEDS YOU" badge anywhere on the page. The BLOCKED (3) in synthesis mentions a parser regex issue, but that's buried in the synthesis panel below 3500px of YOUR PATH. Nothing above the fold says "hey, something is waiting on you." **Feeling: uneasy. I don't know if I'm ignoring something important.**

---

## 3. Section-by-Section Experience Review

### WHERE YOU LEFT OFF

| Question           | Assessment                                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Earns its space?   | **Yes** — being first is correct. The concept is right.                                                              |
| Scannable?         | **Mostly** — 2 cards, clear layout. But the content is broken: "Successfully completed: [Summary]" tells me nothing. |
| Creates anxiety?   | **Mild confusion.** "ACTIVE NOW" for completed sessions is contradictory.                                            |
| Directive framing? | **Yes** — "WHERE YOU LEFT OFF" is good. "ACTIVE NOW" is good (when accurate).                                        |
| Would Nic use it?  | **Yes, if the content were meaningful.** Right now the card text is placeholder garbage.                             |

**What would make it better**: Show the initial prompt (what I asked), not the completion status. "Review PR #42" is more useful than "Successfully completed: [Summary]". If something is actually completed, say "Done" not "Active Now."

### YOUR PATH

| Question           | Assessment                                                                               |
| ------------------ | ---------------------------------------------------------------------------------------- |
| Earns its space?   | **No, not at this size.** The concept is valuable but the execution is actively harmful. |
| Scannable?         | **No.** 10 project groups, 40+ entries, 80% noise.                                       |
| Creates anxiety?   | **Yes, significantly.** This is the section that makes the page feel overwhelming.       |
| Directive framing? | **Yes** — "YOUR PATH" is good framing.                                                   |
| Would Nic use it?  | **He'd skim 2-3 project headers and give up.**                                           |

**What would make it better**:

- Filter out "/clear", "commit changed and new files", and polecat system prompts entirely — they have zero recovery value
- Collapse by default, show only the 3 most recent meaningful sessions per project
- Strip ANSI escape codes
- If a project only has "commit and push" sessions, don't show it at all

### FOCUS SYNTHESIS

| Question           | Assessment                                                                          |
| ------------------ | ----------------------------------------------------------------------------------- |
| Earns its space?   | **Absolutely — this is the best section on the page.**                              |
| Scannable?         | **Yes.** Narrative bullets, status cards, one-line focus suggestion.                |
| Creates anxiety?   | **Reduces it.** "4/4 sessions successful" is calming. "Focus on X" gives direction. |
| Directive framing? | **Yes** — "FOCUS SYNTHESIS", "TODAY'S STORY", "BLOCKED", "SESSION INSIGHTS".        |
| Would Nic use it?  | **Yes, every time he opens the dashboard.**                                         |

**What would make it better**: Move it to position 2 (right after WHERE YOU LEFT OFF, before YOUR PATH). It answers "what's the overall picture?" which is the second most urgent question after "what's running?". Making the user scroll past YOUR PATH to reach it is cruel.

### SPOTLIGHT EPIC

| Question          | Assessment                                                                             |
| ----------------- | -------------------------------------------------------------------------------------- |
| Earns its space?  | **Marginally.** It's calm and informative but passive — you can't do anything with it. |
| Scannable?        | **Yes** — progress bar, 3 counts. 2 seconds.                                           |
| Creates anxiety?  | **Neutral.** The 46% progress is mildly encouraging.                                   |
| Would Nic use it? | **He'd glance at it. He wouldn't interact with it.**                                   |

### PROJECT GRID

| Question          | Assessment                                                                                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Earns its space?  | **The populated cards do. The empty ones don't.**                                                                          |
| Scannable?        | **In theory.** But 20+ cards with 10+ being empty noise ("f1x", "1", "n", "c") makes it hard to find the ones that matter. |
| Creates anxiety?  | **Mild.** The sheer number of cards suggests "you have a LOT of things going on."                                          |
| Would Nic use it? | **He'd use the 6-8 cards with real content (tja, personal, ns, academicOps, mem, dotfiles).**                              |

**What would make it better**: Hide cards that have no EPICS, no UP NEXT, and no recent activity. If a project is just a name and a colored bar, it doesn't belong on this page.

### QUICK CAPTURE

| Question          | Assessment                       |
| ----------------- | -------------------------------- |
| Earns its space?  | **Yes.**                         |
| Would Nic use it? | **Yes, when a thought strikes.** |

---

## 4. Emotional Assessment

**The dashboard tells a story now — the synthesis panel is a genuine win.** When I read "4/4 sessions successful" and "Focus on gemini-aops-4 — 2 friction points," I feel someone is paying attention to the chaos. That's the feeling this whole dashboard should create.

**But YOUR PATH undoes it.** The journey from "ACTIVE NOW" (top) to "Focus on gemini-aops-4" (synthesis) requires scrolling through ~3500px of session timelines that are mostly "/clear", "commit and push", polecat system prompts, and ANSI escape codes. For an ADHD user, that scroll is where attention dies. The useful information exists but it's buried under noise, and the page has no mechanism (collapsing, filtering, summarizing) to compress that noise.

**The emotional arc of using this dashboard today:**

1. Open → mild orientation ("oh, 2 sessions") → confusion ("active but completed?")
2. Scroll YOUR PATH → growing overwhelm → "why am I looking at git sync commands?"
3. Reach synthesis → relief → "oh, this is good, this is what I needed"
4. Reach project grid → useful but cluttered with empty cards
5. Overall: **the dashboard has the right information but makes you work too hard to get to it**

**The one change that would most improve the experience**: Move FOCUS SYNTHESIS to position 2 (after WLO, before YOUR PATH) and collapse YOUR PATH by default. That way the user sees: what's running → what's the story → and only _chooses_ to drill into the session timelines if they need to.

---

## 5. Technical Checks

Referencing `qa/dashboard-qa.md` check matrix. Only noting changes from Round 2 and user-impact assessment.

| Check                         | Status       | User Impact                                                                     |
| ----------------------------- | ------------ | ------------------------------------------------------------------------------- |
| D1: Section reordering        | PARTIAL PASS | **High** — WLO at top is right, but synthesis buried below YOUR PATH hurts      |
| D2: Stale session archive     | NOT IMPL     | Low — stale sessions are hidden, which is fine for now                          |
| D3: Session filter fix        | PARTIAL      | **Medium** — no "unknown" sessions, but meaningless placeholders still appear   |
| D4: Synthesis fallback        | PARTIAL      | **High when triggered** — section silently disappears if synthesis.json missing |
| D5: Path error handling       | PASS         | Low — working correctly                                                         |
| D6: Project cards show agents | NOT IMPL     | Medium — would be nice but not urgent                                           |
| D7: UP NEXT status badges     | NOT IMPL     | Medium — can't distinguish blocked from active tasks                            |
| D8: Collapsible sections      | NOT IMPL     | **Critical** — the page is 9400px and YOUR PATH can't be collapsed              |
| D9: Epic drill-down           | NOT IMPL     | Low — nice to have                                                              |
| E7.7: Console errors          | PASS         | 0 errors                                                                        |
| Session Summary regression    | MOSTLY FIXED | Low — down to 2 errors from 40+                                                 |

---

## 6. Issues — Prioritized by User Impact

### P1: The page creates overwhelm (the thing it's supposed to prevent)

**YOUR PATH is too long and too noisy.** 10 project groups, 40+ entries, ~3500px. Approximately 80% of the content is noise:

- "/clear" commands (zero recovery value)
- "commit changed and new files, pull, fix conflicts, push" (zero recovery value)
- Polecat worker system prompts (zero recovery value)
- ANSI escape codes (rendering bug)
- Sessions like "Working..." with no meaningful prompt

**User experience change needed**: When I open YOUR PATH, I should see only sessions where I asked something real. Housekeeping, system prompts, and commands should be filtered out. What remains should be collapsible per project, showing only the 2-3 most recent meaningful sessions by default.

### P1: Synthesis is buried below the noise

**FOCUS SYNTHESIS is the most valuable section on the page but it's at position 3, after YOUR PATH.** A user has to scroll through ~3500px of session noise to reach the narrative that actually orients them.

**User experience change needed**: After seeing "what's running" (WLO), the next thing I should see is "what's the story" (Synthesis). YOUR PATH is detail I might want — it should be available but not blocking the narrative.

### P2: "Active Now" shows completed sessions

The WLO section says "ACTIVE NOW" but shows sessions that "Successfully completed" 2h ago. This is confusing. If they completed, they should be in a "Recently Completed" section or show their completion status clearly.

**User experience change needed**: When I see "ACTIVE NOW," I should see things that are actually running. Completed sessions should say they're done.

### P2: Session cards show placeholder text

"Successfully completed: [Summary]" and "Successfully completed: GitHub Issue created: [link]" — the [Summary] and [link] are placeholders from the Framework Reflection format, not useful content. The cards should show what I _asked_ the session to do.

**User experience change needed**: Session cards should show my initial prompt ("run the evaluation QA workflow"), not the agent's self-assessment placeholder.

### P2: Collapsible sections not implemented

The page is 9400px. Only Paused Sessions can be collapsed. Everything else is always expanded.

**User experience change needed**: I should be able to collapse any section I don't need right now, and the page should remember my preference.

### P3: Empty project cards clutter the grid

Cards for "f1x", "1", "n", "c", "017", "fcf", "cd4", "epic" show just a name and colored bar. They add visual noise without information.

**User experience change needed**: If a project has no EPICS, no UP NEXT, and no recent activity, don't show it.

### P3: "What needs me?" has no answer anywhere on the page

The spec says the dashboard should answer "What needs me?" above the fold. Nothing does. The BLOCKED count in synthesis is close but it's buried and describes technical issues, not "this thing is waiting on your input."

### P3: Stale badge on synthesis lacks regeneration hint

When synthesis is >60 min old, the STALE badge appears but doesn't tell you how to refresh it.

### P3: Synthesis fallback when file is missing

If synthesis.json doesn't exist, the section silently disappears with no explanation.

---

## Screenshots

- `qa/screenshots/cold-open-20260304c.png` — What you see when you first open the page
- `qa/screenshots/full-page-20260304c.png` — Full page capture (9400px)
