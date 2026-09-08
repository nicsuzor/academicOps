---
name: axioms
description: Provides the axioms that govern agent behavior from universal, user, and project scopes.
---

# Axioms

Axioms are packaged in three layers:

1. Universal axioms: Provided by this skill, in `./axioms/`.
2. Project local axioms: `$CWD/.agents/rules/*.md`.
3. User-specific axioms: stored in the `pkb`; use the MCP tool to search for 'type: axiom'.

## Layer dictates scope, not priority

- Axioms are universal truths. The cannot conflict and they cannot be modified or read down by other rules.
- If it is not possible to satisfy all axioms, the only option is to escalate to a rule-making process for review.
