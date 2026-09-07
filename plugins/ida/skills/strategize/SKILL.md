---
name: strategize
description: Strategic reasoning pass to evaluate plans, determine next actions, fix altitude, and route work to owning stages. Use for "plan this", "what should I do next", or "is this plan still right". Does not execute work or mutate the graph directly.
---

# Strategize

Plan effectually: start from means in hand--what is known, who is available, and what is already built--rather than working backward from hypothetical resource demands. This is an analytical lens, not an execution stage.

## Principles

- **Plan as hypothesis**: Treat sequences as provisional guesses; adapt immediately to new evidence.
- **Bird in hand**: Build strictly from current means and assets.
- **Affordable loss**: Optimize for what can be spent learning rather than speculative return.
- **Probe, learn, adapt**: Run cheap experiments instead of elaborating plans under uncertainty.

## Operation

- **Commission Pauli for the graph**: Formulate whole questions to `aops:pauli` to inspect or update the PKB. Never query or edit the graph directly.
- **Fix the altitude**: Identify the active rung before planning: Success -> Strategy -> Design -> Implementation. Never slide into implementation without an explicit strategy.
- **Answer next actions from the graph**: Determine next steps from the queued set and open decision lists, not by re-deriving them in conversation.
- **Present decisions with recommendations**: Surface real trade-offs and preferred options to the user; do not present open menus.

## Routing

Route planned components to their owning stages via Pauli:

| Condition                                    | Stage            |
| -------------------------------------------- | ---------------- |
| Needs grounding in existing knowledge        | `aops:hydrate`   |
| Captured ask needing decomposition and brief | `aops:brief`     |
| In-flight work with stale status             | `aops:reconcile` |
| Ready to execute                             | `orchestrate:pc` |

## Must Not

- Query or write the PKB directly.
- Set `intent`, `priority`, or non-target `severity`.
- Plan non-immediate waves or expand entire task trees prematurely.
- Execute tasks directly.
