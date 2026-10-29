---
name: craft
description: Authoring standard and quality gate for agent-facing instruction text and workflow templates. Use when writing, reviewing, or revising SKILL.md bodies, frontmatter descriptions, agent definitions, subagent prompts, tool descriptions, or workflow templates. Exclude for human-facing prose (specs, reports).
allowed-tools: Read, Write, Edit
---

# Instruction Craftsmanship

Author and review agent-facing instructions, personas, and workflow templates for operational clarity, contract separation, instruction density, and token efficiency.

## First Principles

1. **Trust the harness, not today's quirks**: Write for durable capabilities. Avoid hard-coding workarounds for transient model behaviors.
2. **Specify process, not keystrokes**: State when to invoke a capability and what outcome proves it worked. Omit basic sub-steps or flags the agent already knows.
3. **One component, one job**: Keep instructions and templates focused on their singular purpose. Dispatch to peer skills rather than summarizing their internals. Leave another agent's domain to that agent: name the hand-off, never how it does its work.
4. **State the contract, not the neighbour**: Specify what a component needs as input and delivers as output. Never couple to specific neighbour names or slugs; composing agents decide what fills each slot.
5. **Decouple persona from execution (Who vs How)**: Personas establish persistent identity, authority boundaries, and behavioral tone; skills define modular, reusable execution recipes. Personas name capabilities without inlining skill mechanics; skills specify operational contracts without binding to specific personas.
6. **Progressive disclosure over monolithic injection**: Expose only routing metadata upfront; load procedural bodies just-in-time, and offload dense references to on-demand files.
7. **Write for a headless worker**: Assume unattended, asynchronous execution with no interactive human in the loop. A step never pauses or waits for human input; explicit approval boundaries terminate the task and wire dependent tasks as blocked.
8. **Promise only what the executor delivers**: Output contracts list only artifacts and state the executing agent itself produces. Another party's subsequent act (human sign-off, reviewer verdict) is never an executor deliverable.
9. **Verification must be real**: Demand direct inspection of live artifacts (outputs, logs, diffs) rather than relying on compliance checklists.
10. **Instruction density over conversational prose**: Maximize high-signal constraints per token. Every line earns its place; eliminate incident stories, post-mortems, and historical rationales.

## The Deletion Test

Delete or relocate any line whose removal leaves the median task unaffected. Confine rare paths and deep schemas to progressive reference files. Eliminate legacy patches and bug retrospectives; instructions define current state only.

## Persona vs. Skill Boundaries

Maintain strict architectural separation between agent definitions and skill instructions:

1. **Agent Personas (The "Who")**: Global, persistent system instructions loaded on every turn. Bound to 5–10% of base token budget. Define role identity (1–3 sentences), authority limits, behavioral postures, output schemas, and safety invariants.
2. **Skills (The "How")**: Modular, transient workflow packages loaded just-in-time when invoked. Define step-by-step procedures, tool calling sequences, input/output contracts, and validation criteria.
3. **Linking and Decoupling**:
   - **Personas never inline skill mechanics**: An agent persona names available skills or declares tool access, but never prescribes a skill's internal steps, modes, or argument flags. Skills evolve without requiring persona updates.
   - **Skills never couple to specific personas**: Instructions define objective contracts executable by any capable agent. Avoid persona-specific language, names, or assumptions.

### Three-Level Progressive Disclosure

To prevent context bloat and instruction dilution, structure skill packages in three tiers:

- **Level 1: Frontmatter Metadata (Router)**: `name` and `description` loaded into the system prompt. Acts as the semantic router.
- **Level 2: Skill Body (`SKILL.md`)**: Operational instructions loaded just-in-time when the skill is claimed or triggered.
- **Level 3: Auxiliary References (`references/`, `scripts/`)**: Detailed schemas, reference manuals, or executable tools stored exactly one directory deep and loaded on demand.

#### Incorporating Level 3 References

Agents rarely explore unprompted reference files. To ensure Level 3 assets are read reliably without bloating median context:

1. **Imperative Procedural Gating**: Never rely on passive suggestions ("see references/...", "consult X"). State an explicit condition, exact relative path, and action in the Level 2 procedure: e.g., `If <condition>, read references/<file>.md before <action>`.
2. **Shape Inline, Depth in Reference**: Provide structural contracts, schema skeletons, and expected shapes inline in the Level 2 body so the agent understands the pattern immediately. Use Level 3 files strictly for exhaustive enumerations, raw schemas, or rare edge cases.
3. **The Median Path Invariant**: If an agent must read a file on the median execution path, that content belongs inline in Level 2 (refactored to fit the 30–80 line budget), not in Level 3. Level 3 is reserved strictly for off-median branches, deep references, or secondary lookups.

## Length Budgets by Instruction Type

Adhere to quantitative token and line limits to prevent attention degradation ("Lost in the Middle") and instruction dilution:

| Instruction Type | Target Length | Hard Ceiling | Contents & Placement |
| :- | :- | :- | :- |
| **Agent Persona** | 30–60 lines (~200–500 tokens) | 100 lines (<2,500 chars) | Role identity, behavioral boundaries, safety invariants, output schema. |
| **Skill Description** | 1–3 sentences (150–400 chars) | 1,024 chars | Frontmatter router: trigger conditions, primary domain, explicit exclusions. |
| **Skill Body (`SKILL.md`)** | 30–80 lines (~400–1,000 tokens) | 150–200 lines (~1,500 tokens) | Step-by-step procedure, input/output contract, verification gate. |
| **Workflow Template** | 30–60 lines | 100 lines | High-level stage composition and handoff contracts. |
| **Tool Description** | 150–400 chars | 800 chars | Purpose, when to use, when NOT to use, argument constraints. |
| **Reference File (Level 3)** | 50–150 lines | 300 lines | Modular single-topic technical documentation or schemas. |

## The Description Is the Router

Frontmatter descriptions are the primary routing surface (target 150–400 chars, ceiling 1,024 chars). Because affirmative instructions yield significantly higher compliance (IFEval, arXiv:2507.22462), descriptions must be affirmative-first:

- **Affirmative-First Structure (1–3 sentences)**:
  1. _Core Capability_: Active imperative stating the primary domain and outcome (Sentence 1).
  2. _Trigger Conditions_: Explicit phrases, user asks, and task contexts where the skill applies (Sentence 2).
  3. _Contrastive Exclusions_: Terse negative boundaries paired with alternative redirects (Sentence 3).
- **Proportionate Exclusions**: Dedicate at least 75% of the description budget to positive capabilities and trigger conditions. Do NOT compile exhaustive lists of what a skill is not--negative enumerations dilute semantic matching and cause under-triggering.
- **Contrastive Redirects**: Limit exclusions strictly to real adjacent competitors or collision domains where ambiguity exists, and always name the alternative tool or peer skill (e.g., `Exclude for X (use Y)`).
- **Consolidate Routing**: Place all triggering logic in the description field. Auxiliary fields (e.g. `when_to_use`) are non-portable.

## The Body Is a Budget

Hold operational content strictly under the 200-line ceiling (target 30–80 lines):

- **Structural Anchoring (Primacy & Recency)**: Place critical invariants, boundary constraints, and stopping rules at the very start or very end where model attention is highest.
- **Progressive disclosure**: Offload dense reference tables, schemas, or script definitions to `references/` or `scripts/`.
- **Provide shape, not logic**: Provide structural skeletons rather than full worked logic examples that induce overfitting.

## Concision and Instruction Density

Maximize actionable constraints per token:

- **Positive imperatives with functional reasoning**: Frame rules around what the agent must do, paired with functional reasoning ("Use X because Y"). Functional clauses help models generalize.
- **Pair prohibitions with alternatives**: Every prohibition must state the mandatory affirmative path and legitimate escape hatch.
- **Eliminate conversational padding**: Strip politeness, conversational framing, and rhetorical flourishes.
- **Static prefix, variable tail**: Structure instructions with invariant rules and templates first, appending dynamic content at the end to maximize prompt cache hits.

## Workflow Templates

Workflow templates (`type: template`) govern repeatable multi-stage execution and task composition (<100 lines target).

- **Schema**:
  ```yaml
  ---
  title: <human name>
  type: template
  description: <one line: what class of work this covers, so a composer can select it>
  tags: [...]
  ---
  ```
- **Contract over neighbour**: Define input and output contracts per stage. Never name another template slug in frontmatter or body. A composite lists stages as contract expectations in order ("an independent review verdict on the spec"), never as slugs.
- **Headless execution & approval boundaries**: A step never pauses, waits, or prompts a human mid-task. Where approval is required, the step ends there: the worker files the complete artifact on the record and structures the boundary so downstream work remains strictly blocked until approval is recorded (e.g. releasing as `partial` with an explicit decision task or dependency-wired review task). Cut the composition chain at that boundary; work following the decision belongs in a separate dependent task.
- **Promise only executor deliverables**: Output contracts specify only artifacts and state generated by the executing agent. Future external decisions or approvals are not executor deliverables.
- **`wf-` prefix**: Templates stating an obligation that blocks acceptance rather than a process that proceeds conventionally carry a `wf-` prefix.

## Quality Gates

Every agent instruction, skill, persona definition, and subagent prompt must pass these five gates before merging:

1. **Categorical generality (Categorical Imperative)**: Express rules in general terms covering the full class of situations. Prohibit hyper-specific quotas, rigid interaction numbers, or one-off compromises.
2. **Entity abstraction (Name the process, not the actor)**: Refer to the principal as "the user", never by a personal proper noun or name. Refer to collaborators by role or capability.
3. **No PKB leakage (Data Boundaries)**: Never include private PKB note or task IDs (`aops_...`, `task_...`, `mem_...`, `kb_...`) or Obsidian wikilinks (`[[...]]`) in distributed framework instruction files. Use standard relative markdown links for file references.
4. **Zero historical provenance**: Strictly eliminate incident stories, post-mortem recaps ("after an incident on..."), or PR/commit changelog citations. Instructions define what is true now, never how it came to be true.
5. **Adjudication against empirical evidence**: When an instruction design choice or length budget is contested during review, cite the empirical findings and sources in `references/evidence.md`.

## Agent Definitions

Limit agent definition bodies to:

1. **Identity/role**: 1–3 sentences defining the persona.
2. **Behavioral rules**: Terse operational constraints.
3. **Output schema**: Expected report structure and verdict states.
4. **Routing table**: Clean table without per-route narrative.

Name a skill the agent uses; leave its modes, arguments, and when each applies to the skill. A change to a skill's modes or arguments owes the agent definitions that use it no edit.

## Schemas and Construction

- Define strict schemas with `required` fields and `additionalProperties: false`.
- **Static prefix, variable tail**: Emit invariant template text first and append variable content at the end to maximize prompt caching.
