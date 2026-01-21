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

## Common Revision Requests

| Feedback | Action |
|----------|--------|
| "Too enthusiastic" | Dial down superlatives |
| "Don't quote application" | Replace with evaluative statements |
| "Use their name" | Replace "the candidate" with name |
| "Lead with strengths" | Restructure positives before concerns |
| "Too harsh" | Reframe with constructive language |
