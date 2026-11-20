---
name: craft
description: Authoring standard and quality checklist for agent-facing instruction text and workflow templates. Use when writing, reviewing, or revising SKILL.md bodies, frontmatter descriptions, agent definitions, subagent prompts, tool descriptions, or workflow templates. Exclude for human-facing prose (specs, reports).
allowed-tools: Read, Write, Edit
---

# Instruction Craftsmanship

Author and review agent-facing instructions, personas, and workflow templates for operational clarity, contract separation, instruction density, and token efficiency.

## First Principles

1. **Trust the harness, not today's quirks**: Write for durable capabilities; avoid workarounds for transient model behaviors.
2. **Specify process, not keystrokes**: State when to invoke a capability and what outcome proves it worked; omit sub-steps or flags the agent already knows.
3. **One component, one job**: Keep each component focused on a single purpose. Dispatch to peer skills rather than summarizing their internals; name hand-offs, never how another agent works.
4. **State the contract, not the neighbour**: Specify input and output contracts; never couple to specific neighbour slugs. Composing agents decide what fills each slot.
5. **Decouple persona from execution (Who vs How)**: Personas define identity, authority, and tone; skills define reusable execution recipes. Skills owned by one agent name that owner in one line and remain otherwise agent-agnostic.
6. **Progressive disclosure over monolithic injection**: Expose routing metadata upfront, load procedural bodies just-in-time, and offload dense references to on-demand files.
7. **Write for a headless worker**: Assume unattended execution with no human in the loop. Never pause or wait mid-task; end at approval boundaries and wire dependent work as blocked.
8. **Promise only what the executor delivers**: Output contracts list only artifacts and state the executing agent produces, never another party's subsequent act, sign-off, or user installation/deployment of a shipped release.
9. **Verification must be real**: Demand direct inspection of live artifacts (outputs, logs, diffs) rather than compliance checklists.
10. **Instruction density over conversational prose**: Maximize high-signal constraints per token; eliminate incident stories, post-mortems, and historical rationales.

## The Deletion Test

Delete or relocate any line whose removal leaves the median task unaffected. Confine rare paths and deep schemas to progressive reference files, and state current rules only.

## Persona vs. Skill Boundaries

Maintain strict separation between agent definitions and skill instructions:

1. **Agent Personas (The "Who")**: Persistent system instructions loaded on every turn (5-10% of base token budget). Define role identity (1-3 sentences), authority limits, behavioral postures, output schemas, and safety invariants. A persona line applies across any task; anything that applies only inside one skill lives in that skill (with at most one capability line in the persona).
2. **Skills (The "How")**: Modular, transient workflow packages loaded just-in-time. Define procedures, tool sequences, input/output contracts, and validation criteria.
3. **Linking and Decoupling**:
   - **Personas never inline skill mechanics**: Name available skills or tool access without prescribing internal steps, modes, or flags.
   - **Skills name an owner, never a persona's mechanics**: Define objective contracts executable by any capable agent. A skill one agent owns states that owner once (description and opening line); the procedure carries no persona-specific assumptions.

### Progressive Disclosure

Structure skill packages in three tiers:

- **Level 1 (Router)**: Frontmatter `name` and `description` loaded into the system prompt.
- **Level 2 (`SKILL.md`)**: Operational procedure loaded just-in-time, keeping structural shapes inline and median paths within the 30-80 line budget.
- **Level 3 (`references/`, `scripts/`)**: Exhaustive schemas or off-median branches stored one directory deep. Load via imperative procedural routing (`If <condition>, read references/<file>.md before <action>`), never passive suggestions ("see...").

## Type-Specific References

- If authoring or reviewing a workflow template, read `references/workflow-templates.md` before writing.
- If authoring or reviewing an agent definition, read `references/agent-definitions.md` before writing.

## Length Budgets by Instruction Type

| Instruction Type | Target Length | Hard Ceiling | Contents & Placement |
| :- | :- | :- | :- |
| **Agent Persona** | 30-60 lines (~200-500 tokens) | 100 lines (<2,500 chars) | Role identity, behavioral boundaries, safety invariants, output schema. |
| **Skill Description** | 1-3 sentences (150-400 chars) | 1,024 chars | Frontmatter router: trigger conditions, primary domain, explicit exclusions. |
| **Skill Body (`SKILL.md`)** | 30-80 lines (~400-1,000 tokens) | 150-200 lines (~1,500 tokens) | Step-by-step procedure, input/output contract, verification check. |
| **Workflow Template** | 30-60 lines | 100 lines | High-level stage composition and handoff contracts. |
| **Tool Description** | 150-400 chars | 800 chars | Purpose, when to use, when NOT to use, argument constraints. |
| **Reference File (Level 3)** | 50-150 lines | 300 lines | Modular single-topic technical documentation or schemas. |

## The Description Is the Router

Frontmatter descriptions are the primary routing surface (150-400 chars, ceiling 1,024 chars). Consolidate all triggering logic in `description` (avoid non-portable fields such as `when_to_use`) using an affirmative-first structure:

1. _Core Capability_: Active imperative stating primary domain and outcome (>=75% of budget on positive capability and triggers).
2. _Trigger Conditions_: Explicit phrases, asks, and contexts where the skill applies.
3. _Contrastive Exclusions_: Terse negative boundaries naming the peer alternative (`Exclude for X (use Y)`), avoiding speculative negative lists that dilute matching.

## Body Structure, Density, and Schemas

Hold operational content under the 150-200 line ceiling (target 30-80 lines):

- **Structural anchoring & caching**: Place critical invariants first and stopping rules at the start or end (U-shaped attention); emit static rules/templates before variable tail content to maximize prompt caching.
- **Shape, not logic**: Provide structural skeletons rather than exhaustive worked examples; define strict schemas with `required` fields and `additionalProperties: false`.
- **Positive imperatives with functional reasoning**: Frame rules around what to do ("Use X because Y"), pairing any prohibition with its mandatory alternative. Strip conversational padding.

## Quality Standards

Every agent instruction, skill, persona definition, and subagent prompt must pass these six checks before merging:

1. **Categorical generality (Categorical Imperative)**: Express rules covering the full class of situations; prohibit hyper-specific quotas, rigid interaction numbers, or one-off fixes.
2. **Entity abstraction (Name the process, not the actor)**: Refer to the principal as "the user", never by a personal name; refer to collaborators by role or capability.
3. **No PKB leakage (Data Boundaries)**: Never include private PKB IDs (`aops_...`, `task_...`, `mem_...`, `kb_...`) or Obsidian wikilinks (`[[...]]`) in distributed instructions; use standard relative markdown links.
4. **Zero historical provenance (CURRENT STATE ONLY)**: Eliminate incident stories, post-mortem recaps, changelog citations, and historical `sources:` arrays; state only what is true now.
5. **Adjudication against empirical evidence**: If an instruction design choice or length budget is contested during review, read `references/evidence.md` and cite its empirical findings.
6. **Model, tier, and harness agnosticism**: Shipped instructions name no model, tier, or harness variant; state the capability required (e.g., cheapest subagent able to complete the task vs. high-reasoning synthesis), leaving deployment-specific model/harness mappings to deployment configuration.
