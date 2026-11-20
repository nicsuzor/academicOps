---
name: axioms
description: Provides the axioms that govern agent behavior from universal, user, and project scopes.
---

# Axioms

Axioms are packaged across three scopes:

1. Universal axioms: every `*.md` file in this skill's own directory except `SKILL.md` and `README.md`. Read them all; `README.md` indexes them.
2. Project local axioms: `$CWD/.agents/rules/*.md`.
3. User-specific axioms: stored in the `pkb`; use the MCP tool to search for 'type: axiom'.

## Scope does not weaken baseline axioms

- Axioms are universal truths. They cannot conflict and they cannot be modified or read down by other rules.
- If it is not possible to satisfy all axioms, the only option is to escalate to a rule-making process for review.
