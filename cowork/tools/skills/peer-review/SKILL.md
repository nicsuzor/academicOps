---
name: peer-review
description: 'Peer review of research funding applications and academic submissions. Scheme-agnostic — fetches current criteria from the relevant handbook each round, since weights and language change. Covers Detailed Assessor and College-of-Experts / General Assessor roles, plus collegial draft review.

  '
---

# Peer Review Skill

Prepare peer reviews of research funding applications or academic submissions, matching
the current round's scheme criteria and producing evidence-based, signable feedback. The
agent prepares and verifies; **the academic owns the scores, the net call, and the final
submitted text.**

Run it as an adaptive loop of five stages, not a pipeline ending in a self-check: its
failures happen at the seams — a polish pass promoting a paraphrase into a fabricated quote,
a voice rewrite dropping a verified correction.

## Core Rules

- **Framing Precedes Defects**: Before any criterion-by-criterion pass, establish what the
  document is trying to be and whether that is the right thing to be. The highest-value
  points live here and cannot be reached by probing against criteria.
- **Evidence-Based**: Every claim must cite the application (page, section, line, or quote).
- **Absent Evidence Is Feedback**: A missing required element is a scoreable weakness, not
  an omission to skip silently — but say where you looked (a documented grep with synonyms),
  never assert an absence you didn't search for.
- **Fetch Round Criteria**: Fetch the current scheme guidelines (ARC, ERC, SNSF, NHMRC) for
  _this_ round. Weights, bands, and character minimums change; do not reuse prior criteria.
- **Human Owns Judgment**: Scores, top-line read, net call, and submitted text are the
  academic's. The agent prepares evidence-mapped drafts with **scores left blank**. This is
  how funding-body GenAI policies (e.g. ARC's ban on AI-generated assessor text) are
  satisfied _structurally_ — not by refusing to help draft.
- **Never Pre-Commit the Author's Results**: Do not propose a finding, headline claim, or
  framing asserting what an unrun study will show — suggest evaluating how well something
  works, never demonstrating that it fails. An integrity rule, not a style preference.
- **No Integrity Allegations in Comments**: Route suspected research-integrity breaches to
  the scheme's integrity office separately (see [[platform-instructions]]).
- **One Living Draft in Git**: One draft per review, versioned by **git history** — no
  `-v2` / `-v3` files, no carried-forward appendix. Cut critique lives in the history, not
  in a growing reserve block (see [[review-template]]).
- **Every Worked Example Verbatim-True**: Any example in these skill files that quotes an
  application must be a real, grep-checked string. A fabricated "illustrative" quote in the
  doctrine is how the doctrine teaches the bug. Generic placeholders (`"{quoted phrase}"`)
  are fine; invented specifics are not.

## Execution model — serial core, parallel optional

The loop is written so **one agent can run it alone, in series**, wearing each stage as a
hat (read the stage's reference file → do the stage → move on). That is the portable
default; it needs no fleet infrastructure.

When you have many reviews in a round **and** the infrastructure to fan out, two stages
parallelise — in _opposite_ directions:

- **VERIFY silos**: one independent, contextless verifier **per application** — isolation
  prevents cross-contamination. Prefer a _fresh_ sub-agent for VERIFY even in serial mode;
  an agent verifying its own draft is a weaker adversary than a cold reader.
- **DE-TEMPLATE is whole-set**: a single pass over the _entire round's_ drafts at once —
  fingerprints only exist across documents.

**Dispatch constraint.** Fan-out is a privilege of a top-level / lead session. If this
skill is itself running inside a leaf sub-agent, it **cannot** fan out a verifier panel —
fall back to the serial hat-switch, or escalate to the caller that a panel needs a
top-level session.

## The five-stage loop

The number of passes is **not fixed** (informal iteration): a clean application may need
one VERIFY cycle; a contested one several. Exit a stage when its checks pass, not after a
prescribed count.

### Stage 0 — Intake & setup (once per round)

- Capture the assignment: scheme/round, application ID, candidate, institution, title,
  role (Detailed vs General Assessor / CoE vs collegial — see [[reviewer-roles]]), deadline.
- **CoI scan, once.** Scan participant lists and references for institutional, personal,
  collaborator, supervisory, or financial relationships → **declare** → carry the result as
  a one-line header flag, then drop it. Do not re-litigate CoI every turn. The single
  residual that _must_ recur: "confirm against your own records" — the scan cannot see
  private collaboration history (see [[reviewer-roles]]).
- **Fetch this round's criteria, weights, bands, and character minimums fresh** from the
  handbook (PKB or the scheme site). Do not reuse last round's.
- Assemble materials under `${ACA_DATA:-~/brain}/reviews/{scheme}/{appid}/`. Convert:
  `pdftotext -layout source.pdf source.txt`. **Honest tooling note:** `-layout` gives
  layout-preserved text, **not** line numbers, and it **mangles tables / GANTT / budget** —
  read those from the PDF pages directly. Build a section→line map in the reading notes.

### Stage 1 — PREP (probe-driven draft)

Read the application against the **analytical probes** ([[review-probes]]) and produce two
deliberately separated things ([[reading-notes-format]]):

- a **factual, line-mapped notes file** (where-to-look + the application's claims, line-cited); and
- a **raw judgement block** — your actual hunches and reservations, kept verbatim and
  _never tidied_, quarantined from submission text. This is where the real assessment
  forms; bless it as first-class, do not sanitise it into blandness.

Then draft evidence-cited per-criterion comments applying the probes, following the scheme's
bands ([[review-guidance]]). **Scores left blank.**

**PREP self-review before finishing** — PREP is the weakest self-checking link:

- No integrity-adjacent or third-party-identifying material in prose (route separately).
- **Recompute any number before asserting it** — never quote a total you haven't re-derived.
- **Mark paraphrase as paraphrase.** Never write a phrase a downstream reader could mistake
  for a quotable string. This is the exact seed of a fabricated quote. Do not dress a guess
  as a fact with a `[?]`.

### Stage 2 — VERIFY (adversarial, independent) — the highest-value stage

Run as a **separate contextless pass** (fan-out) or an explicit, forceful hat-switch, and
run it as [[review-verification]] is written — the six techniques, the claim-by-claim
classification, the independent gap analysis, and the BLOCKER / FIX / NIT ladder. Never
degrade it to a citation-check of the draft's own claim list.

### Stage 3 — VOICE & DE-TEMPLATE

Convert the **verified** draft into clean, signable prose in the academic's voice, as
[[voice-and-detemplating]] is written — two registers, render boldly, the voice-onboarding
loop, and the whole-set de-template pass when the round holds more than one review.

Its one stage-level bound: cut to roughly one reservation per criterion, framed
constructively and anchored to the application's own promises.

### Stage 4 — FINAL-CHECK & submit

- **Pre-"ready" gate:** verbatim-quote grep + spell + dash-normalise +
  budget-recompute must pass **before** a draft is called ready. The final check confirms;
  it must not be the first place anyone greps a quote.
- Run a final contextless confirmation pass (the VERIFY techniques as a safety net).
- **Boundary gate — the most important structural rule:** _"verified" attaches to a
  committed artifact, not an idea._ Any regeneration after VERIFY — a voice rewrite, a
  polish pass, a hand-edit — **re-enters verification**. Stamp the verified commit; re-run
  the checks on any later diff. On-disk drafts are mutable and get rewritten post-hoc, so
  the committed, verified artifact is the record, never a live draft.
- The academic owns scores, top-line read, net call, and submission. Submit; save the
  confirmation to the task file.

### Side-stage — Integrate external / cross-model feedback (optional)

When external or cross-model review comments arrive, integrate them with a **distrust
default** ([[external-feedback]]): per-claim adjudication, a two-axis filter (is it already
covered, sharper? does its framing reverse a position we reached?), and a one-line
justification per ADD / MODIFY / REJECT. Cross-model's proven value is **distillation** (of
the academic's analytical signature) and corroboration of emphasis — not new content. A
final cross-model truth-check is reasonable but optional, not the primary safety net.

## Scribe Mode (collegial drafts)

For reviewing draft papers / proposals written by colleagues before submission:

1. Assemble materials under `${ACA_DATA:-~/brain}/reviews/{author}/`.
2. Generate reading notes ([[reading-notes-format]]) mapping the author's questions to line
   numbers, plus a raw judgement block.
3. Draft feedback in the academic's voice ([[voice-and-detemplating]]). The author is in the
   room — be direct but constructive; the academic provides the judgment, the agent supports.
4. Budget length by the author's remaining time, not by your thoroughness — ask or infer
   how long they have; a day left means about a page. Volume reads as thoroughness to the
   writer and as noise to the reader.
5. Lead with what works, then the one structural idea, then detail — enthusiasm first, one
   big idea, done.
6. Never paraphrase what the academic previously said into a label — check the primary source
   and quote their words.

## References

- [[review-probes]] — the analytical core: the probes PREP reads the application against
- [[review-verification]] — the adversarial VERIFY stage: techniques, severity ladder, self-verify
- [[voice-and-detemplating]] — two registers, voice onboarding, whole-set de-templating
- [[external-feedback]] — integrating external / cross-model comments, distrust-default
- [[reviewer-roles]] — role distinctions (Detailed vs General Assessor vs collegial vs journal)
- [[review-guidance]] — taxonomy, scoring bands, score–text alignment, anti-bias drafting discipline
- [[review-template]] — assessment file template
- [[reading-notes-format]] — reading-notes layout (factual notes + raw judgement block)
- [[platform-instructions]] — submission platform tips; integrity / foreign-affiliation routing
- PKB (optional): search for `{scheme}-Assessor-Handbook` or `{scheme} Grant Guidelines`;
  if no PKB, fetch the handbook from the scheme's site each round.
