---
title: External & Cross-model Feedback
permalink: external-feedback
tags: [reference, peer-review, external-feedback]
---

# Integrating External / Cross-model Feedback

An optional side-stage, used when external review comments or a cross-model (e.g. another
LLM) pass arrive. Its honest, evidenced value is **distillation** of the academic's
analytical signature and **corroboration of emphasis** — _not_ new content. In the evidence
corpus the external-AI donor was ~95% redundant or circular, and the cross-model truth-check
ran off-screen with an unproven catch rate. So integrate with a hard **distrust default**,
and do not treat cross-model as the primary safety net — the in-loop adversarial VERIFY is
what demonstrably catches the BLOCKER.

## Distrust-default per-claim adjudication

Decompose the external comments into **atomic claims** and grade each against the
application (not against your draft's convenience):

- **TRUE** — supported by the application; verify the supporting evidence yourself.
- **PARTIALLY** — a kernel of truth, overstated or misdirected.
- **FALSE** — contradicted by the application.
- **OVERSTATED** — directionally right, too strong for the evidence.
- **NOT-FOUND** — references something not in the application.

Then decide **ADD / MODIFY / REJECT** for each, with a **one-line justification per verdict**.
REJECT is **not a safe harbour** — defaulting to blanket REJECT is its own failure mode;
MODIFY (concede a real strength in a clause while keeping the critique) is often the honest
call. Make yourself justify every REJECT in one line.

## The two-axis filter (truth is not enough)

The dangerous external comment is **not** the obviously false one — it is the **true-but-conflicting**
praise that, if folded in, would _reverse_ a weakness your draft reached. So grade every
claim on two axes, not one:

1. **Truth** — is it accurate against the application? (the table above)
2. **Redundancy** — is this already covered in the draft, _sharper_? If yes, REJECT as
   redundant even when true.
3. **Conflict** _(make this a required per-claim field — it is the one that catches the real
   threat)_ — **does this framing reverse a position we reached?** A true observation that
   recasts a weakness as a strength is a conflict. **Flag conflicts to the human; never
   silently resolve them.**

## Cross-model distillation (the proven use)

The reliable payoff of a cross-model pass is **extracting the academic's analytical signature**
— feeding the academic's past reviews to another model to surface the recurring probes and
voice, which then sharpen [[review-probes]] and the voice file. Treat a cross-model
_independent claim-check_ as an optional extra safety net layered **on top of** VERIFY, never
as a replacement for it. Be honest in the review record about which use you ran: distillation
and corroboration are evidenced; a final cross-model truth-check is reasonable but its
catch-rate is unproven here.

## Corpus-level note

A fingerprint or consistency problem that spans the _set_ of reviews is structurally
invisible to any single-application adjudication. If external feedback touches more than one
review, run the cross-document check as a **whole-set pass** (see the de-templating procedure
in [[voice-and-detemplating]]), not per-application silos.
