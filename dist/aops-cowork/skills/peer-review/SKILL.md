---
name: peer-review
type: skill
description: >
  Peer review of research funding applications and academic submissions.
  Scheme-agnostic — fetches current criteria from the relevant handbook each
  round, since weights and language change. Covers Detailed Assessor and
  College-of-Experts / General Assessor roles, plus collegial draft review.
category: instruction
triggers:
  - "review this grant"
  - "review this application"
  - "future fellowship"
  - "DECRA"
  - "ARC assessment"
  - "ERC review"
  - "SNSF review"
  - "fellowship review"
  - "detailed assessor"
  - "general assessor"
  - "college of experts"
  - "process reviewer comments"
modifies_files: true
needs_task: true
mode: workflow
domain:
  - academic
allowed-tools: Read,Write,Edit,Grep,Glob,Bash
version: 2.0.0
permalink: skill-peer-review
---

# Peer Review Skill

**Purpose**: Run a peer review of a research funding application or academic submission, preserving the user's voice and producing evidence-based feedback that matches the _current round's_ scheme criteria.

**When to invoke**: User is assigned as a Detailed Assessor, a General Assessor / College of Experts member, or is reviewing a paper, thesis, or draft.

**Core stance**: Criteria, weights, scoring bands, and even rubric language change between rounds. **Do not assume the previous round's criteria still apply.** Always fetch the current handbook or guidelines first.

For role-specific nuance see [[reviewer-roles]]. For platform tips see [[platform-instructions]]. For taxonomy and scoring guidance see [[review-guidance]].

---

## Core Axiom: Evidence Over Opinion

Every score and every sentence of feedback must point to evidence in the application. "The methodology is weak" is not feedback; "The proposed survey instrument (Part C, p.4) does not specify sampling frame or recruitment strategy" is.

For collegial draft review (where the user provides the judgment), an additional axiom applies — **support, don't replace judgment**. The agent prepares materials, maps questions to text, drafts in the user's voice. The agent does not generate critique unless explicitly asked.

---

## Workflow

### 1. Intake & CoI Check

1. Read the assignment notice (email, RMS notification, etc.). Capture:
   - Scheme + round (e.g. FT26, DE27, ERC-ADG, SNSF Project)
   - Application ID, candidate, institution, title
   - **Role**: Detailed Assessor vs. General Assessor / CoE vs. collegial reviewer (see [[reviewer-roles]])
   - Deadline (and any platform's earlier soft deadline)
   - Min char/word counts per criterion (Detailed only)
2. **Declare CoI before reading**: institutional, personal, recent collaborator (typically last 4 years for outputs / 2 years for funding under ARC), supervisory, or financial. Re-check CoI when reading the participant list and references — collaborators may be named only deep in the application.
3. Create a task file `YYYYMMDD-{scheme}-{appid}.md` with the assignment context, deadline, and role.

### 2. Fetch Current Criteria

**Do not reuse criteria from a prior round**. Fetch the current scheme handbook or guidelines:

- **ARC** schemes: search PKB for the current handbook (e.g. `ARC-FT26-Assessor-Handbook`, `ARC-DE27-Assessor-Handbook`); else fetch from https://www.arc.gov.au/funding-research/peer-review/assessor-resources or via GrantConnect for the Grant Guidelines.
- **ERC**: call-specific evaluation guide.
- **SNSF**: scheme-specific assessor instructions in mySNF.
- **NHMRC**: peer review guidelines for the specific scheme + round.

Extract into the task or working notes:

- Criteria list, sub-elements, weights
- Any add-on criteria (e.g. ARC Indigenous research add-ons)
- Scoring scale + band descriptors + indicative distribution
- Char minimums (per criterion + overall)
- Submission platform + deadline
- Role-specific instructions (Detailed vs General Assessor differ — see [[reviewer-roles]])
- Anything new this round vs. last (compare with PKB notes from the previous year if any)

### 3. Materials Assembly

1. Download the application PDF + supporting parts. Store under `${ACA_DATA}/reviews/{scheme}/{appid}/`.
2. Convert to line-numbered text: `pdftotext -layout {input}.pdf source.txt`. This enables grep + line citations in notes.
3. Build a **section map** (table of section → line range) at the top of the working notes. This is the most useful single navigation aid for re-reads.
4. Generate a working assessment file from the criteria fetched in step 2 — see [[review-template]] for the structure to instantiate.

### 4. Initial Read & Reading Notes

One full pass, no scoring. Goal: understand the project, candidate trajectory, and ask. The output is a **reading notes** document at `~/brain/reviews/{scheme}/{appid}/YYYYMMDD-reading-notes.md` that:

- Maps every assessment criterion to specific line ranges in the source
- Records **basic factual claims** the application makes against each criterion (what it says it does, with line refs) — NOT yet judgments
- Flags `[?]` markers where claims need verification or where something is missing/inconsistent
- Surfaces structural anchors useful for re-read (RQs, aims, theoretical frame, methods phases, budget summary)
- Includes an anti-bias checklist tailored to this application

The reading notes are designed to be read alongside the source — keep both open. See [[reading-notes-format]].

### 5. Criterion-by-Criterion Assessment

For each criterion fetched in step 2:

1. **Locate evidence** in the application — quote or page-cite. Absent evidence is itself feedback.
2. **Categorise** each unit (see taxonomy in [[review-guidance]]):
   - **Scope**: specific text | section | document
   - **Type**: structural | methodological | substantive | clarity | citation | strategic-fit
   - **Direction**: strength | weakness | gap | concern
3. **Draft comment** to meet the round's char minimum. Lead with strengths, then material weaknesses, then minor concerns. Avoid hedging.
4. **Score** against the band descriptors fetched in step 2. Distribute realistically — don't drift toward the centre.

### 6. Quality Check

Before drafting overall:

- [ ] Each criterion comment cites the application (page, section, or quote)
- [ ] Scores are consistent with text — no "outstanding" prose with a B score
- [ ] No personal attacks; criticise the proposal, not the person
- [ ] Tone professional; for grants, slightly more supportive than for journal review (it's a funding decision)
- [ ] No suspected research-integrity breaches mentioned in assessor comments — route to the integrity office separately
- [ ] No restatement of the application; no comparison with other applications; no AI-generated text (per ARC policy)
- [ ] Char counts pass

### 7. Overall Assessment & Score

Synthesise: what makes this application competitive? What would have to change for it to be? The overall score is a judgment about whether this should be funded against the scheme's purpose, not a mechanical average.

### 8. Submission

1. Log in to the platform (RMS, EvalAccess, mySNF). Pre-flight char counts.
2. Paste, save frequently, submit. Capture confirmation.

### 9. Close-out

Update task to `[x] #status-done`; append final assessment to the task file; archive the review folder; note any patterns worth keeping in PKB.

---

## Scribe Mode (collegial drafts, not panel assessment)

For colleague drafts, theses, or letters where the user is providing the judgment:

1. **Assemble** materials in `${ACA_DATA}/reviews/[author]/`.
2. **Reading guide**: produce `YYYYMMDD-reading-notes.md` mapping the author's stated questions to specific line numbers / sections. Do NOT add your own critique.
3. **Scribe**: capture the user's reactions and draft feedback in their voice (terse, specific, no LLM hedging).
4. **Finalise**: append response to task file, mark complete, file in author folder.

---

## Critical Rules

- **Fetch criteria fresh each round.** Do not assume the previous year's criteria.
- **Match your role.** Detailed and General Assessor / CoE work differs — see [[reviewer-roles]].
- **Evidence-based.** Every claim points to the proposal.
- **CoI declared and re-checked** when participant lists and references are reached.
- **Voice.** For collegial review, match the user. Direct, specific, no effusive thanks.
- **No integrity allegations in comments.** Route to the scheme's integrity office.
- **No AI-generated assessment text** under ARC policy. The agent prepares notes and helps draft in the user's voice; the user owns the final text.

---

## References

- [[reviewer-roles]] — Detailed Assessor vs General Assessor / CoE vs collegial reviewer
- [[review-guidance]] — taxonomy, scoring bands, tone calibration, anti-bias
- [[review-template]] — generic assessment file structure (instantiate per scheme)
- [[reading-notes-format]] — reading notes layout that helps you read alongside the source
- [[platform-instructions]] — RMS, mySNF, EvalAccess submission tips
- PKB: search for `{scheme}-Assessor-Handbook` or `{scheme} Grant Guidelines` for the current round
