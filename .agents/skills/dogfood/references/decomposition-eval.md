# Evaluating decomposition quality (a dogfood application)

A reusable way to test whether a planner — or any decompose-mode instruction set —
_critically thinks through the constituent components of a high-level abstract task_,
not just whether it produces a well-formed task tree. This is `/dogfood` (delegated
instruction testing) pointed at the planner's decomposition instructions.

## Method

1. **Pick a pair.** A one-line abstract request + a **gold-standard decomposition** —
   ideally the requester's own "how I actually wanted this broken down", captured from
   real work. The gold standard's value is that it encodes _real intent_, not a
   constructed test.
2. **Blind the agent.** Give a contextless agent the _real_ planner skill + the one-liner
   ONLY. It must not see the gold standard (or blindness is lost — see "fresh pairs"
   below). Have it produce the decomposition as a proposal (no PKB writes).
3. **Write your hypothesis down first**, then score against the rubric, citing the output.
   A dimension counts as SURFACED only if the planner _reasoned its way to the
   consideration_ — not if a generic step merely brushed it. (Recording the hypothesis
   before you read the output is what lets you discover you were wrong.)
4. **Review independently.** A second agent (e.g. pauli) scores from scratch — withhold
   your own scores so its read is its own.
5. **If you edit the skill, re-run blind and re-score the delta. Run ≥2 per condition** —
   a single before/after cannot separate the edit's effect from agent variance.

## The epistemics rubric

Score against the planner's decomposition quality rubric
(`aops-core/skills/planner/references/decomposition-quality-rubric.md`) — the
D1–D11 dimension table and the scaffolding/critical-thinking split live there,
not here, since it's decomposition-quality guidance the planner skill owns; this
file owns only the blind-test method around it.

## Fresh pairs, not a kept fixture

**Do not enshrine one example as a standing blind regression test.**

- **Contamination:** the moment a gold standard is written to the PKB (or anywhere the test
  agent can search), a future "blind" run is no longer blind. Keep the _methodology_ durable;
  treat each _gold-standard pair_ as single-use, stored where the test agent can't reach it.
- **Over-fitting:** a single fixed target invites tuning the skill to ace that case rather
  than the general faculty.

Capture pairs opportunistically from real work. If you want a standing bank, make it
_several diverse_ pairs treated as calibration snapshots, not a pass/fail gate.

## Worked example (2026-06-04 — non-blind illustration only)

**Request:** "Find the most frustrating and trickiest issues with the aops framework that
can only really be addressed by qualitatively applying generally expressed rules, and create
an initial implementation of the Claude Code 'auto' mode classifier (max 1–3 rules)."

**What the gold standard surfaced that a baseline planner missed:** the
rejected-as-too-brittle-PR evidence signal (D6), recent daily-note frustrations (D4), the
transcript-instrumentation prerequisite for evaluating the classifier (D9), and an
explicitly _non-mechanical_ test plan for a qualitative artifact (D10).

**Result:** scoring a blind decomposition exposed exactly that cluster — strong structure,
weak task-epistemics. The fix (planner `decompose.md` step 3.5 "Interrogate the task's
epistemics") closed D4/D6/D9/D10 on a blind re-run (N=1; PR #1594). This pair is retained as
illustration only — it is now contaminated by appearing here, so it is _not_ a blind fixture.
