---
name: pr-code
type: review-context
description: Context descriptor for code PRs — feature additions, bug fixes, refactors. Calibrates agent commission and quality bars for software changes.
---

# Review Context: Code PR

## When This Applies

A PR containing code changes — new features, bug fixes, refactors, test additions. May include config changes, dependency updates, or script modifications alongside code.

## Agent Commission

| Agent      | Commission?             | Rationale                                                                                                                                                       |
| ---------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ruth**   | Always                  | Axiom compliance: scope explosion, plan-less execution, authority violations are common in code PRs                                                             |
| **Pauli**  | When architecture moves | If the PR changes interfaces, data flows, error handling patterns, or adds new abstractions — commission Pauli. If it's a targeted fix with clear scope — skip. |
| **Marsha** | Always for code changes | Code claims require runtime evidence. Marsha must run tests, not just read them.                                                                                |

## Quality Bars

**Ruth must check:**

- P#5 (Do One Thing): Is the PR scoped or does it touch unrelated concerns?
- P#9 (Fail-Fast): Does new code handle errors explicitly or silently degrade?
- P#26 (Verify First): Are there assertions, not just assumptions, about preconditions?
- P#30 (Nothing Is Someone Else's): Does the PR own its test failures?

**Pauli (when commissioned) must check:**

- Is this the right fix, or is it patching a symptom?
- What class of change is this — does it create a pattern that will be repeated?
- What does this change make harder to do later?
- Negative space: what test cases are missing?

**Marsha must:**

- Run the test suite, not just read it
- Verify the specific behavior the PR claims to fix or add
- Check for regressions in adjacent code
- Note explicitly if runtime verification was not possible and why

## Sufficient

A code PR review is sufficient when:

- Ruth has no unresolved BLOCK or WARN
- Marsha has runtime evidence for the claimed behavior (or has explicitly named what she couldn't verify)
- Any architectural concern from Pauli is either resolved or flagged as a human decision

## Escalate When

- Marsha's tests fail and the cause is architectural, not mechanical
- Ruth returns BLOCK on a genuinely contested authority question
- Pauli identifies that the PR is fixing the wrong problem at the root level
