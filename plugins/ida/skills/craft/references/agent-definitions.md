# Agent Definitions

Agent persona definitions establish persistent role identity, authority limits, and output contracts loaded on every turn (target 30-60 lines, hard ceiling 100 lines / <2,500 chars).

## Allowed Body Sections

Limit agent definition bodies strictly to these four sections:

1. **Identity/role**: 1-3 sentences defining the persona and scope of authority.
2. **Behavioral rules**: Terse, universal operational constraints and safety invariants.
3. **Output schema**: Expected report structure and verdict states.
4. **Routing table**: Clean capability-to-skill mapping table without per-route narrative.

## Decoupling and Scope Rules

- **Cross-task generality**: A persona line applies to ANY task the agent performs. Anything specific to one skill lives in that skill, leaving at most a one-line capability pointer in the persona.
- **Name skills, not mechanics**: Name a skill the agent uses; leave its modes, arguments, and when each applies to the skill. A change to a skill's modes or arguments owes the agent definitions that use it no edit.
- **Role and entity abstraction**: Refer to the principal as "the user", use gender-neutral pronouns, and state required capabilities without naming model tiers or client harnesses.
