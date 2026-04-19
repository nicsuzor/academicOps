---
name: pr-framework
type: review-context
description: Context descriptor for framework PRs — changes to skills, agents, hooks, enforcement, workflow infrastructure. Higher stakes than code PRs; architectural and axiom questions are central.
---

# Review Context: Framework PR

## When This Applies

A PR that modifies the framework itself — skills, agents, hooks, enforcement maps, workflow infrastructure, gate logic, context loading. This includes changes to agent definitions, skill SKILL.md files, the universal axioms, hook routing, or plugin manifests.

Framework PRs are higher stakes than code PRs. They shape how all future work gets done. A bad agent definition compounds. A broken hook fires on every session. A removed axiom weakens the whole enforcement model.

## Agent Commission

| Agent      | Commission?           | Rationale                                                                                                             |
| ---------- | --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Ruth**   | Always                | Framework changes can alter enforcement itself — Ruth must verify the change doesn't undermine axiom compliance       |
| **Pauli**  | Always                | Framework changes require systems thinking: what does this enable, what does it foreclose, what compounds?            |
| **Marsha** | For hook/gate/runtime | If the PR touches hooks, gates, CLI commands, or anything with runtime behavior — Marsha must verify it actually runs |

## Quality Bars

**Ruth must check:**

- P#5 (Do One Thing): Is the framework change scoped, or is it a grab-bag?
- P#99 (Delegated Authority Only): Does the new skill/agent/workflow stay within its granted authority?
- P#31 (Acceptance Criteria Own Success): Does the PR define how to know if the change worked?
- Does the change weaken any existing enforcement? If axioms or gates are touched, is the intent to relax or strengthen?

**Pauli must check:**

- Is this solving the right problem, or papering over friction that indicates a deeper design issue?
- What does this change make harder to do? What patterns does it encourage?
- Negative space: what edge cases in framework behavior is this not handling?
- Systems view: how does this interact with the hook system, the gate system, the skill discovery system?
- Does this increase or decrease framework complexity? Is the complexity earned?

**Marsha (when commissioned) must:**

- Run the hook or gate in a session context, not just read the code
- Verify the skill is discoverable (triggers work, context loads)
- Check that the change doesn't break existing behavior
- For agent definitions: verify the agent can be commissioned and produces parseable output

## Sufficient

A framework PR review is sufficient when:

- Ruth has no unresolved BLOCK on enforcement integrity
- Pauli has assessed the systemic implications, not just the local change
- If hooks/gates are touched: Marsha has runtime evidence
- The review has evaluated what this change makes HARDER, not just what it enables

## Escalate When

- Pauli identifies that the PR changes a foundational pattern in a way that affects multiple systems
- Ruth's reading of the axioms conflicts with the PR's stated intent (e.g., the PR claims to enforce P#5 but Ruth reads it as violating P#5)
- The PR weakens enforcement in a way that requires human authorization
- James cannot reconcile Pauli's architectural concerns with the PR's design goals
