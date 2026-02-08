# Triage Email Workflow

Classify emails into actionable categories.

## When to Use

Use this workflow when:

- Processing incoming emails
- Triaging an email inbox

## Constraints

### Critical Precondition

Before classifying any email, **check sent mail first**. If a matching reply already exists, classify as Skip.

### Classification Rules

Each email gets exactly one classification:

**Task** (create a task):

- Signals: "please review...", decisions needed, deadlines, personal invitations
- Action: Create a task with appropriate priority

**FYI** (archive):

- Signals: "awarded", "approved", outcomes, thank-you messages
- Action: Archive the email

**Skip** (archive):

- Signals: from noreply@, newsletters, already replied to
- Action: Archive the email

**Uncertain** (ask user):

- Signals: mixed signals, unknown sender
- Action: Ask the user for classification

### Priority Inference (for Tasks)

- **P0**: Contains "URGENT" or deadline is less than 48 hours
- **P1**: Deadline is less than 1 week, or collaborator request
- **P2**: Deadline is less than 2 weeks, or general request
- **P3**: No deadline, administrative

## Triggers

- When email is received → check sent mail
- If no reply exists → classify the email
- If reply exists → archive as skip
- If classified as Task → create task with priority
- If classified as FYI → archive
- If classified as Uncertain → ask user

## How to Check

- Sent mail checked: sent folder was searched for a matching reply
- Reply exists: sent mail contains a reply to this email
- Actionable signals: contains "please review", decision request, deadline, or personal invitation
- Informational signals: contains "awarded", "approved", outcome notification, or thank-you
- Skip signals: from noreply@, is a newsletter, or reply already exists
- Uncertain signals: not actionable, not informational, and not skip
- One classification per email: email receives exactly one category
