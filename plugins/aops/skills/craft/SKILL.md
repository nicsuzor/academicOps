---
name: craft
description: Authoring standard and quality gate for agent-facing instruction text. Use when writing, reviewing, or revising SKILL.md bodies, frontmatter descriptions, agent definitions, subagent prompts, or tool descriptions. Exclude for human-facing prose (specs, reports) or workflow templates.
allowed-tools: Read, Write, Edit
---

# Instruction Craftsmanship

Author and review agent-facing instructions for operational clarity and token efficiency. Consult `references/evidence.md` for empirical findings.

## First Principles

1. **Trust the harness, not today's quirks**: Write for durable capabilities. Avoid hard-coding workarounds for transient model behaviors.
2. **Specify process, not keystrokes**: State when to invoke a capability and what outcome proves it worked. Omit basic sub-steps or flags the agent already knows.
3. **One skill, one job**: Keep instructions focused on their singular purpose. Dispatch to peer skills rather than summarizing their internals.
4. **Verification must be real**: Demand direct inspection of live artifacts (outputs, logs, diffs) rather than relying on compliance checklists.
5. **Every line earns its place**: Relocate historical narratives, incident stories, and philosophical justifications to change records.

## The Deletion Test

Delete or relocate any line whose removal leaves the median task unaffected. Confine rare paths to progressive reference files.

## The Description Is the Router

Frontmatter descriptions are the primary routing surface (<1024 chars):

- **Front-load intent**: State the exact trigger conditions in the opening clause.
- **Define exclusions**: Explicitly state when not to invoke to prevent crossover.
- **Consolidate routing**: Place all triggering logic in the description field.

## The Body Is a Budget

Hold operational content strictly under 200 lines (target 30-80 lines):

- **Segment clearly**: Place critical constraints first or last; use markdown headers for navigation anchors.
- **Progressive disclosure**: Place dense reference materials or schemas one level deep in `references/`.
- **Provide shape, not logic**: Provide structural skeletons rather than full worked logic examples that induce overfitting.

## Voice

- Use positive imperatives paired with functional reasoning ("Use X because Y").
- Pair prohibitions with mandatory alternatives and legitimate escape hatches.
- Rely on document structure rather than capitalized absolutes ("ALWAYS", "NEVER").

## Agent Definitions

Limit agent definition bodies to:

1. **Identity/role**: 1-3 sentences defining the persona.
2. **Behavioral rules**: Terse operational constraints.
3. **Output schema**: Expected report structure and verdict states.
4. **Routing table**: Clean table without per-route narrative.

## Schemas and Construction

- Define strict schemas with `required` fields and `additionalProperties: false`.
- **Static prefix, variable tail**: Emit invariant template text first and append variable content at the end to maximize prompt caching.
