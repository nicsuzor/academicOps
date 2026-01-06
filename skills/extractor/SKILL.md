---
name: extractor
category: instruction
description: Archive information extraction - assess archival documents and identify information worth preserving in the knowledge base.
allowed-tools: Read,Skill
version: 1.0.0
permalink: skills-extractor-skill
---

# Archive Information Extraction Skill

Assess archival documents (emails, correspondence, receipts) to identify information worth preserving in the knowledge base. This skill provides judgment criteria only - actual storage is handled by `Skill(skill="remember")`.

## Purpose

Filter noise from archival documents and identify genuinely significant information that should be preserved. Most archival documents have NO long-term value - be highly selective.

## Assessment Criteria

### Decision Framework

For each document, use LLM judgment to answer:

1. **Is this important enough to mention at a monthly research meeting?**
2. **Would I want to remember this in 5 years?**
3. **Is this a concrete outcome, or just noise?**
4. **Did Nic take significant action, or is this passive/routine?**

**Trust your judgment** - you understand context better than regex patterns.

### What to Extract

#### 1. Projects & Publications
- **Papers**: Actual submissions, acceptances, revisions, publications (not CFPs)
- **Grants**: Applications submitted, outcomes received, progress reports
- **Books/Chapters**: Contracts signed, submissions, publications
- **Research Projects**: Project initiation, significant milestones, new collaborations
- **Awards**: Significant awards or recognitions
- **Milestones**: Major career milestones, important advocacy/policy work
- **Media**: Media appearances or public engagement

**Think**: Is this a concrete action or outcome? Or just noise?

#### 2. Professional Activities
- **Events Organized**: Conferences, workshops, panels Nic ran/chaired/coordinated
- **Speaking**: Confirmed talks, keynotes where Nic actually spoke
- **Service**: OSB decisions, editorial board work, advisory roles
- **Reviews**: Actual reviews submitted (not review requests)

**Think**: Did Nic DO something significant? Or just receive an invitation?

#### 3. Applications & Career
- **Grant Applications**: Submitted applications (not drafts or ideas)
- **Job Applications**: Roles applied for
- **Awards/Honors**: Nominations received, awards won
- **Promotion/Tenure**: Applications, outcomes

**Think**: Is this a concrete milestone or application? Or just planning?

#### 4. Important Contacts & Relationships
- **Collaborations**: Research collaboration proposals or agreements
- **Partnerships**: Grant writing partnerships, joint projects
- **Networks**: Connections made at conferences, international research networks
- **Students**: PhD supervision milestones, significant correspondence
- **Institutions**: New institutional relationships, key ongoing relationships

**Think**: Is this the start/milestone of an important relationship? Or routine correspondence?

#### 5. Financial Records
- **Receipts, invoices, contracts** by project and category
- Log with: message ID, date, entity, project, description, amount, currency, payment status
- Essential for grant acquittal and tax purposes

**Think**: Will we need this for financial reporting?

### What to Skip

Most documents are noise. Skip:

- Mass communications (newsletters, announcements, marketing, digests)
- Administrative routine (meeting scheduling, calendar invites, reminders)
- Declined invitations (conferences not attended, webinars skipped)
- Generic outreach (CFPs, generic collaboration requests, surveys)
- Automated systems (notifications, confirmations - unless significant)
- Spam/phishing
- Personal chitchat without professional substance
- Room bookings and logistics
- Normal student supervision (unless exceptional)
- Regular staff interactions
- Forum posts and mailing list discussions
- Course coordination and teaching logistics
- Standard reference requests

**Test**: Would I forget this within a week with no consequence?

### Uncertain Cases

When uncertain:
- **Lean toward extraction** in initial pass
- Tag output with `#review-classification` for manual review
- Better to extract and discard later than miss important information

## Judgment Examples

**EXTRACT**: "Your paper 'Platform Governance' has been accepted by Nature"
→ Clear publication outcome

**SKIP**: "CFP: Submit to Journal of Platform Studies by Dec 1"
→ Generic invitation, no submission

**EXTRACT**: "Congratulations, your FT210100263 grant has been awarded $500K"
→ Grant outcome with specifics

**SKIP**: "Reminder: Your FT210100263 annual report is due next month"
→ Administrative reminder

**EXTRACT**: "Following our chat at IGF, I'd love to collaborate on disinformation research..."
→ New substantive collaboration starting

**SKIP**: "You're invited to join our webinar on content moderation"
→ Mass invitation, not personal

**EXTRACT**: Email from examiner with detailed feedback on PhD thesis
→ Supervision milestone

**SKIP**: "HDR student seminars happening this week"
→ Generic announcement

**EXTRACT**: "OSB Case 2025R final decision: Upheld with modifications..."
→ Actual OSB work product

**SKIP**: "OSB weekly meeting reminder"
→ Routine scheduling

## Key Information to Identify

When you decide to extract, identify these elements:

### People
- Full name and affiliations
- Contact information (if provided)
- Role/position
- Relationship to Nic (collaborator, contact, student, etc.)

### Organizations
- Universities and research institutions
- Research groups or labs
- Funding bodies
- Conferences or professional organizations

### Events
- Conference/workshop name
- Speaking engagements
- Meetings with significance
- Research visits

### Projects/Collaborations
- Research topics discussed
- Grant proposals
- Joint publications
- Ongoing or proposed collaborations

### Dates & Timing
- When correspondence occurred
- When events happened or will happen
- Project timelines if mentioned

### Topics/Tags
- Research areas (platform-governance, content-moderation, AI-ethics, etc.)
- Geographic locations
- Types of activity (collaboration, speaking, reviewing)

### Identifiers (CRITICAL)

**Always extract canonical identifiers** to allow future reference:

- Email message ID (preferred)
- Source UUID or unique identifier
- URL or DOI
- If no canonical ID exists, create citation: "email from [sender] to [recipient] dated [YYYY-MM-DD] subject: [subject]"

Store identifier inline with extracted information.

## Storage

Use `Skill(skill="remember")` to store extracted information in the knowledge base. The remember skill handles:
- Entity creation/updates
- Format validation
- Deduplication checking
- Proper categorization

Store information using the memory server with properly formatted markdown. Tag extracted information appropriately for searchability and future retrieval.

**Common approaches for email extraction**:
- Email metadata (sender, date, subject) → Use memory tags like `#email`, `#correspondence`
- Project information → Use memory tags like `#project`
- Coordinator/team roles → Store with descriptive relationships
- Timeline/duration → Use memory tags like `#timeline`, `#deadline`
- Status information → Use memory tags like `#status`
- Relationships between people → Document relationships clearly with role descriptions

**Storage principles**:
- Use clear, structured memory entries
- Include all relevant metadata and timestamps
- Tag appropriately for semantic search
- Avoid inventing custom categories or types
- Delegate all storage to the remember skill

## Quality Standards

### Confidence Levels
- Only extract when information is clear and valuable
- Mark uncertain extractions with `#review-classification`
- Skip ambiguous or unclear information

### Atomic Information
- Each piece of information should be specific and verifiable
- Include dates, sources, and context
- Tag appropriately for searchability

### Fail Fast
- If document is malformed, skip it and log error
- If extraction is ambiguous, skip it or tag for review
- Continue processing other documents
