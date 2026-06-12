---
name: academic-grant-review
type: skill
description: >
  Conceptual review of scholarly work — grant applications, papers, theses, colleague drafts. A general analytical core for peer review. Produces evidence-mapped and double-checked preparatory materials;
  **academic owns all judgments and all submitted text**.
triggers:
  - "review this grant"
  - "review this application"
  - "review this paper"
  - "grant assessment"
  - "detailed assessor"
  - "peer review"
mode: workflow
domain: [academic]
---

# Academic grant review

Review the input material and produce:

- an evidence-mapped table of criteria and evidence
- a list of key critiques the academic may wish to consider
- a draft in the user's voice — never a finished review, never a score
- evidence that every claim you make has been double-checked by an independent agent

## The summary

First, produce a brief summary to help the user orient themsleves when reading the application. The summary should cover all important points relevant to the assessment criteria. Present the summary in brief dot points with references.

The summary should explain the entire reserach pipeline from:

- social benefit need;
- basic research questions;
- methods;
- theories for analysis;
- expected outcomes;
- impact and engagement strategies.

Also summarise the role of each member of the team and their key research track record relative to opportunity info.

## Hard rules

**Conceptual level only.** Comments engage the work's ideas, design, evidence, and feasibility. Never comment on grammar, spelling, typography, formatting, or copyediting — not in draft prose, not in dot points, not in "private notes". If you notice a typo, keep walking. The one exception is _substantive_ internal inconsistency — a budget that doesn't reconcile, a method that contradicts the timeline, a sample that can't support the claimed inference — which is in scope precisely because it bears on a criterion, not because it is an error.

**Evidence over opinion.** Every claim points at the source: quote or line ref. Convert the PDF with `pdftotext -layout` and treat line numbers as the citation currency. Absence of evidence is itself a finding, but claims of absence require a documented search. Always eyeball the original PDF pages for tables, GANTT charts, and budget grids — text extraction silently mangles exactly the content that decides feasibility.

- **Evaluate the research team relative to their opportunities for research.**
- **Always expect strong mentoring**: where relevant, examine researcher development and succession plan, over-reliance on casual or unfunded researchers. External grant funding should build capacity and provide the necessary support for research team development, particularly for early career researchers, and expecially for researchers from diverse, disadvantaged, and under-represented backgrounds.
- **CoI before reading.** Enumerate every participant and check for collaborators, institutional links, and funding relationships before substantive reading.

## Method

The sequence:

- generate a summary of the application for the user
- convert source to markdown and save
- build a section map (section → line ranges)
- factual reading notes per criterion with `[?]` flags, no judgment yet
- draft
- independent adversarial verification
- apply fixes
- hand over with a top-line summary
- user writes their own top-line read, scores, and final text

Reading notes are factual ("proposes 20 participants over 2 weeks", with line ref) — evaluation belongs in the draft, not the notes. Paraphrase with line refs rather than long quotes.

**Verification is not optional.** Commission a separate contextless agent to audit the draft against the source: every factual claim classified CONFIRMED (verbatim quote + line), UNSUPPORTED, or WRONG; claims of absence re-searched; arithmetic recomputed; then an independent gap analysis of what the draft missed. Fix everything it finds — and check the verifier's own corrections, which can be wrong in the same ways drafts are.

## The analytical probes

These are the questions that find what matters. Apply them with judgment, not as a checklist — most reviews turn on two or three of them.

The probe set itself is maintained as a **single source of truth** in the aops-core peer-review skill — **the eleven analytical probes** in [[aops-core/skills/peer-review/references/probes.md]] (permalink `review-probes`). Read the application against all eleven; that file carries each probe verbatim plus the PREP guidance on which probes most often surface the single largest vulnerability (1, 3, 4, 6), the feasibility/access pair (7, 9), and the anti-credulity check (5).

Do not work from a paraphrased or pruned subset here. An earlier distillation of this same set into "8 probes" silently dropped four analytical moves — conceptual-contribution-vs-descriptive, citation-integration, translation-pathways, institutional-commitment — which is exactly how analytical moves get laundered out. Keep all eleven; prune only by _adding_ probes your discipline needs, never by merging or dropping them. The inline examples in `probes.md` are a law / social-science reviewer's — read them as illustrations and substitute your own field's analogues.

## Voice

First person, warm, and constructive — always nice, never adversarial, calibrated in positivity to the academic's net call on the application. Emphatic praise is permitted and used when the evidence supports it ("an outstanding team", "an eminent authority", "a pre-eminent research centre", "the benefit case is strong"); don't flatten genuine enthusiasm into measured hedging. Strengths first, stated concretely from the evidence. Reservations are phrased as requests or advice, not verdicts: "I would have liked to see…", "I'd like to see more detail on…", "I would include contingency plans for…", "I would expect some statement of additional support from the institution…" — and close with an affirmation of capability where one is genuine ("I think the team are very capable of managing the project"). Short paragraphs, two or three per criterion; reservations woven in or placed at section end, easy to cut as a unit. No bullet lists in draft review prose: evaluative paragraphs only. No LLM tells. Balance depth across criteria roughly in proportion to their weights.

Phrases Nic has explicitly struck (growing list — add to it whenever he flags one): "sits squarely", "de-risks", "real substance under the…", "lines up against the design". Don't open alternating paragraphs with "However," — vary the turn ("My reservation here is…", "The budget documentation needs care, though.", or just state the concern directly). Don't reuse a signature evaluative word across reviews in the same round ("eminent" once per round, not once per application). Keep credential detail light in criterion-1 prose — one or two evidence items per investigator carries the judgment; the full inventory belongs in the orientation summary, not the review text.

The "X rather than merely Y" appraisal construction ("well grounded rather than merely asserted", "evidenced rather than decorative", "real collaborative history rather than a paper consortium") reads as GPT to Nic when repeated — at most one per review, and prefer stating the positive plainly: "The problem is real and the evidence for it is strong."

## Critique calibration

The analytical probes generate an inventory of vulnerabilities; the draft review text is not that inventory in prose form. Observed revision pattern across finals: the academic cuts most of the critique, keeps at most one or two reservations per criterion — sometimes none, when the application is strong and the silence is itself a scoring signal — and chooses _which_ reservations survive from the dot points. So:

- **Draft prose carries the academic's likely position, not the full case for the prosecution.** Lead each criterion with what the application does well. Include only the one or two reservations with the strongest claim to survive the academic's judgment, framed constructively. Everything else stays in the dot points and appendix, where the academic can promote it if their read is harsher.
- **Anchor reservations in the application's own promises.** Quote the application's framing (e.g. "a 'comprehensive digital platform accountability framework'") and ask whether the design delivers _that_ — not whether it meets an external standard the applicants never claimed. **Any phrase you put in quotation marks must be verbatim from the source — grep-confirm it before drafting.** A blended or approximated quote is the one error the applicants can catch by reading their own document, and it discredits the whole assessment; the final pre-submission round caught exactly this (a plausible framework phrase that appeared nowhere in the application). If you can't confirm the exact words, paraphrase without quote marks.
- **Never frame an early career researcher's record as a deficit.** Assess whether the project's structure supports and develops them; an ECR carrying a major component is a _strength_ when mentoring and support are evidenced. Direct continuity and resourcing critiques at institutions, not at the vulnerable researcher (institutions "are increasingly expected to better support researchers when co-investing in publicly funded research").
- **Preserve the academic's top-line hunches, including hedged ones.** A speculation marked "not sure" in their notes is often the most distinctive content in the final review, asserted confidently once they own it. Surface these in the draft; never silently filter them as too tentative.
- **The academic's Notes block is working space.** Raw impressions, questions, and self-corrections ("actually, no, I was too early with that critique") belong there and inform which draft reservations survive. Keep the slot in every draft; never tidy it.
- **Place each reservation under the criterion it really belongs to — and notice the weight that implies.** Doubts about whether findings will be useful or adopted are Benefit material, not Quality material, even when they originate in a methods observation (Nic moved the "nobody has best practices / effectiveness can't be measured" critique from Quality 45% to Benefit 15%, where it reads as a benefit-realisation risk rather than a design flaw). Ask of every reservation: which criterion does this actually score against?
- **State the conclusion of the analysis, not the audit trail.** Forensic detail dissolves in final text: a catalogue of D1/D2 budget contradictions became "there is a lot to do in this project and I'm worried that it might actually be a little under-resourced… as submitted it leaves some genuine uncertainty about how risks will be mitigated." The prep notes hold the particulars; the review states the judgment they support. This applies even to substantive internal inconsistencies — they justify the conclusion, they don't appear in it.
- **Concede before asking.** "The application counts 20+ ARC-funded projects and suggests there is still a gap to be filled, and I'm minded to agree, but I really think the project would benefit from…" — agree with the application's premise first, then make the ask. Understatement carries the critique: "with a bit more precision", "a little under-resourced", "a slight timing challenge".
- **One fact, one criterion.** Don't deploy the same evidence (a flagship precedent, a commissioned-work record) in two criteria; put it where it does the most work and let the other section generalise.
- **Answer your own critique when the answer is real.** After noting an absence, say whether fitting it in would even have been desirable: "Having said that, it's already a full program of work, and I don't think it's desirable to try to fit more in." This converts a deficit into a scoping judgment and signals fairness — the critique stands, but so does the applicant's trade-off.
- **Reserve points get promoted, so keep them sharp.** Nic lifted a private dot-point (lead CI's 0.2 FTE against a 50% teaching load) into final Feasibility text — reframed at the institution and wrapped in praise: "It is unfortunate that the host institution is not able to provide additional teaching relief for such a standout academic researcher." That's the promotion pattern: circumstances criticised, person praised, institution addressed.
- **Even supporting statistics leave the final prose.** The eSafety figures (48.2%, 432→2,852) backed a _positive_ point and still got cut to "Australian regulator data show sextortion is now the largest and fastest-growing category." The two-register rule applies to praise as much as critique.
- **When an ethical point is the reason, state it as the reason — and let it land last.** The draft cushioned a critique of field-erasing self-promotion with a procedural rationale ("assessors must be able to rely on track-record statements"); Nic deleted the procedural cushion and moved the ethical point to the paragraph's final sentence: "This matters beyond rhetoric: the claim of global pre-eminence writes over and erases the contributions of the women, including queer and Black women scholars, on whose work the field rests." Don't manufacture a 'safer' justification for a critique whose real ground is a value; and note the affirmation-closer is a default, not a rule — a section may end cold when the application's conduct warrants it.
- **Never ground a data-access critique in platform terms of service.** Nic rewrote "terms-of-service and audience-privacy questions" to "practical risk and privacy questions": his own scholarship opposes platform gatekeeping of research, so a review that faults researchers for ToS exposure would contradict his position. Critique data plans on practical feasibility and participant/audience privacy, not on deference to platform rules.
- **Render the academic's voice faithfully, including politically pointed language.** Nic restored "alt-right" and "jawboning" after the draft softened them. Don't pre-soften: write what the academic said, and raise any publication-register worry in conversation, not by silent substitution. Also describe expertise at the accurate level of generality ("regulation of digital technologies" where the broader field is the truth; "judicial bodies" where the citing courts include the CJEU) — and say why a credential matters for this project ("international networks that are fundamentally important here"), not just that it exists.

## Specificity: two registers

The preparatory materials and the draft review text run at deliberately different levels of specificity, and conflating them is a failure mode.

**Preparatory materials (summary, reading notes, critique dot points, appendices): maximally specific.** Names, numbers, dates, line refs, verbatim quotes. This is where every claim is pinned to the source, where the academic drills down, and where verification has something to bite on.

**Draft review text: the academic's overall position, at a level of generality they can stand behind from their own reading.** The submitted review reflects considered judgment, not a forensic audit, and the academic must be able to sign it without re-verifying a catalogue of particulars. Everything in it must still be supported — but strip dollar amounts, citation counts, sample sizes, contract dates, named outputs, and named Bills out of the draft prose unless the specific fact _is_ the critique (a budget that omits a whole cost category; an empirical base too small for the claimed inference). Prefer "a documented record of commissioned work taken up in regulatory processes" over the list of instances; the instances live in the prep notes as backup.

The test for any draft-review sentence: could the academic assert this confidently from one careful reading of the application, without checking a number? If not, generalise the sentence and move the detail to the appendix. Quote the application's own language sparingly, and only where the critique turns on its exact wording.

Pair the draft with an appendix block that maps each load-bearing general claim in the prose back to its specifics and line refs, so support is one lookup away if the academic is challenged or wants to sharpen a point.
