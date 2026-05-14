---
title: Morning Timeline — render "what was I trying to do?"
type: skill-instruction
parent: skills/daily
---

# Morning Timeline

A chronological narrative of the work date's sessions so far, anchored on the user's **verbatim prompts**. Renders into `## Today's Log` when the day is still in flight — the user is asking "what was I just trying to do?", not "summarise yesterday".

This is the complement to [[work-summary]], not a replacement:

- **Morning Timeline** (this file) — fires while the day is in flight. Chronological. Verbatim-prompt-anchored. Names the goal and any blocker that ate time. Reader is the user returning to their desk after lunch / a meeting / a context switch.
- **Work Summary** (end-of-day) — fires once the day is mostly done. Editorial. Synthesises threads and patterns. Reader is the user (or future-them) wanting the shape of the day in one read.

Both write into `## Today's Log`. Only one runs per `/daily` invocation. Pick by mode (see §When to render).

## Why this exists

The user prompt is the most information-dense signal in a transcript. It states the goal in their own words, before any agent paraphrase or framing. A timeline that surfaces those verbatim — with one-line outcomes — answers "what was I trying to do this morning?" in seconds. Without it, the user has to grep their own transcripts.

The failure mode this avoids: omitting `## Today's Log` entirely on morning runs (the existing empty-morning rule), which loses the most useful artefact a returning-to-desk user wants — a re-orientation on their own intent.

## When to render

Render Morning Timeline when **all** of the following hold:

1. The work date has at least one interactive session (i.e. `$AOPS_SESSIONS/transcripts/YYYYMMDD-*-abridged.md` exists where YYYYMMDD = today and the session is `client: claude-code` or `client: claude-desktop` — not a worker session).
2. No end-of-day reflection has been written for the work date yet (no `## Framework Reflection` block in the note; no `[[work-summary]]` end-of-day block).
3. The `/daily` invocation is happening during the work day (call time is the same calendar date as the work date).

When any of the above fails:

- No interactive sessions → omit `## Today's Log` entirely (existing empty-morning rule).
- End-of-day reflection has fired → render via [[work-summary]] instead (editorial synthesis).
- `/daily` is being run later about an earlier work date → render via [[work-summary]] for that work-date note.

## Input

Read **abridged** transcripts only (full transcripts are too large):

```
$AOPS_SESSIONS/transcripts/YYYYMMDD-*-abridged.md
```

Filter:

- **Include**: `surface: claude-code-cli` or `surface: claude-code-desktop` with non-empty Turn 1. These are user-initiated.
- **Exclude**: `slug` matches `gha-*`, `polecat-*`, `crew-*`, `enforcer-review`, `worker-*`, `botnicbot-*`, or any session with `assignee: polecat` in the originating task. Worker sessions are visible in the Work Log via PR signals; they don't belong in the user's "what was I doing" timeline.
- **Exclude**: sessions where Turn 1 user content is empty or is just a tool result (these are continuation invocations, not new goals).

For each included transcript, extract:

| Field                                      | Source                                                                                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Start time** (HH:MM, work-date timezone) | `date:` field in frontmatter                                                                                                                           |
| **Host**                                   | `hostname:` (translate `J5HW6L4KT6` → "Mac", `nicwin` → "nicwin/WSL", `dev3.*` → "dev3", etc.)                                                         |
| **Repo / project**                         | `repo:` field                                                                                                                                          |
| **Verbatim Turn 1 prompt**                 | The first user message body, trimmed                                                                                                                   |
| **Skill / agent invoked**                  | First `Invoked: /<skill>` or `Agent(subagent_type=...)` after Turn 1                                                                                   |
| **First material outcome**                 | The first agent text response, OR the first error / pivot signal (look for `❌ ERROR`, `Request interrupted`, `Stop hook error`, hand-off to subagent) |
| **Follow-up user prompts**                 | Subsequent `## User (Turn N)` messages with non-empty body content (skip pure tool results / bash-input)                                               |

## Rendering

Format the section as:

```markdown
## Today's Log

**Morning timeline.** Verbatim prompts in order, one outcome line each.

**HH:MM (host/repo)** — _"verbatim user prompt, trimmed to the first sentence or 1–2 lines."_ → one-sentence factual outcome.

**HH:MM (host/repo)** — _"…"_ → outcome.

…

**What you were trying to do**: 1–2 sentences naming the through-line: the parent task / epic, the underlying goal, and any blocker that ate the morning. No verdict. No "great work" / "this ate your day". Just: "you were chasing X; got blocked by Y; cleared it via Z." If no through-line — multiple unrelated threads — say that.
```

### Line-level rules

1. **Verbatim, not paraphrased.** Use the user's actual words. Italic + quote marks. Trim long prompts to the first sentence or first 1–2 lines — don't summarise away the voice. If a prompt is multiline with a code block, keep the user's first natural-language line; drop the code block (it lives in the transcript).

2. **Pivots get their own line.** When a session changes goal mid-stream (Turn 1 says X, Turn 3 says "stop, do Y instead"), render both. The pivot is the signal — that's the moment the user redirected.

3. **Compress retries.** If two adjacent sessions are the same `/skill` re-invocation after a tool denial / interrupt with no new content, render once: `**HH:MM (host/repo)** — _"prompt"_ → first attempt denied; retry at HH:MM succeeded → outcome.`

4. **Worker-spawned sessions don't appear.** They're already represented by merged-PR rows in `## Work Log`. Listing them in the timeline doubles the noise without adding signal.

5. **Name the blocker if there is one.** When the timeline shows an error → diagnostic detour → fix → resumption, the closing synthesis MUST name the blocker by ID or one-line cause. The point of the section is "what ate the morning" — not naming the eater is a failure.

6. **No editorial weight.** Don't say "wisely pivoted" or "wasted time on". Describe what happened. The user can decide whether the diversion was worth it.

7. **Wikilink people, projects, tasks.** `[[Cam Wilson]]`, `[[aops-2b248ee4]]`, `[[LLB242]]` — the timeline is part of the PKB graph, not a flat log.

8. **Hostname translation** (apply consistently):
   - `J5HW6L4KT6` → `Mac`
   - `nicwin` → `nicwin/WSL`
   - `dev3.stoat-musical.ts.net` → `dev3`
   - `services-new.*` → `services-new`
   - GitHub-hosted runners → `gha`

### Worked example

The day's interactive sessions (filtered):

- 10:57 Mac brain — `/remember` re Cam Wilson contact; skill asked "want me to add to MOC?"; user fired `/learn` 18min later: "should never ask"
- 11:50 nicwin brain — `/supervisor aops-5430c4c1 — dispatch with local gemini polecats`; tool use denied
- 11:51 nicwin brain — same prompt, retry; supervisor found undecomposed, called pauli for preflight
- 12:14 nicwin brain — `/pull aops-2b248ee4 and dispatch locally using gemini polecats`; failed at config layer with `unknown gates keys: ['commit']`
- 12:15 nicwin academicOps — `explain to me what this polecat bug is and what choice i have`; traced to PR #988 removed `commit` gate but stale `polecat.yaml` files still had it
- 12:20 nicwin academicOps — `we caught ourselves in a bug…confirm it's fixed in current commit so i can cut a new release bugfix`; confirmed `daf82d78` on main; `make prerelease`
- 12:25 nicwin brain — `/pull aops-2b248ee4…i think the polecat config bug has been fixed`; retried dispatch
- 12:28 nicwin brain — `/pull aops-76525b02 and help me get back on track`; blocker `aops-53b83faf` now done; previous in_progress still hanging

Rendered:

```markdown
## Today's Log

**Morning timeline.** Verbatim prompts in order, one outcome line each.

**10:57 (Mac/brain)** — _"/remember had a good conversation with [[Cam Wilson]], who's just moved to ABC as national AI reporter (from Crikey)…"_ → filed `cont-e195f86b`; `/remember` asked whether to also add him to the journalists MOC, you fired `/learn` 18min later: _"the /remember skill should never ask whether to improve the pkb! always do it!"_

**11:50–11:51 (nicwin/WSL, brain)** — _"/supervisor aops-5430c4c1 — dispatch with local gemini polecats"_ → first attempt denied at the `get_task` call; retry ran, supervisor found the epic undecomposed and called pauli for preflight rather than dispatching.

**12:14 (nicwin/WSL, brain)** — _"/pull aops-2b248ee4 and dispatch locally using gemini polecats"_ → dispatch failed at the config layer: `ValueError: unknown gates keys: ['commit']`. Blocked all polecat dispatch on this host.

**12:15 (nicwin/WSL, academicOps)** — _"explain to me what this polecat bug is and what choice i have"_ → traced: yesterday's #988 (`Remove commit gate from gate definitions`) removed `commit` from the allowed-keys set in `polecat_config.py`, but stale `polecat.yaml` files (sessions repo + `~/.aops/local.yaml`) still had `commit: warn`. Config migration miss, not a code bug.

**12:20 (nicwin/WSL, academicOps)** — _"we caught ourselves in a bug: we deleted the 'commit' gate but not the test in router.py. confirm it's fixed in current commit so i can cut a new release bugfix"_ → confirmed `daf82d78` on main ahead of cached `0.3.23-dev.48`; ran `make prerelease`.

**12:25 (nicwin/WSL, brain)** — _"/pull aops-2b248ee4…i think the polecat config bug has been fixed"_ → retried dispatch under new build.

**12:28 (nicwin/WSL, brain)** — _"/pull aops-76525b02 and help me get back on track"_ → blocker [[aops-53b83faf]] now `done`; task `aops-76525b02` still sitting `in_progress` from the earlier failed attempt.

**What you were trying to do**: dispatch a chain of SEV2 framework tasks under `task-bf380696` ("escalations-only coordinator step-change") to local gemini polecats on WSL. A stale-yaml / code-drift bug from yesterday's PR wave ate ~75 minutes — caught it, cut a prerelease, dispatch path now reopened.
```

## Anti-patterns

- **Paraphrasing the prompt away.** _"/pull a task and dispatch"_ — no. Use the actual words. The verbatim quote is the point.
- **Listing worker sessions.** `gha-enforcer-review`, `polecat-*` sessions don't belong in the user's morning timeline. They're tracked by PR rows.
- **Hand-waving the blocker.** "Got blocked by a config bug" — name the bug. ID, file, what the actual error was. The user came here to remember the specifics.
- **Hidden chronology.** Don't group by project / thread when rendering the timeline. The chronology IS the structure. Save thematic grouping for end-of-day [[work-summary]].
- **Editorial verdicts.** "This was a productive use of time" / "this ate your morning unfairly". Describe; don't judge.
- **Re-running expensive work.** If [[progress-sync]] has already loaded the session list and frontmatter, reuse that data — don't re-parse every transcript top-to-bottom.

## Interaction with other instructions

- **[[progress-sync]]** already enumerates today's session JSONs for Work Log. The Morning Timeline reuses the same enumeration; only the rendering target differs (Today's Log narrative vs Work Log provenance row).
- **[[work-summary]]** is the end-of-day mode. The two are mutually exclusive within a single Today's Log section.
- **[[reflect]]** writes Framework Reflection at end-of-session. Its presence in the note signals "day is closed" and switches Today's Log from Morning Timeline mode to Work Summary mode on the next run.
