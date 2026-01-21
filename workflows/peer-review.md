# Peer Review Workflow

Structured peer review for grant or fellowship applications with bot-assigned subtasks for parallel processing.

## Inputs

Before starting, gather:

1. **Assessment package** - Zip file or folder containing application PDFs
2. **Scheme identifier** - e.g., "ARC FT26", "NHMRC Ideas 2026"
3. **Parent task ID** - Task to nest review tasks under (create if none exists)
4. **Workspace path** - Where to set up review folder (default: `data/reviews/<scheme-slug>/`)

## Phase 1: Setup

- Create Workspace folders
- Download/Locate Assessment Criteria
    - Search for "[scheme name] assessor handbook" or "assessment criteria"
- Extract key criteria structure for template

- Generate review template based on criteria structure.

## Phase 2: Task Scaffolding

For each application:
- Create Parent Review Task
- Create 3 subtasks per application, all assigned to `bot` for automated processing:
    - transcribe (Convert PDF to markdown)
    - Draft Review Doc with factual responses providing information in response to each criterion
    - Draft initial observations against assessment criteria


## Phase 3: Execution (Bot Tasks)

After scaffolding, bot-assigned subtasks can be processed:

### Transcribe Task
1. Read PDF using Read tool or pdf-to-md conversion
2. Extract text preserving structure (headings, sections)
3. Write to `<APP_ID>-transcript.md`
4. Mark task complete

### Draft Review Doc Task
1. Copy template to `<APP_ID>-review.md`
2. Fill metadata fields from application
3. Extract descriptive information (candidate bio, project summary)
4. Mark task complete

### Initial Observations Task
1. Read transcript and criteria
2. For each criterion, note relevant evidence from application
3. Flag gaps or concerns
4. Append observations to review doc
5. Mark task complete

## Phase 4: Composition (Human + Agent)

After initial observations, the reviewer drafts assessment comments. Agent assists with redrafting in reviewer's voice.

### Composition Principles

**Tone**: Professional positive assessment
- Enthusiastic where evidence warrants, but measured not effusive
- "Strong track record" not "exceptional and outstanding track record"
- "Reasonable confidence" not "high confidence"
- "Timely and important" not "urgent, not merely timely"

**Voice**: Reviewer's independent critique
- Do NOT quote application material back ("seminal", "unique", "world-leading")
- Evaluate claims, don't restate them
- The reviewer's job is assessment, not summarization

**Structure**: Balance across sections
- Shorter sections (Benefit, Feasibility) need expansion to avoid looking thin
- Aim for comparable depth across all criteria
- Character count check: each section should meet minimum, Overall Comments substantially exceeds minimum

**Style**: Apply reviewer's style guide if available
- Load `STYLE.md` or equivalent before composition
- Sharp topic sentences that deliver complete thoughts
- Evidence before abstractions
- Acknowledge complexity without paralysis

### Composition Workflow

1. **Human completes initial assessment** with notes and scores
2. **Agent reads style guide** and review template
3. **Agent redrafts** in reviewer's voice, applying composition principles
4. **Human reviews** and provides feedback (tone calibration, balance)
5. **Agent revises** based on feedback
6. **Verify**: Character counts meet minimums, all scores filled

### Common Revision Requests

| Feedback | Action |
|----------|--------|
| "Too enthusiastic" | Dial down superlatives, use measured language |
| "Don't quote the application" | Remove quoted praise, replace with evaluative statements |
| "Expand this section" | Add substantive analysis, not padding |
| "Stay in my voice" | Re-read style guide, match sentence patterns |
