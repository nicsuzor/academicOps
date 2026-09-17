---
name: peer-review
description: Peer review of research funding applications and academic submissions. Scheme-agnostic; fetches round criteria dynamically. Covers Detailed Assessor, General Assessor / College of Experts, and collegial draft review.
---

# Peer Review

Prepare evidence-based, signable peer reviews matching current round criteria. The agent drafts and verifies; the academic owns scores, net call, and submitted text.

## Core Rules

- **Framing precedes defects**: Establish what the document aims to achieve before criterion-level critique.
- **Evidence-based**: Cite application locations (page, section, line, or quote) for every claim.
- **Documented absence search**: Treat missing elements as critique only after documented synonym search.
- **Fetch round criteria**: Retrieve current scheme guidelines, bands, and weights fresh each round.
- **Human owns judgment**: Leave scores blank in drafts to comply with funding-body GenAI policies.
- **No speculative outcomes**: Evaluate research feasibility without pre-committing what unrun studies will show.
- **Route integrity breaches**: Report suspected research-integrity issues through official scheme channels, never in assessment text (see [[platform-instructions]]).
- **Single living draft**: Maintain one draft per review versioned in git history; avoid duplicate version files.
- **Verbatim accuracy**: Use real, verified quotes or generic placeholders; never invent illustrative quotes.

## Five-Stage Workflow

Serial execution by a single agent is the default. Lead sessions with multi-review rounds may parallelise Stage 2 (isolated per-application verifiers) and Stage 3 (whole-set de-templating).

### Stage 0: Intake & Setup

1. Capture metadata: scheme, round, application ID, candidate, title, role ([[reviewer-roles]]), deadline.
2. Check conflicts of interest (CoI) once across participants and references; flag to academic for confirmation.
3. Fetch scheme criteria, score bands, and character limits from the current handbook.
4. Extract text to `${ACA_DATA:-~/brain}/reviews/{scheme}/{appid}/` via `pdftotext -layout`. Inspect tables and budgets directly from the PDF.

### Stage 1: PREP (Probe-Driven Draft)

1. Read against analytical probes ([[review-probes]]).
2. Produce reading notes ([[reading-notes-format]]) with two separated layers: line-mapped facts and a private raw judgment block.
3. Draft criterion comments aligned with scheme bands ([[review-guidance]]), leaving scores blank.
4. Self-check: verify arithmetic, confirm paraphrase is marked, and exclude integrity allegations.

### Stage 2: VERIFY (Adversarial Verification)

Execute an independent cold check per [[review-verification]]:

- Run quote-existence greps, recompute arithmetic with tools, and verify absence claims.
- Classify findings: CONFIRMED, UNSUPPORTED, or WRONG; assign severity (BLOCKER, FIX, NIT).
- Triage and apply fixes using narrow edits; verify diffs directly.

### Stage 3: Voice & De-template

1. Match the academic's voice and convert prep notes into signable prose per [[voice-and-detemplating]].
2. Run whole-set de-templating across all reviews in the round to eliminate repeated phrases and AI artifacts.
3. Ensure quote accuracy and evidence anchors remain unaltered.

### Stage 4: Final Check & Submit

1. Execute pre-ready gate: verbatim-quote grep, spelling check, and budget verification.
2. Boundary gate: verification applies to committed artifacts; post-verification edits require re-verification.
3. Academic reviews, assigns scores, and submits. Record confirmation in the task file.

## Scribe Mode (Collegial Review)

For pre-submission drafts by colleagues:

1. Store materials under `${ACA_DATA:-~/brain}/reviews/{author}/`.
2. Map author questions to line numbers in reading notes ([[reading-notes-format]]).
3. Budget feedback length to available time (lead with working elements, then one structural priority).
4. Quote the colleague's text directly rather than paraphrasing into labels.

## References

- [[review-probes]] -- Analytical probes for proposal evaluation
- [[review-verification]] -- Adversarial verification techniques and severity ladder
- [[voice-and-detemplating]] -- Voice registers and whole-set phrase deduplication
- [[external-feedback]] -- Distrust-default integration of external and model critiques
- [[reviewer-roles]] -- Detailed Assessor, General Assessor, and collegial reviewer scopes
- [[review-guidance]] -- Feedback taxonomy, scoring bands, and anti-bias drafting
- [[review-template]] -- Assessment markdown template
- [[reading-notes-format]] -- Factual map and raw judgment structure
- [[platform-instructions]] -- RMS, ERC, SNSF, and NHMRC submission guidelines
