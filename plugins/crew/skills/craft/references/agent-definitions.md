# Agent Definitions

Agent persona definitions establish persistent role identity, authority limits, and output contracts loaded on every turn (target 30-60 lines, hard ceiling 100 lines / <2,500 chars).

## Allowed Body Sections

Limit agent definition bodies strictly to these sections (omitting optional sections when unused by that agent):

1. **Identity/role**: 1-3 sentences defining the persona, eponymous grounding where present, and public-law office / scope of authority in the author's voice.
2. **Behavioral rules**: Concise, universal operational constraints and safety invariants framed through public-law concepts (office, jurisdiction, delegated authority, separation of powers, checks and balances) -- preserving authentic authorial voice rather than compressing skill mechanics into telegraphic bullet soup.
3. **Output schema**: Expected report structure and verdict states.
4. **Capabilities** _(optional; applied at runtime only when selected by the composed workflow)_: Clean capability-to-skill list or table without per-route narrative.

## Decoupling and Scope Rules

- **Cross-task generality**: A persona line applies to ANY task the agent performs. Anything specific to one skill lives in that skill, leaving at most a one-line capability pointer in the persona.
- **Name skills, not mechanics**: Name a skill the agent uses; leave its modes, arguments, and when each applies to the skill. A change to a skill's modes or arguments owes the agent definitions that use it no edit.
- **Role and entity abstraction**: Refer to the principal as "the user", use gender-neutral pronouns, and name models strictly by capability tier (`flagship`, `mid-tier`, `fast`) without naming concrete model variants or client harnesses.
