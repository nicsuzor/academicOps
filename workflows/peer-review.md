# Peer Review Workflow

Structured peer review for grant or fellowship applications with bot-assigned subtasks for parallel processing.

## Inputs

1. **Assessment package** - Zip/folder with application PDFs
2. **Scheme identifier** - e.g., "ARC FT26"
3. **Parent task ID** - Task to nest reviews under
4. **Workspace path** - Default: `data/reviews/<scheme-slug>/`

## Phases

### Phase 1: Setup
- Create workspace folders
- Download/locate assessment criteria
- Generate review template from criteria structure

### Phase 2: Task Scaffolding
For each application, create 3 bot-assigned subtasks:
- Transcribe (PDF → markdown)
- Draft Review Doc (factual responses to criteria)
- Initial Observations (evidence against criteria)

### Phase 3: Execution (Bot Tasks)
Workers process subtasks autonomously using templates and criteria.

### Phase 4: Composition (Human + Agent)
Human drafts assessment comments, agent assists with redrafting in reviewer's voice.

## Composition Principles

| Principle | Guideline |
|-----------|-----------|
| **Tone** | Professional positive, measured not effusive |
| **Voice** | Evaluate claims, don't restate them |
| **Structure** | Balance depth across all sections |
| **Style** | Apply reviewer's style guide if available |
| **Naming** | Use candidate's name/title, never "the candidate" |
| **Concerns** | Frame as opportunities ("would benefit from") |
| **Critical assessments** | Lead with genuine strengths before concerns |

## FT26-Specific Patterns (ARC Future Fellowships)

### Tone Calibration
**Avoid effusive language**. Replace superlatives with measured assessments:
- ❌ "Seminal", "exceptional", "outstanding" (overused)
- ✅ "Strong track record", "demonstrates capacity", "well-positioned"
- ❌ "World-leading breakthrough"
- ✅ "Addresses an important gap in the field"

**Measured confidence, not certainty**:
- ❌ "Will transform the field"
- ✅ "Has potential to contribute significantly"
- ❌ "Demonstrates unparalleled expertise"
- ✅ "Track record that few in this field can match"

### Evaluative vs Descriptive Writing
**Don't list metrics—interpret their significance**:
- ❌ "149 publications, h-index 47, ranked 14th globally"
- ✅ "Publication record places them among leading researchers in this field"
- ❌ "6 pieces of legislation, 3 court citations"
- ✅ "Demonstrated track record of translating research into legislative change"

**Focus on what evidence shows, not what it is**:
- ❌ Bullet lists of achievements
- ✅ Narrative synthesis showing patterns and significance

### Structure and Balance
**Lead with context, then assessment**:
1. What is being evaluated (project/track record)
2. Strengths with specific evidence
3. Concerns or limitations (if any)
4. Overall judgment

**Balance section depth**. Avoid:
- Multi-paragraph investigator sections with thin 2-line benefit sections
- All detail in one criterion, perfunctory treatment elsewhere

**Reservations belong at section end**:
- ❌ Concerns scattered throughout
- ✅ "My only reservation is..." after establishing strengths

### Evidence Selection
**Concrete examples over generalizations**:
- ❌ "Strong policy impact"
- ✅ "Research cited 65+ times in Interactive Gambling Act Review"
- ❌ "International standing"
- ✅ "Only non-UK member of GambleAware Advisory Board"

**Link claims to consequences**:
- ❌ "Has advisory board"
- ✅ "Advisory board spanning ACTU, AHRI, AHRC positions research to reach policymakers"

### Voice Consistency
**Maintain measured professional tone throughout**. Avoid:
- Oscillating between enthusiasm and skepticism
- Cheerleading in some sections, harsh scrutiny in others
- Use "would benefit from" rather than "lacks" or "fails to"

**Frame limitations constructively**:
- ❌ "The methodology is thin and underspecified"
- ✅ "The application would be stronger with more implementation detail"
- ❌ "This is a fatal flaw"
- ✅ "This is a concern, though the staged design appropriately mitigates risk"

## Common Revision Requests

| Feedback | Action |
|----------|--------|
| "Too enthusiastic" | Dial down superlatives |
| "Don't quote application" | Replace with evaluative statements |
| "Use their name" | Replace "the candidate" with name |
| "Lead with strengths" | Restructure positives before concerns |
| "Too harsh" | Reframe with constructive language |
