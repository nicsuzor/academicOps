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

### Naming Convention

**Always use the candidate's name/title**, never generic references:
- ✓ "Dr Albright is a capable researcher" / "A/Prof Ng's track record demonstrates"
- ✗ "The candidate is capable" / "This researcher's track record"

Use appropriate title (Dr, A/Prof, Prof) with surname throughout. This makes the review feel personalised and engaged rather than bureaucratic.

### Constructive Framing

Frame concerns as opportunities for improvement, not failures:

| Instead of | Write |
|------------|-------|
| "fails to explain" | "would benefit from clearer articulation" |
| "does not adequately demonstrate" | "could more clearly demonstrate" |
| "cannot credibly claim" | "is ambitious for the proposed scope" |
| "the application is weak on" | "the application could be strengthened by" |

### Strengths-First in Critical Assessments

Even when giving a low score, lead with genuine strengths before raising concerns:

**Before** (concern-first):
> The project has not clearly identified its regulatory target. Misinformation is a thorny problem...

**After** (strengths-first):
> The project addresses a genuine problem—the timing dilemma in technology regulation is real, and the insight that focusing on enduring values might provide more stable regulatory foundations is conceptually appealing. The backcasting workshops are methodologically creative... However, the pathway from theoretical framework to concrete recommendations would benefit from further elaboration.

### Lead with Distinctive Experience

Open paragraphs with what makes THIS candidate unique, not generic assertions:

**Before**:
> Strong candidate with a notable track record in digital forensics.

**After**:
> Dr Albright is a capable researcher with a strong track record in digital forensics and platform accountability. His work on Russian disinformation operations attracted significant attention and has had demonstrable policy impact—contributing to the Honest Ads Act and forcing Facebook to implement its Ad Library in response to his findings.

### Redundancy Avoidance

Don't repeat in Overall Comments what's already stated in criterion sections. If the same point appears in both places, either:
1. Remove it from criterion sections and save for Overall (if it's a cross-cutting theme)
2. Keep it in criterion sections and reference briefly in Overall ("As noted above...")
3. Fold the Overall section's content into the other criteria to avoid repetition entirely

### Measured Qualifiers

Use precise, measured language:

| Instead of | Write |
|------------|-------|
| "high confidence" | "reasonable confidence" |
| "exceptional" | "strong" |
| "seminal work" | "work that has been well received" |
| "eight times the expected rate" | "approximately eight times" |
| "zero transition risk" | "minimal transition risk" |

### Common Revision Requests

| Feedback | Action |
|----------|--------|
| "Too enthusiastic" | Dial down superlatives, use measured language |
| "Don't quote the application" | Remove quoted praise, replace with evaluative statements |
| "Expand this section" | Add substantive analysis, not padding |
| "Stay in my voice" | Re-read style guide, match sentence patterns |
| "Use their name" | Replace "the candidate" with name/title throughout |
| "Lead with strengths" | Restructure to acknowledge positives before concerns |
| "Too harsh" | Reframe with constructive language ("would benefit from") |
