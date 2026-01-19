# Email Triage Workflow

Classify emails into actionable categories using semantic understanding (not keyword matching).

**Used by**: [[skills/daily]] (morning briefing), [[commands/email]]

## Pre-Classification Check

**CRITICAL**: Before classifying ANY inbox email, check sent mail first.

1. Fetch sent mail: `mcp__outlook__messages_list_recent(limit=20, folder="sent")`
2. For each inbox email, compare subject (ignoring Re:/Fwd: prefixes) against sent subjects
3. If matching sent reply exists → **Skip** (already handled)

This prevents duplicate task creation for emails you've already responded to.

## Classification Categories

### Task (Requires Action)

Create task or flag for `/email` processing when ANY of these signals present:

**Explicit action indicators:**
- Direct requests: "Please review...", "Can you...", "Need your...", "Could you..."
- Deadlines: "by Friday", "due Nov 15", "before the meeting"
- Decision points: "Your vote on...", "Approve/reject...", "Sign off on..."
- Scheduling: "Confirm attendance", "RSVP", "Book travel"
- Review requests: "Feedback needed", "Please comment", "Review attached"

**Implicit action indicators:**
- Personal invitations requesting participation: "Would you be interested in...", "Wanted to see if you...", "Let me know if..."
- Questions directed at recipient expecting response
- Emails from known contacts about user's strategic interests (check strategy.md)
- Deliverables requiring processing: attached documents, spreadsheets, files to upload/integrate

**Key rule**: If an email asks for the user's opinion, participation, or response - even phrased as a question or "just sharing" - it's a **Task**, not FYI.

### FYI (Important, No Action)

Read body, extract key info, present to user before archiving:

**Signals:**
- Contains: "awarded", "accepted", "approved", "decision", "published", "outcome"
- From: OSB, ARC, grant/research bodies, institutional announcements
- Subject: conference acceptance, publication notification, funding outcome
- Significant deadline changes or policy updates affecting user's work
- Thank-you notes for completed work (e.g., "Thank you for your peer review")
- Pure status updates not requiring response

**For FYI emails**: Extract key information (dates, amounts, outcomes, decisions, links) for presentation in daily note.

### Skip (Safe to Ignore)

Archive without review:

**Signals:**
- Already handled (sent reply exists)
- From: `noreply@`, `newsletter@`, `quarantine@`, `digest`
- Subject: "Weekly digest", "Newsletter", "Update"
- Automated notifications without specific action: CI failures, service alerts
- Generic mass communications: CFPs to mailing lists, webinar invites
- Domain-irrelevant: funding/CFPs/opportunities outside user's research domains (check strategy.md)

### Uncertain

Present to user for manual classification when:
- Mixed signals (looks like FYI but has deadline mention)
- Unknown sender with ambiguous content
- Can't determine if response expected

## Priority Inference (for Tasks)

When creating tasks from emails, infer priority from signals:

| Priority | Signals |
|----------|---------|
| **P0** (Urgent) | "URGENT", "ACTION REQUIRED" in subject; OSB votes; deadline <48h; high-importance sender |
| **P1** (High) | Deadline <1 week; review requests from collaborators; meeting prep; grant/paper deadlines |
| **P2** (Normal) | Deadline <2 weeks; general correspondence; unclear urgency |
| **P3** (Low) | No deadline; administrative tasks; travel confirmations |

## Classification Summary

| Category | Signals | Action |
|----------|---------|--------|
| **Task** | deadline, "please", "review", "vote", direct question, invitation | Create task |
| **FYI** | "awarded", "accepted", "decision", from grant bodies, thank-you | Extract info, present |
| **Skip** | noreply@, newsletter, digest, automated, already replied | Archive |
| **Uncertain** | mixed signals, ambiguous | Ask user |

## Examples

### Task (correctly classified)

> **Subject**: Interest in joining working group?
> **From**: Dr. Jane Smith
> **Body**: "wanted to see if you'd be interested in this idea... organise a zoom discussion"

**Classification**: Task (P1) - Personal invitation requesting participation, from known contact, strategic interest

### FYI (correctly classified)

> **Subject**: Thank you for your peer review
> **From**: Academic Law Journal
> **Body**: "We greatly appreciate the time you have taken to review"

**Classification**: FYI - Thank-you for completed work, no action needed

### Skip (correctly classified)

> **Subject**: [username/project] Run failed: CI Pipeline
> **From**: GitHub notifications

**Classification**: Skip - Automated CI notification
