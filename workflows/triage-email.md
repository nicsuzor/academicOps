# Email Triage Workflow

Classify emails into actionable categories using semantic understanding.

**Used by**: daily skill (morning briefing), email command

## Pre-Classification Check

**CRITICAL**: Before classifying inbox emails, check sent mail first.
If matching sent reply exists → **Skip** (already handled).

## Classification Categories

### Task (Requires Action)

Create task when ANY of these signals present:

**Explicit**: "Please review...", "Can you...", deadlines, decision requests, scheduling, review requests

**Implicit**: Personal invitations requesting participation, questions expecting response, emails about user's strategic interests, deliverables to process, event invitations from real people addressed personally

**Key rule**: If email asks for opinion, participation, or response—even phrased as question—it's a **Task**, not FYI.

### FYI (Important, No Action)

Extract key info, present to user, then archive:

**Signals**: "awarded", "accepted", "approved", outcomes, decisions, deadline changes, thank-you for completed work

### Skip (Safe to Ignore)

Archive without review:

**Signals**: Already replied, noreply@/newsletter@, digests, automated CI notifications, generic mass communications, domain-irrelevant funding/CFPs

### Uncertain

Present to user when: mixed signals, unknown sender, can't determine if response expected.

## Priority Inference (for Tasks)

| Priority | Signals |
|----------|---------|
| **P0** | "URGENT", "ACTION REQUIRED", deadline <48h |
| **P1** | Deadline <1 week, collaborator requests, meeting prep |
| **P2** | Deadline <2 weeks, general correspondence |
| **P3** | No deadline, administrative |
