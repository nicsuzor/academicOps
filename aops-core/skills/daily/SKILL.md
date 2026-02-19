---
name: daily
category: instruction
description: Daily note lifecycle - briefing, task recommendations, progress sync, and work summary. SSoT for daily note structure.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move
version: 2.0.0
permalink: skills-daily
---

# Daily Note Skill

Manage daily note lifecycle: briefing, task recommendations, progress sync, and work summary.

Location: `$ACA_DATA/daily/YYYYMMDD-daily.md`

## CRITICAL BOUNDARY: Planning Only

**This skill is for PLANNING, not EXECUTION.**

- `/daily` captures priorities in the daily note
- `/daily` does NOT execute tasks, even if user states priorities
- When user answers "what sounds right for today?" → record in Focus section, then COMPLETE
- After daily note is updated: output "Daily planning complete. Use `/pull` to start work." and HALT

**User stating a priority ≠ authorization to execute that priority.**

## Invocation

Every `/daily` invocation runs the **full pipeline** and updates the daily note in place. There are no separate modes — the skill is designed to be run repeatedly throughout the day.

```
/daily          # Run full pipeline (create note if missing, then update everything)
/daily sync     # Alias — same behavior, kept for muscle memory
```

**Pipeline**: 1 (create if missing) → 1.5 (mobile capture triage) → 2 (email briefing) → 3 (focus & recommendations) → 4 (progress sync & merged PRs) → 5 (work summary)

**Idempotent updates**: Each section is updated in place using the Edit tool. User-written content is **never deleted**:

- **Purely machine sections** (Task Tree, Session Log, Session Timeline, Merged PRs): fully replaced on each run
- **Mixed sections** (Focus, FYI, Project Accomplishments): machine content is regenerated above a `<!-- user notes -->` marker; anything the user writes below that marker is preserved
- **User sections** (any section/text the user adds that isn't in the template): left untouched entirely

**Incremental data handling**: Email triage skips already-processed emails (cross-ref against FYI section + sent mail). Session sync skips already-processed session JSONs (cross-ref against Session Log table). Merged PR listing always refreshes from GitHub API.

## Section Ownership

| Section                 | Owner    | Updated By                               |
| ----------------------- | -------- | ---------------------------------------- |
| Mobile Captures         | `/daily` | Triage from notes/mobile-captures (mixed)|
| Focus                   | `/daily` | Task data + user priorities (mixed)      |
| Task Tree               | `/daily` | Task hierarchy snapshot (machine)        |
| Today's Story           | `/daily` | Synthesis from merges + sessions + tasks |
| FYI                     | `/daily` | Email triage (mixed)                     |
| Merged PRs              | `/daily` | GitHub API query (machine)               |
| Session Log/Timeline    | `/daily` | Session JSON synthesis (machine)         |
| Project Accomplishments | `/daily` | Session JSON synthesis (mixed)           |
| Reflection              | `/daily` | Goals vs achieved analysis (machine)     |
| Abandoned Todos         | `/daily` | End-of-day (user)                        |

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers in generated content (only valid in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax (e.g., `[[Greg Austin]]`, `[[academicOps]]`)
3. **Task IDs**: Always include task IDs when referencing tasks (e.g., `[ns-abc] Task title`)

---

## 1. Create note

Manage the initial creation of the daily note (or skip if it already exists).

> See [[instructions/briefing-and-triage]] for details on note creation and carryover verification.

## 1.5. Mobile Capture Triage

Process unprocessed notes from `notes/mobile-captures/` (captured via iPhone shortcut / quick-capture workflow).

> See [[instructions/mobile-capture-triage]] for the triage protocol.

## 2. Update daily briefing

Triage recent emails to provide an FYI briefing.

> See [[instructions/briefing-and-triage]] for email classification details.

## 3. Today's Focus

Populate the Focus section with priority dashboards and intelligent task recommendations.

> See [[instructions/focus-and-recommendations]] for task tree generation, pending decision queries, and recommendation heuristics.

## 4. Daily progress sync

Synchronize work from session summaries, merged PRs, and completed tasks back into the daily note and task files.

> See [[instructions/progress-sync]] for session loading, PR querying, task matching, and cross-linking protocols.

## 5. Work Summary

Generate natural language narratives of the day's achievements for both the daily note and terminal output.

> See [[instructions/work-summary]] for story synthesis and terminal briefing formats.

---

## Error Handling

- **No mobile captures**: Skip triage, continue with email briefing
- **Outlook (optional plugin) unavailable**: Skip email triage, continue with recommendations
- **GitHub CLI unavailable**: Skip merged PR listing, note in section
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`
- **Memory server unavailable**: Skip semantic task matching, continue with daily.md updates
- **Task file not found**: Log warning "Task file missing: {path}", continue to next accomplishment
- **Unexpected task format**: Log warning "Skipping task {id}: unexpected format", continue processing

## Daily Note Structure (SSoT)

See [[references/note-template]] for the complete daily note template.
