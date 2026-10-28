---
alias:
  - wf-daily
  - tpl_daily
  - tpl-daily
description: Universal daily note workflow -- read existing note content to enrich and reconcile it, strike out completed tasks, process user annotations into tasks/updates, elevate verbatim requests and high-signal prompts into tracking and work tasks, itemize merged PR elements, and compose a scannable, high-signal briefing.
id: wf-daily
tags:
  - wf-template
  - daily
  - briefing
title: wf-daily
type: template
---

## What this step does

Creates or updates today's daily note as a scannable cognitive prosthesis. The daily note reads what the user has been working on, enriches and reconciles existing note content, and organizes threads into what was set out, what came up, the day's agenda, and open decisions.

## Obligations

1. **Untruncated Ingestion & Preconditions**: Fetch the full daily template without truncation (`truncated: false`). Ensure PKB interface answers. Enforce strict single-line scannable ceiling (≤25 words per bullet) on objectives. Absolutely ban run execution logs (`## Daily Log`), cron heartbeats, and raw reconcile dumps.
2. **Enrich Existing Note Content**: When updating an existing daily note for today, workers MUST read existing content and actively enrich it:
   - _Strike out completed tasks_: Inspect tasks listed in the note (under set-out, came-up, still open, or agenda sections). If a task has closed on the graph, strike it out (`~~item~~`) or rephrase it so its completion is obvious.
   - _Process user annotations, comments, and instructions_: Extract user annotations, comments, indications of dealt-with tasks, or custom directives. File them as updates on existing tasks or create new tasks with proper links and parents. Update the note text in-place, rewriting annotations with recorded task IDs, slugs, and actions taken (`*Filed as [[task-id]]: action taken*`).
   - _Elevate verbatim user requests_: Verbatim requests, notes, or custom sections placed in the note reflect deliberate, high-priority user signals. Verify if a tracking task exists. If not, create a tracking task assigned to the front supervisory agent (`ida`) under `agent_brains/ida` for follow-up. If the underlying work has no task, create one situated under the appropriate parent on the graph (marked `status: in_progress`). If matching an existing task, situate it properly.
   - _Itemize merged PR progress_: If a relevant PR has merged for tracked work, update the note to itemize completed versus incomplete elements in a checklist (`- [x]` completed, `- [ ]` incomplete), leaving undone components visible.
   - _Carry over incomplete work_: Incomplete elements from merged PRs and unfinished tasks carry over as incomplete work to the next day's note.
3. **Trawl Daily Prompts for Consolidated Insights (`wf-prompt-objectives`)**:
   - Trawl user prompts across daily trace sources to recover genuine asks, high-signal insights, and open loops.
   - Where the user wrote a detailed handwritten prompt or emphasized task importance, apply the same verbatim elevation (ensuring Ida tracking tasks under `agent_brains/ida` and situated work tasks).
   - Consolidate related items into dense thematic summaries rather than outputting raw laundry lists.
4. **Read Agenda & Obligations**: Run correspondence sweep over the window since last note compose; inspect candidate task bodies to distinguish conditional invitations from mandatory commitments; read today's calendar and personal invitations.
5. **Reconcile the Graph**: Run graph reconciliation (`wf-reconcile`). Escalate pending user decisions to `## With you`. Reconcile must not dump raw mutations or system logs into the note.
6. **Collect Open PRs**: Query open pull requests across active repositories requiring user action (review, merge, close). If GitHub is unreachable, emit quiet single-line status (`*Open PRs unverified (GitHub unreachable at run time).*`) without carrying stale tables.
7. **Assemble State**: Subagent reads graph status, owners, due dates, and moved agent work for tracked items, grouping agent work by parent epic.
8. **Judge and Write**: Rebuild note applying the core filter ("would the user act on it or be relieved to know where it stands today?"). Recompose machine sections fresh, preserve user priorities and running accounts verbatim, and write atomically through the PKB interface.

## Structure

1. **Lede**: One or two lines making order of the day; top priority first.
2. **`## Catastrophic`**: Urgent items with verbatim consequence text; omitted if none.
3. **`## Today`**: Today's calendar events, emails needing reply today, and hard deadline commitments. Optional invitations phrased conditionally.
4. **`## What you set out to do`**: One scannable line (≤25 words) per set-out objective, heaviest first. Completed items struck out (`~~item~~`). Includes `<details><summary>Still open from before today (n)</summary>` for carried-over incomplete work, and `<details><summary>What you wrote</summary>` for user priorities.
5. **`## What came up along the way`**: One scannable line (≤25 words) per branched objective, naming what it branched from.
6. **`## With you`**: Decisions and answers waiting on the user now.
7. **`## Open PRs`**: Clean table of open PRs requiring user action (`PR | What it does | Recommendation`).
8. **`## Agents' work`**: Fold `<details><summary>Agents' work (n groups)</summary>` grouping moved work by parent epic.
9. **`## Invitations`**: Worthwhile invitations judged against standing goals; omitted if none.
10. **`## Today's work`**: Preserved running account of the day.

## Must not

- Must not overwrite or discard user annotations, comments, or custom sections without converting them to tracked graph tasks/updates and updating the note text with task IDs and slugs.
- Must not append `## Daily Log`, cron heartbeats, commit SHAs, or raw reconcile mutation dumps.
- Must not exceed 25 words per bullet in objective sections.
- Must not carry forward multi-day stale PR tables or inject apologetic system disclaimers.
- Must not output raw prompt laundry lists; prompt trawling must produce dense consolidated summaries.
