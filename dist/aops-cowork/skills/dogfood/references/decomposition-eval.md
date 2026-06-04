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

The test is not string-matching the gold standard ("not deterministic deconstruction").
It is whether the same _kinds_ of considerations surface. Two classes:

- **Scaffolding** (table stakes — the skill drills these): D1 spec-first, D5 GitHub issues,
  D8 approval gate, D11 unified PR + review.
- **Critical-thinking** (the real target): D2, D3, D4, D6, D7, D9, D10.

| #   | Dimension                                    | What a thoughtful decomposition surfaces                                                             |
| --- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| D1  | Spec-first / define-before-build             | Write the spec first, grounded in existing docs; make the artifact's purpose explicit                |
| D2  | Negative scoping as the core constraint      | Reserve the mechanism for what it is _for_; exclude what's already handled — and say why             |
| D3  | Architectural registration                   | Register a new element in the system's self-description (maps, pyramid, index docs)                  |
| D4  | Evidence: lived/recent signal                | Mine recent daily notes / lived frustration, not only distilled corpora                              |
| D5  | Evidence: formal/tracked signal              | Review GitHub issues                                                                                 |
| D6  | Evidence: the DIAGNOSTIC negative signal     | Rejected-as-too-brittle PRs / reverts — the highest-signal source for "what only judgment can catch" |
| D7  | Track the negative space                     | Record candidates you are _not_ actioning so they aren't dropped                                     |
| D8  | Human approval at the right point            | Surface high-blast-radius / values calls; don't over- or under-surface                               |
| D9  | Observability / instrumentation prerequisite | You cannot evaluate a gate whose decisions aren't instrumented — build the visibility first          |
| D10 | Verification matches artifact nature         | A qualitative artifact needs observational / boundary-probing tests, not mechanical pass/fail        |
| D11 | Unified delivery + review-improve loop       | One PR, reviewed, then improved                                                                      |

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
