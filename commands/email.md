---
name: email
description: Check email, automatically update task database, and present digest
permalink: aops/commands/email
---

# Email Management

Launch the task-manager agent to check email and update task database.

## Workflow Parameters

**Default Account**: Focus on QUT work account (n.suzor@qut.edu.au) unless explicitly asked for other accounts.

**Time Window**: Retrieve emails from the last 2-4 weeks to catch potentially missed emails, not just recent 24-48 hours.

**FYI Email Handling**:
- Batch FYI emails by category (newsletters, notifications, automated reports)
- Present concise summary for each batch:
  * Category name
  * Count of emails
  * 2-3 sentence summary of common content
- Propose archiving entire batches (not individual emails)

**Archive Strategy**:
- Only propose archiving for QUT account emails (folder structure verified)
- Skip archive operations for personal account (folder structure issues)
- Request confirmation before archiving any batch

The task-manager agent will:
- Fetch emails from QUT account (last 2-4 weeks) using email skill
- Extract actionable tasks using tasks skill
- Update existing tasks if emails provide new information
- Present digest of new/updated tasks
- Present FYI emails in batches with summaries
- Propose batches of emails to archive (with confirmation)
