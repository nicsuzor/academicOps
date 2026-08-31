---
alias:
- wf-blind-proof-wf-blind-proof
- wf-blind-proof
created: 2026-07-21T23:27:05.661604308+00:00
id: wf-blind-proof
last_modified: 2026-07-28T03:01:21.916798735+00:00
modified: 2026-07-28T03:01:21.916797312+00:00
permalink: wf-blind-proof
tags:
- wf-template
- v0.4
- module-f
title: wf-blind-proof
type: template
---

## What this step does

Demonstration protocol for proving a capability actually works, not just asserting it — three-role separation between the agent who writes the job, the agent who executes it, and the agent who grades it, plus durable evidence capture at run time. Composes [[wf-qa]]'s lock-criteria-before-evidence pattern (the VERIFIER role here IS a wf-qa pass) and sits on top of [[wf-verification]]'s floor. Use this when what's being proven is "does X actually work when nobody's coaching it" — a demonstration whose executor saw the pass-conditions is a biased test and proves nothing.

## Core Pattern — three roles, never collapsed

1. **DISPATCHER** — writes the job brief and separately locks the acceptance criteria (composing [[wf-verification]]'s "lock before evidence"). Brief and AC are two different documents from the start; the AC is never shown to the executor.
2. **EXECUTOR** — receives ONLY the job brief: what to do, what's out of bounds, and an explicit license to report inability rather than guess. Never receives: acceptance criteria, pass/fail thresholds, expected results, or the history of prior failed attempts. A brief that leaks any of these is not a blind test — restart with a clean brief.
3. **VERIFIER** — a separate agent (or the DISPATCHER, never the EXECUTOR) that holds the AC and grades the executor's actual output against it afterward, per [[wf-qa]]. Blindness has to be actively demonstrated, not just asserted — the verifier's writeup states what the executor's prompt did and did not contain.

## Evidence capture — at run time, not reconstructed

Before claiming PASS, archive verbatim, durably (a PKB doc plus files in the sessions archive — not solely in one agent's summary of itself):

1. The executor's actually-received prompt (not the AC, not a paraphrase).
2. The executor's full transcript (raw, not a curated excerpt).
3. The verifier's graded verdict, with citations into the transcript.

Post-hoc transcript recovery is unreliable — background-agent completions can land in whatever parent chunk happened to be open at dispatch time and never get archived separately. If evidence wasn't captured live, treat the run as unproven and re-run rather than reconstructing from memory or from a task's own summary of itself.

## Licensed honest failure

The executor's brief must explicitly permit failing or reporting inability (e.g. "CANNOT ANSWER — do not guess"). This is the one thing allowed to bias the test — toward honest failure, never toward a pass. Naming the expected result, the pass bar, or "this is being tested" in the same brief is never allowed.

## Failure is a first-class result

A FAIL is recorded as a real result, not smoothed over:

- Root-cause it (cite the actual defect, not a guess).
- Fix it through the normal task/PR loop — same as any other bug.
- Re-run the SAME protocol on a FRESH sample (different sessions/artifacts/inputs than the ones the failure was diagnosed on) — reusing the diagnosed sample lets the fix overfit to what was already inspected.

Only a fresh-sample re-run that PASSes closes the proof.

## Claim registers

Every claim in the proof record is labelled:

- **observed** — primary evidence checked directly by whoever is writing the record, with a citation (file, line, tool-call result).
- **reported** — asserted by another agent or document; state what verification (if any) has been done on it.

Before the proof is surfaced to the principal, an independent spot-check of a sample of the evidence happens — not just a re-read of the summary.

## Contest handling

If the principal challenges the proof:

1. Mark the record **CONTESTED**, with the challenge quoted verbatim (not paraphrased).
2. Resolution requires actually meeting the standard the principal is now holding you to — not re-arguing the old standard.
3. Retain the full audit trail (original claim, challenge, resolution) — never delete or overwrite the contested version; append the resolution below it.

## Principal-facing summary

The proof record leads with a plain-language summary readable in under a minute: what was tested, PASS/FAIL per item, and any disclosed gaps. Verbatim evidence (prompts, transcripts, citations) sits below it, for whoever wants to check the work — not interleaved with the summary.

## Routing signals

- "prove this actually works", "demonstrate", "show me it in action" — especially after an assertion-only claim has already been rejected.
- Any acceptance gate where the executing agent could game the result by being coached toward the answer.
- Re-proving a capability after a fix, where the original failure's sample must not be reused.

**NOT this gate**: routine PASS/FAIL QA where nobody's incentives are at stake in seeing the criteria → use [[wf-qa]] directly. Not a substitute for [[wf-outbound-review]] when the artifact itself is about to leave the team.

## When to Skip

- Low-stakes claims where an ordinary [[wf-qa]] evidence table already satisfies the principal.
- The principal has not asked for, and would not value, blind execution — composing this unasked is disproportionate process for a two-way-door claim.

## Declared stakes

Door-type is two-way per individual run (a FAIL sends the underlying capability back for a fix; it doesn't itself authorize a release) — but the accumulated proof record is often the gating evidence for a one-way door elsewhere (e.g. a release integration PR). Treat evidence-capture failures as blocking, not cosmetic.

## Anti-patterns

- Quoting the DISPATCHER's acceptance criteria and calling it "the executor's prompt" — these are different documents; the AC must never reach the executor.
- Reconstructing a transcript from a task's own summary of itself after the fact, instead of archiving the raw transcript live.
- Re-running a FAILed protocol on the same sample the failure was diagnosed on.
- Deleting or overwriting a CONTESTED record instead of appending the resolution.

---

Origin: generalised from the v0.4 acceptance proof protocol — see [[docu_36500cdb]] for the worked example (dispatch-topology table + blind re-run evidence per proof) and tracker [[aops-a9e6b48c]] Log entry "NIC CHALLENGE 2026-07-22" for the standard's canonical statement.
