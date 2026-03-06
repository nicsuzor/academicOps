# Dashboard QA Assessment - 2026-03-06 (Redo)

**Assessor**: Claude (crew/barbara_5)
**Dashboard**: Cognitive Load Dashboard on port 8501
**Verdict**: ISSUES FOUND — text readability failures across multiple sections

---

## 1. Cold Open Narration

I'm Nic at 9am, overwhelmed, can't remember yesterday. I open the dashboard.

**First impression**: "WHERE YOU LEFT OFF" is the first section. Good — it tries to answer "what was I doing?" But the items say:

- "Fix problem where" — where _what_? Sentence cut off mid-phrase.
- "Add pytest uses" — cryptic slug. Uses of what?
- "Aops core butler" — system internal name, not a human description
- "Https github com" — a URL fragment as a title
- "Run assessment overwhelm" — verb-noun slug, barely parseable
- "Fix aops pytest" — another slug

**Feeling**: Confused. These aren't descriptions of what I was doing — they're auto-generated slugs from session data. I can see they're all "aops" project and recent (19m to 3h), but I can't reconstruct what I was working on from these titles. The PAUSED SESSIONS expander (10 sessions) is fine — collapsed by default, doesn't add clutter.

**Scrolling to FOCUS SYNTHESIS**: "58m ago" — good timestamp. TODAY'S STORY bullets are better than before (no `[project]` prefixes), but still slug-like: "Record buttermilk generation", "Https github com". DONE (3) lists "Https github com; Run assessment overwhelm; Fix aops pytest" — these are the same slugs.

**CONTEXT**: "explorations, sessions" — fine, minimal.

**SESSION INSIGHTS**: "10 SESSIONS, 45K TOKENS, 100% CACHE" with "In/Out: 598/44K" and "Cache Read: 5.6M" — useful for a power user, compact.

**YOUR PATH**: AOPS section shows full session prompts — useful but very long. The actual user prompts are visible ("omg, anthropic finally fixed the bug...") which is genuinely helpful for context recovery. EXPLORATIONS section shows buttermilk run notes. This section earns its space but is verbose.

**Epic: Framework Core**: 46% progress bar with 16 done / 18 in progress / 1 blocked — clean and useful. But it's the ONLY epic shown at top level.

**Project cards**: TJA, PERSONAL, ACADEMICOPS, EXPLORATIONS, MEM, DOTFILES, ACADEMIC, OMCP, WRITING, MEDIAMARKETS, AOPS-CORE, FRAMEWORK, ACADEMICOPS (duplicate?), OSB-BENCHMARKING, NETWORK-PLANNING. All real projects — no bogus cards! The earlier fix worked. Each card shows epics (with progress) and UP NEXT tasks with priority badges. Good.

**QUICK CAPTURE**: Clean, functional, at the bottom. Fine placement.

**Overall feeling after scrolling**: The project cards section is the most useful part. YOUR PATH is genuinely helpful for reconstruction. But the WHERE YOU LEFT OFF section — the very first thing I see — gives me gibberish instead of clarity. It's the worst possible first impression.

**Time to feel oriented**: ~30 seconds scanning project cards. But the first 10 seconds (WHERE YOU LEFT OFF) actively confused me.

---

## 2. Text Readability Scan

### WHERE YOU LEFT OFF (FAIL)

| Item                       | Verdict | Issue                  |
| -------------------------- | ------- | ---------------------- |
| "Fix problem where"        | FAIL    | Truncated mid-sentence |
| "Add pytest uses"          | FAIL    | Slug — "uses" of what? |
| "Aops core butler"         | FAIL    | System internal name   |
| "Https github com"         | FAIL    | URL fragment as title  |
| "Run assessment overwhelm" | FAIL    | Verb-noun slug         |
| "Fix aops pytest"          | FAIL    | Slug — no context      |

**6/6 items fail.** This section provides zero useful information. Every item is an auto-generated slug derived from session data, not a human-readable description.

### FOCUS SYNTHESIS — TODAY'S STORY (WARN)

| Item                           | Verdict | Issue                                 |
| ------------------------------ | ------- | ------------------------------------- |
| "Record buttermilk generation" | WARN    | Technically readable but jargon-heavy |
| "Commit changed files"         | WARN    | Generic — which files?                |
| "Https github com"             | FAIL    | URL fragment                          |
| "Run assessment overwhelm"     | FAIL    | Slug                                  |
| "Fix aops pytest"              | FAIL    | Slug                                  |

**3/5 fail, 2/5 warn.** Same underlying data as WHERE YOU LEFT OFF.

### FOCUS SYNTHESIS — DONE (3) (FAIL)

| Item                                                          | Verdict | Issue               |
| ------------------------------------------------------------- | ------- | ------------------- |
| "Https github com; Run assessment overwhelm; Fix aops pytest" | FAIL    | All three are slugs |

### FOCUS SYNTHESIS — CONTEXT (PASS)

"explorations, sessions" — meaningful project names.

### SESSION INSIGHTS (PASS)

"10 SESSIONS, 45K TOKENS, 100% CACHE" — clear, compact, useful for power user.

### YOUR PATH — Session Titles (WARN)

| Item                                                    | Verdict | Issue                              |
| ------------------------------------------------------- | ------- | ---------------------------------- |
| "omg, anthropic finally fixed the bug..."               | PASS    | Real user prompt, genuinely useful |
| "we've been trying to tune graphs..."                   | PASS    | Real user prompt                   |
| "show me the test cases for the session stop..."        | PASS    | Real user prompt                   |
| "record that the buttermilk generation run finished..." | PASS    | Real user prompt                   |

Session titles in YOUR PATH are the actual user prompts — these are good! But the sub-items show "Requested: ..." and "Created: something" repeatedly. "Created: something" is a placeholder.

### YOUR PATH — Sub-items (WARN)

| Item                                       | Verdict | Issue                                    |
| ------------------------------------------ | ------- | ---------------------------------------- |
| "Created: something" (repeated 8x)         | FAIL    | Placeholder text, not a real description |
| "Requested: [Request interrupted by user]" | PASS    | Accurate status                          |
| "Requested: /model"                        | PASS    | Actual command                           |

### Epic: Framework Core (PASS)

Clear title, percentage, done/in-progress/blocked counts. No issues.

### Project Cards (PASS)

All project names are real. Task titles within cards are human-readable: "Bolt in unfinished shelf (safety hazard)", "Review HSSC manuscript (Dr Pellegrini)", "Get aops-core plugin working in Claude Cowork". Priority badges (P0/P1/P2) are clear.

### Task Graph (PASS)

Title, node count, link count shown clearly. "Start:" caption names top spotlight nodes. Legend has 22 items across 5 sections — comprehensive.

### Quick Capture (PASS)

Clean, functional, clear placeholder text.

---

## 3. Three Questions Test

1. **"What's running right now?"** — FINDABLE. WHERE YOU LEFT OFF shows 6 active sessions with "ACTIVE NOW" label and timestamps. But the titles are gibberish, so I know _something_ is running but not _what_.
2. **"What got dropped?"** — FINDABLE WITH EFFORT. PAUSED SESSIONS (10, 4-24h ago) is collapsed. I'd have to expand it, and the titles would likely be equally cryptic.
3. **"What needs me?"** — NOT VISIBLE. No "NEEDS YOU" or "blocked on human" section exists. I'd have to scan project cards for blocked items.

---

## 4. Section Experience Review

| Section              | Earns its space?                                  | Scannable?                        | Anxiety?               | Directive?   |
| -------------------- | ------------------------------------------------- | --------------------------------- | ---------------------- | ------------ |
| WHERE YOU LEFT OFF   | No — gibberish titles                             | No — can't parse items in 3s      | Neutral                | Good framing |
| FOCUS SYNTHESIS      | Partially — DONE count useful, narrative is slugs | Mixed                             | Low                    | Good         |
| SESSION INSIGHTS     | Yes — compact power-user stats                    | Yes                               | None                   | Neutral      |
| YOUR PATH            | Yes — real prompts aid reconstruction             | No — too verbose, needs scrolling | Moderate — long        | Good framing |
| Epic: Framework Core | Yes — clear progress                              | Yes                               | Reduces anxiety        | Neutral      |
| Project Cards        | Yes — best section                                | Yes                               | Low — manageable count | Good         |
| Quick Capture        | Yes                                               | Yes                               | None                   | Good         |

---

## 5. Issues — Prioritized by User Impact

### P0: WHERE YOU LEFT OFF shows gibberish session titles

**Impact**: The first thing a returning user sees is incomprehensible. Every single item fails the readability test. This is the highest-impact issue because it's the first impression.

**Root cause**: Session titles are auto-generated from session data (likely first few words of the prompt or a filename slug). The dashboard displays whatever the synthesis pipeline provides without checking quality.

**Fix needed**: The session title generation pipeline needs to produce human-readable summaries. Options:

1. Use the first user prompt as the session title (YOUR PATH already does this — reuse that data)
2. If a session has a claimed task, use the task title
3. Fall back to "Session at {time}" rather than displaying a slug

### P1: DONE/TODAY'S STORY items are the same gibberish slugs

**Impact**: The synthesis narrative sections repeat the same unreadable session slugs. "Https github com" appears in both TODAY'S STORY and DONE.

**Root cause**: Same as P0 — these derive from the same session title data.

**Fix needed**: Same pipeline fix as P0 would resolve this. Additionally, DONE items should reference task titles (what was accomplished) rather than session titles (how the session was named).

### P1: YOUR PATH shows "Created: something" placeholder (8x)

**Impact**: Moderate — the section is useful overall but "Created: something" repeated 8 times is obviously placeholder data that was never replaced with real content.

**Root cause**: The session event logging records "Created: something" as a placeholder when the actual creation target isn't captured.

**Fix needed**: Either capture the real creation target (task ID, file path) or suppress "Created: something" entries entirely.

### P2: Only one epic shown at top level

**Impact**: Low-moderate. Framework Core at 46% is useful, but other epics (PKB search quality, Dotfiles & Dev Environment, etc.) are buried inside project cards.

**Root cause**: The spotlight epic is likely hardcoded or selected by a simple heuristic.

**Fix needed**: Show top 3 epics by activity/priority, or the epic with the most blocked items.

### P2: No "Needs You" indicator

**Impact**: Low — blocked items exist in project cards but aren't surfaced at top level.

**Fix needed**: Add a "NEEDS YOU" section showing items with status=blocked or status=waiting that are assigned to the user.

---

## 6. Verdict

**ISSUES FOUND** — 2 P0/P1 issues, both rooted in session title quality. The project cards, epic progress, and task graph sections are all working well after the earlier fixes. The critical gap is that session-derived text (WHERE YOU LEFT OFF, TODAY'S STORY, DONE) displays auto-generated slugs instead of human-readable descriptions.
