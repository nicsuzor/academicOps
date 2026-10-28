---
title: Daily note and reconcile -- steps and owners
type: spec
category: workflow
status: ready
tags: [spec, daily, reconcile, workflow]
---

# Daily note and reconcile: steps and owners

What runs, in order, when the daily note is composed, and which workflow holds each step. Source of record for where each step lives.

## Daily note -- wf-daily / tpl_daily

The daily note reads what the user has been working on, enriches and reconciles existing note content, and makes order out of the day: what was set out, what came up, what is on today's agenda, and what only the user can decide. Routine queries (done lists, task-by-task status, full PR lists) and internal traces belong in the PKB, telemetry, and dashboard. The note completely bans run execution logs (`## Daily Log`), hourly cron heartbeats, raw reconcile dumps, and defensive system failure narratives.

| # | Step | What it does | Contained in |
| - | - | - | - |
| 0 | Preconditions | Confirm PKB answers; verify template fetched untruncated (`truncated: false`); enforce single-line scannable ceiling (≤25 words per objective bullet) and absolute ban on run logs / heartbeats (`## Daily Log`) | wf-daily |
| 0b | Enrich existing note | Read existing daily note content and enrich it: strike out an item (`~~item~~`) only when its result has reached the user, not when its task closes; extract user annotations, comments, and instructions, filing them as tasks or updates and rewriting note text in-place with task IDs and slugs; elevate verbatim requests | wf-daily |
| 1 | Read conversations & trawl prompts | Pull daily user prompts across trace sources; strip agent traffic; thread asks; trawl for high-signal nuggets and unfinished work; elevate detailed handwritten prompts; synthesize dense consolidated thematic summaries (no laundry lists) | [[wf-prompt-objectives]] (hand-back) |
| 1a | Sort set out vs came up | An objective holding a session's opening ask or fresh unprompted ask is set out; one arising from other work came up, naming what it branched from | wf-daily |
| 2 | File asks whose result has not reached the user & situate verbatim requests | File asks whose result has not reached the user; deliberate verbatim requests elevated to Ida-assigned tracking tasks under `agent_brains/ida` and situated work tasks (marked `in_progress`); itemize merged PR elements into checklists with undone work carried over | wf-daily |
| 3 | Read today's agenda | Correspondence sweep over window since previous note; inspect candidate task bodies to distinguish conditional invitations from mandatory commitments; read today's calendar; personal invitations no task carries | Correspondence sweep + wf-daily |
| 4 | Reconcile | Move graph to truth (single-flight execution); returns escalated decisions for `## With you`; raw reconcile dumps forbidden | wf-reconcile |
| 5 | Collect open PRs | Query open PRs across active repos requiring user action (review, merge, close); if unreachable, replace with quiet single-line status (`*Open PRs unverified (GitHub unreachable at run time).*`) | wf-daily |
| 6 | Assemble state | Subagent reads graph for tracked IDs: status, owner, due date, open parent, what moved today; agent work grouped by parent epic | wf-daily |
| 7 | Judge and write | Rebuild sections applying the core filter; enforce ≤25-word single-line ceiling on objectives; preserve user priorities and running accounts verbatim; atomic write through PKB interface | wf-daily |

## Reconcile -- wf-reconcile

| # | Step | What it does | Contained in |
| - | - | - | - |
| 1 | Load active tasks | Read non-terminal tasks across active statuses within the sweep window; closures by principal are self-authorizing | wf-reconcile |
| 2 | Match PRs | Tie open and merged PRs to their tasks; merged PR closes task done, open PR leaves review; itemize completed vs undone elements for multi-element tasks | wf-reconcile |
| 3 | Clear review | Move every review task to exactly one outcome under the bazaar model; dispatch or queue minted review tasks | wf-reconcile |
| 4 | Settle decisions | Settle open decisions where record or reversible judgment allows before escalating | wf-reconcile |
| 5 | Check returns | Verify returned work on the papers before deciding what reaches the user | wf-reconcile |
| 6 | Reset stale claims | Reset unheld in_progress tasks (>24h unmodified) to queued; never move an actively claimed task backwards | wf-reconcile |
| 7 | Demote affected tasks | Send rot (>14d in ready/queued), unblocked dependents, siblings of landed work, and invalidated assumptions to inbox | wf-reconcile |
| 8 | Cancel on world-facts | Cancel on affirmative evidence recorded in the node body | wf-reconcile |
| 9 | Mutate | Two-step status change: body annotation followed by frontmatter mutation | wf-reconcile |
| 10 | Escalate | Settle items reaching the user under the one-level escalation rule; standalone writes to With you, daily run folds in; raw mutation summaries and system IDs prohibited | wf-reconcile |

## Ownership and Boundary Invariants

- **Run Log & Heartbeat Ban Invariant**: The daily note completely bans `## Daily Log`, hourly run heartbeats, and timestamped cron audit breadcrumbs. Internal run traces belong in telemetry and runner logs.
- **Graceful Degradation Invariant**: When an external source (GitHub, Email, Calendar) cannot be reached or has no changes, degrade gracefully in-situ with quiet single-line status (e.g. `*Open PRs unverified (GitHub unreachable at run time).*` or `No open PRs currently require your action.`). Carrying forward multi-day stale tables or writing defensive system-failure apologies is strictly prohibited.
- **Template Ingestion Invariant**: The daily note runner must fetch the full template without truncation (`truncated: false`). Truncation is an immediate fail-loud halt.
- **Reconcile Escalation Boundary Invariant**: Reconcile interfaces with the daily note exclusively through `## With you` for escalated decisions. Reconcile must never write or append raw mutation summaries, commit SHAs, PR merge logs, branch names, or container IDs to the daily note.
- **Scannable Ceiling Invariant**: All objective bullets under `## What you set out to do` and `## What came up along the way` MUST strictly conform to the 25-word single-line ceiling. Narrative paragraphs and agent choreography are forbidden.
- **Existing Content Enrichment Invariant**: Daily note workers must read what already exists in today's daily note and actively enrich it. Strike out an item (`~~item~~`) only when its result has reached the user, not when its task closes on the graph. User annotations, comments, instructions, and indicators of dealt-with work must be extracted and filed as proper task updates or new tasks, with the note text rewritten in-place citing the recorded task IDs, slugs, and actions taken.
- **Verbatim Request & Prompt Elevation Invariant**: Verbatim requests placed deliberately in daily notes and detailed or emphatic handwritten user prompts in daily traces represent high-priority signals. The worker must verify whether a tracking task exists; if missing, create one assigned to the front supervisory agent (`ida`) under `agent_brains/ida` for follow-up, and create/situate the underlying work task (marked `status: in_progress`).
- **Merged PR Element Breakdown & Carry-over Invariant**: When a PR merges for a tracked task or request with multiple components, the worker must update the daily note to show exactly which components are completed versus incomplete using a checklist (`- [x]` done, `- [ ]` incomplete), leaving undone work visible. Incomplete elements carry over to the next day's note as open work.
- **Dense Prompt Trawling & Consolidation Invariant**: Daily prompt trawling (`wf-prompt-objectives`) must actively mine daily user prompts for high-signal insights, instructions, and unfinished work. Prompts must be synthesized into dense consolidated thematic summaries of related items rather than dumped as a mechanical laundry list.
- **Task Body Inspection for Conditional Phrasing Invariant**: Candidate tasks considered for `## Today` or `## Invitations` must have their task bodies inspected before surfacing. Conditional or optional invitations (such as calls for interest or optional event RSVPs) must be phrased conditionally (e.g. 'if you want to attend, RSVP closes today') rather than framed as unconditional directives ('accept or decline').
- **Rot demotion vs. stale claims**: Stale claims (>24h unheld) are reset in Step 6; rot demotion (>14d to inbox) lives exclusively in Step 7.
- **Judgement lives in the template**: What the user cares about, the set-out / came-up sort, and the note's sections are defined in `wf-daily` / `tpl_daily`; in the daily run, sub-workflows hand back facts and the template lays them out.
- **Single-flight reconcile**: Reconcile executes in single-flight mode.
