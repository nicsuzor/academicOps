---
name: briefing-bundle
type: skill
category: instruction
description: Generate morning briefing bundle with decision coversheets, email drafts, and annotation targets from the daily note. Run /daily first.
triggers:
  - "morning brief"
  - "briefing bundle"
  - "generate bundle"
  - "decision brief"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,~~email,~~calendar,~~pkb
version: 0.1.0
permalink: skills-briefing-bundle
---

# Briefing Bundle Skill

Generate a morning briefing document from the daily note. The bundle presents decisions with coversheets and recommendations, pre-drafts emails, includes calendar context, and provides annotation targets for Nic to mark up. It is consumed in a single sitting and processed back into the system.

**This skill produces a separate document from the daily note.** The daily note is a living progress tracker; the bundle is a morning-only decision brief. See [[specs/daily-briefing-bundle.md]] for the full specification and rationale.

## Invocation

```
/bundle         # Generate today's briefing bundle
```

**Prerequisite**: Run `/daily` first. The bundle reads the daily note — it does not re-query data sources the daily note already covers.

## CRITICAL BOUNDARY

**This skill generates a document. It does NOT execute decisions.**

- Generating the bundle ≠ acting on its contents
- Email drafts are staged in Outlook as drafts, never auto-sent
- Task status changes only happen during annotation processing (`/process-bundle`)
- The bundle is ephemeral — actions persist in PKB and Outlook, not in the bundle file

## Pipeline

### 1. Gather data

**From the daily note** (read, do not re-query):

```
Read $ACA_DATA/daily/YYYYMMDD-daily.md
```

Extract:

- Focus section → decision items, overdue tasks, priority recommendations
- FYI section → items for FYI section of bundle
- Carryover section → items to carry forward
- Open PRs section → any needing human review

**From synthesis.json** (if available):

```
Read $ACA_DATA/dashboard/synthesis.json
```

**From yesterday's bundle** (if exists):

```
Read $ACA_DATA/daily/YYYYMMDD-bundle.md  # yesterday's date
```

Check for unprocessed annotations → carry forward un-annotated items.

**New queries** (only what the daily note doesn't provide):

For each item that will become a decision coversheet:

```python
# Full task context for coversheet
task = mcp__pkb__get_task(id=task_id)

# Related emails for draft threading
email = mcp__outlook__messages_get(entry_id=entry_id)
```

For calendar:

```python
# Today + tomorrow
today = mcp__outlook__calendar_list_today()
upcoming = mcp__outlook__calendar_list_upcoming(days=2)
```

### 2. Classify and filter

From all gathered items, classify each into exactly one bundle section:

| Section       | Criteria                                                     |
| ------------- | ------------------------------------------------------------ |
| **Decisions** | Status=waiting/review, assigned to nic, needs human judgment |
| **Calendar**  | Meetings today + tomorrow, with prep context                 |
| **Emails**    | Items needing a reply (not just FYI)                         |
| **FYI**       | Informational items from daily note FYI section              |
| **Carryover** | Items from previous days still open                          |

**Filter rules**:

- Target 5-15 total items. If >15, trim lowest-priority FYIs first.
- Technical tasks that don't need human judgment (CI fixes, code review) → exclude unless blocking.
- Items already resolved since the daily note was generated → exclude.

### 3. Build coversheets

For each **Decision** item, generate a coversheet using the template in [[references/coversheet-template]].

**The editorial work happens here.** This is the step that makes the bundle different from the daily note. For each item:

1. Read the full task body (`get_task`)
2. Read related emails if the task references an email thread
3. **Write a one-line decision summary** — not a task description, but what Nic needs to decide
4. **Make a recommendation** — explicit, justified in one sentence. Never "it depends"
5. **Assess stakes** — what happens if deferred another week
6. **Write 3-5 bullet points of context** — the minimum needed to act. If you're writing more than 5, you're including too much
7. **Draft an email** if the decision requires a reply. Complete draft in Nic's voice per STYLE.md

**Coversheet quality rules**:

- Max 15 non-blank lines above the fold (before `<details>`)
- Supporting detail goes in collapsed `<details>` sections
- The coversheet alone must be sufficient to decide. No "see task for details"
- Include the Outlook `entry_id` in email drafts for threading

### 4. Build remaining sections

**Calendar**: For each meeting today/tomorrow, include: time, title, attendee names with brief context (role/relationship), prep notes if applicable, and any documents to pre-read. Flag free blocks: "2hr free block 10am-12pm — suitable for deep work."

**Emails**: For items needing replies that aren't tied to a decision coversheet, use the email draft template in [[references/email-template]]. Full drafts, not talking points.

**FYI**: Compress each to 2-3 sentences. Group by project (OSB, QUT, academic). Each gets `<!-- @nic: noted -->`. Items that might generate a task include a suggested title: `<!-- @nic: task: [suggested title] -->`.

**Carryover**: Items from previous days, ordered by age (oldest first). Each gets a checkbox. Items carried 3+ consecutive days get: "⚠️ Carried N days — decide: act, defer, or cancel?"

### 5. Write Executive Summary

Written LAST (after all sections are assembled). Max 10 lines containing:

1. Item counts by type: "3 decisions, 2 meetings, 4 emails, 3 FYIs"
2. **The single most urgent item** (bold), with why
3. Calendar shape: "3 meetings, 2hr free block 10am-12pm"
4. Recommended work sequence: numbered, 1-3 sentences
5. Annotation quick-reference: `approved | send | decline | defer to DATE | noted | task: [title]`

### 6. Self-review

Before writing the file, verify:

- [ ] All task IDs resolve (test with `get_task`)
- [ ] Every decision has a bold recommended action
- [ ] Every item has a checkbox and annotation target
- [ ] No coversheet exceeds 15 lines above the fold
- [ ] No duplicate items across sections
- [ ] Total items 5-15 (warn if outside, fail if >25)
- [ ] Email drafts use "Hi [Name]" salutation and "Best" or "Cheers" sign-off
- [ ] Executive Summary is ≤10 lines and contains recommended sequence

Log issues in frontmatter `qa_issues`. If critical issues found (broken task IDs, missing recommendations), fix and re-check (max 2 iterations).

### 7. Export

Write bundle to: `$ACA_DATA/daily/YYYYMMDD-bundle.md`

Use the bundle template from [[references/bundle-template]] for the overall structure.

Output to terminal:

```
Bundle generated: daily/YYYYMMDD-bundle.md
N decisions, N emails, N FYIs, N carryover items
Most urgent: [item description]
Open in Obsidian to review and annotate, then run /process-bundle.
```

---

## Section Order (fixed)

Energy-intensive first, passive last:

1. Executive Summary
2. Decisions
3. Calendar
4. Emails
5. FYI
6. Carryover
7. Done (empty finish line)

---

## Error Handling

| Failure                  | Behaviour                                                                                       |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| Daily note doesn't exist | HALT with: "Run /daily first — the bundle reads the daily note"                                 |
| Outlook unavailable      | Generate without email drafts/calendar. Note: "Email/calendar unavailable" in Executive Summary |
| PKB unavailable          | Generate from daily note text only — no task enrichment                                         |
| No decision items found  | Generate bundle with calendar + FYI only. Note in summary: "No decisions today"                 |
| Task ID doesn't resolve  | Exclude item, log in qa_issues                                                                  |

---

## Templates

See [[references/coversheet-template]] for the decision coversheet format.
See [[references/email-template]] for the email draft format.
See [[references/bundle-template]] for the overall bundle structure.
