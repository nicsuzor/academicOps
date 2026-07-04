# Decomposition Quality Rubric

What a thoughtful decomposition surfaces, beyond a well-formed task tree. Used to
score decompose-mode output — by the [[decompose]] workflow's step 3.5
("Interrogate the task's epistemics", a three-question distillation applied
during live decomposition) and by `/dogfood` when testing decompose-mode
instructions (blind-test method:
[[../../../../.agents/skills/dogfood/references/decomposition-eval.md]]).

The test is not string-matching a gold standard ("not deterministic
deconstruction"). It is whether the same _kinds_ of considerations surface. Two
classes:

- **Scaffolding** (table stakes — the skill drills these): D1 spec-first, D5
  GitHub issues, D8 approval gate, D11 unified PR + review.
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

A dimension counts as SURFACED only if the planner _reasoned its way to the
consideration_ — not if a generic step merely brushed it.
