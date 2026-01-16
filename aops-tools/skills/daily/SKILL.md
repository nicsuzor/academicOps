---
name: daily
category: instruction
description: Daily note lifecycle - morning briefing, task recommendations, session sync. SSoT for daily note structure.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move
version: 1.0.0
permalink: skills-daily
---

# Daily Note Skill

Manage daily note lifecycle: morning briefing, task recommendations, and session sync.

Location: `$ACA_DATA/sessions/YYYYMMDD-daily.md`

## Section Ownership

| Section                 | Owner    | Updated By             |
| ----------------------- | -------- | ---------------------- |
| Focus                   | `/daily` | Morning briefing + task recommendations |
| Today's Story           | `/daily` | Session JSON synthesis |
| FYI                     | `/daily` | Email triage           |
| Session Log/Timeline    | `/daily` | Session JSON synthesis |
| Project Accomplishments | `/daily` | Session JSON synthesis |
| Abandoned Todos         | `/daily` | End-of-day             |

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers in generated content (only valid in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax (e.g., `[[Greg Austin]]`, `[[academicOps]]`)
3. **Bead task IDs**: Always include bead IDs when referencing tasks (e.g., `[ns-abc] Task title`)

## 1. Create note

Check `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**If missing**: Create from template (see Daily Note Structure above), then:

1. Read the previous working day's daily note
2. Identify any incomplete tasks and copy to "## Carryover from Yesterday" section
3. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
4. Note overdue items from yesterday's Focus Dashboard

### 1.2: Load Recent Activity

Read last 3 daily notes to show project activity summary:

- Which projects had work recently
- Current state/blockers per project

## 2. Update daily briefing

### 2.0: Load User Context for Email Classification

Before classifying emails, load domain context to filter by relevance:

```bash
Read $ACA_DATA/CORE.md        # User profile, research focus
Read $ACA_DATA/context/strategy.md  # Active projects and domains
```

**Use this context during classification**: Emails about funding, CFPs, conferences, or opportunities OUTSIDE the user's research domains should be classified as **Skip** (domain-irrelevant), not FYI. The user's domains are visible in strategy.md under "Projects" and "Strategic Logic Model".

### 2.1: Email Triage

Fetch recent emails via Outlook MCP:

```
mcp__outlook__messages_list_recent(limit=50, folder="inbox")
```

**CRITICAL - Check sent mail FIRST**: Before classifying ANY inbox email, you MUST fetch sent mail and cross-reference to avoid flagging already-handled items:

```
mcp__outlook__messages_list_recent(limit=20, folder="sent")
```

**For EACH inbox email**: Compare subject line (ignoring Re:/Fwd: prefixes) against sent mail subjects. If a matching sent reply exists, classify as **Skip** (already handled). This cross-reference is MANDATORY - skipping it causes duplicate task creation.

**Classify each email** (LLM semantic classification, not keyword matching per AXIOM #30):

- **FYI**: Informational, no action needed, but should see before archiving
- **Task**: Requires action AND no sent reply exists → flag for `/email` processing. This includes emails with deliverables requiring processing (attached documents, spreadsheets, files to upload/integrate), even if the email tone is informational.
- **Skip**: Automated, bulk, already handled (sent reply exists), OR domain-irrelevant (funding/CFPs/opportunities outside user's research domains)
- **Uncertain**: Present to user for classification

### 2.2: FYI Content in Daily Note

**Goal**: User reads FYI content in the daily note itself, not by opening emails.

**Thread grouping**: Group emails by conversation thread (same subject minus Re:/Fwd:). Present threads as unified summaries, not individual emails.

**For each FYI thread/item**, fetch full content with `mcp__outlook__messages_get` and include:

- Thread participants and who said what (if multiple contributors)
- **Actual content**: The key information - quote directly for short emails, summarize for long ones

**Format in briefing**:

```markdown
## FYI

### [Thread Topic]

[Participants] discussed [topic]. [Key content/decision/info].

> [Direct quote if short]

### [Single Email Topic]

From [sender]: [Actual content or summary]
```

**After presenting**: Use `AskUserQuestion` to ask which to archive.

**Archiving emails**: Use `messages_move` with `folder_path="Archive"` (not "Deleted Items" - that's trash, not archive). If the Archive folder doesn't exist for an account, ask the user which folder to use.

**Empty state**: If no FYI emails, skip this section.

## 3. Today's Focus

Populate the `## Focus` section with priority dashboard and task recommendations. This is the FIRST thing the user sees after frontmatter.

### 3.1: Load Task Data

```bash
cd $AOPS && bd list --limit=100
```

Parse task data from bd output to identify:

- Priority distribution (P0/P1/P2/P3 counts)
- Overdue tasks (negative days_until_due)
- Today's work by project
- Blocked tasks

### 3.2: Build Focus Section

The Focus section combines priority dashboard AND task recommendations in ONE place.

**Format** (all within `## Focus`):

```markdown
## Focus

```
P0 ░░░░░░░░░░  3/85  → No specific tasks tracked
P1 █░░░░░░░░░  12/85 → [ns-abc] [[OSB-PAO]] (-3d), [ns-def] [[ADMS-Clever]] (-16d)
P2 ██████████  55/85
P3 ██░░░░░░░░  15/85
```

**SHOULD**: [ns-abc] [[OSB PAO 2025E Review]] - 3 days overdue
**SHOULD**: [ns-def] [[ADMS Clever Reporting]] - 16 days overdue
**DEEP**: [ns-ghi] [[Write TJA paper]] - Advances ARC Future Fellowship research goals
**ENJOY**: [ns-jkl] [[Internet Histories article]] - [[Jeff Lazarus]] invitation on Santa Clara Principles
**QUICK**: [ns-mno] [[ARC COI declaration]] - Simple form completion
**UNBLOCK**: [ns-pqr] Framework CI - Address ongoing GitHub Actions failures

*Suggested sequence*: Tackle overdue items first (OSB PAO highest priority given 3-day delay, then ADMS Clever).
```

### 3.3: Reason About Recommendations

Select ~10 recommendations using judgment (approx 2 per category):

**SHOULD (deadline/commitment pressure)**:

- Check `days_until_due` - negative = overdue
- Priority: overdue → due today → due this week → P0 without dates

**DEEP (long-term goal advancement)**:

- Tasks linked to strategic objectives or major project milestones
- Look for: research, design, architecture, foundational work
- Prefer tasks that advance bigger goals, not just maintain status quo
- Avoid immediate deadlines (prefer >7 days out or no deadline)

**ENJOY (variety/energy)**:

- Check `todays_work` - if one project has 3+ items, recommend different project
- Look for: papers, research, creative tasks
- Avoid immediate deadlines (prefer >7 days out)

**QUICK (momentum builder)**:

- Simple tasks: `subtasks_total` = 0 or 1
- Title signals: approve, send, confirm, respond, check
- Aim for <15 min

**UNBLOCK (remove impediments)**:

- Tasks that unblock other work or team members
- Infrastructure/tooling improvements, blocked issues
- Technical debt slowing down current work

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### 3.4: Engage User on Priorities

After presenting recommendations, use `AskUserQuestion` to confirm priorities:

- "What sounds right for today?"
- Offer to adjust recommendations based on user context

### 3.5: Present candidate tasks to archive

```
- [ns-xyz] **[[Stale Task]]** - [reason: no activity in X days]
```

Ask: "Any of these ready to archive?"

When user picks, use `bd update <id> --status=archived` to update status.

### 4. Daily progress

Update daily note from session JSON files. Run after sessions complete or periodically.

### Step 4.1: Find Session JSONs

```bash
ls $ACA_DATA/sessions/insights/YYYY-MM-DD-*.json 2>/dev/null
```

### Step 4.2: Load and Merge Sessions

Read each session JSON. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics

### Step 4.3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

### Step 4.4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Today's Story**: Synthesize narrative from session summaries.

- format in dot points, but use prose to provide detail

**Session Log**: Add/update session entries.

**Session Timeline**: Build from conversation_flow timestamps.

**Project Accomplishments**: Add `[x]` items under project headers.

**Progress metrics** per project:

- **Scheduled**: Tasks with `scheduled: YYYY-MM-DD` matching today
- **Unscheduled**: Accomplishments not matching scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`

### Step 4.5: Update synthesis.json

Write `$ACA_DATA/dashboard/synthesis.json`:

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "sessions": {
    "total": N,
    "by_project": {"aops": 2, "writing": 1},
    "recent": [{"session_id": "...", "project": "...", "summary": "..."}]
  },
  "narrative": ["Session summary 1", "Session summary 2"],
  "accomplishments": {
    "count": N,
    "summary": "brief text",
    "items": [{"project": "aops", "item": "Completed X"}]
  },
  "next_action": {"task": "P0 task", "reason": "Highest priority"},
  "alignment": {"status": "on_track|blocked|drifted", "note": "..."},
  "waiting_on": [{"task": "...", "blocker": "..."}],
  "skill_insights": {"compliance_rate": 0.75, "top_context_gaps": []},
  "session_timeline": [{"time": "10:15", "session": "...", "activity": "..."}]
}
```

## Error Handling

- **Outlook unavailable**: Skip email triage, continue with recommendations
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`

## Daily Note Structure (SSoT)

```markdown
# Daily Summary - YYYY-MM-DD

## Focus

```
P0 ░░░░░░░░░░  3/85  → No specific tasks tracked
P1 █░░░░░░░░░  12/85 → [ns-abc] [[OSB-PAO]] (-3d), [ns-def] [[ADMS-Clever]] (-16d)
P2 ██████████  55/85
P3 ██░░░░░░░░  15/85
```

**SHOULD**: [ns-abc] [[OSB PAO 2025E Review]] - 3 days overdue
**DEEP**: [ns-ghi] [[Write TJA paper]] - Advances ARC Future Fellowship research goals
**ENJOY**: [ns-jkl] [[Internet Histories article]] - [[Jeff Lazarus]] invitation
**QUICK**: [ns-mno] [[ARC COI declaration]] - Simple form completion
**UNBLOCK**: [ns-pqr] Framework CI - Address ongoing GitHub Actions failures

*Suggested sequence*: Tackle overdue items first, then deep work.

## Today's Story

Synthesized narrative from session summaries (2-3 sentences).

## FYI

### [[Topic from Email]]

[[Sender Name]] shared: [Key content summary]

## Carryover from YYYY-MM-DD

**From yesterday:**
- [ns-abc] Task description - reason for carryover

## Session Log

| Session | Project | Summary |
|---------|---------|---------|
| - | - | No sessions yet today |

## Session Timeline

| Time | Session | Terminal | Project | Activity |
|------|---------|----------|---------|----------|
| - | - | - | - | - |

### Terminal Overwhelm Analysis

(Updated by /daily sync)

## Project Accomplishments

### [[academicOps]] → [[projects/aops]]

Scheduled: n/a | Unscheduled: 0 items

### [[writing]] → [[projects/writing]]

Scheduled: n/a | Unscheduled: 0 items

## Abandoned Todos

(Carried to tomorrow at end of day)
```
