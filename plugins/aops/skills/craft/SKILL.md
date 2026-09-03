---
name: craft
description: Authoring standard and quality gate for agent-facing instruction text. Make sure to use this skill whenever writing, reviewing, or revising SKILL.md bodies, frontmatter descriptions, agent definitions, subagent prompts, slash commands, or tool descriptions. Use it to diagnose a skill that under- or over-triggers, or to determine what belongs in a reference file. Exclude this skill for human-facing prose (specs, reports), task briefs, or workflow templates. The bar is excellence, not compliance.
allowed-tools: Read, Write, Edit
---

# Instruction Craftsmanship

Author and review agent-facing instructions for excellence. When a rule here is contested, consult `references/evidence.md` for the measured findings that govern this standard.

## First Principles

Trust a capable, improving agent to exercise judgment through clear processes.

1. **Trust the harness, not today's quirks.** Write instructions for durable capabilities. Ignore transient client limitations and avoid hard-coding workarounds for temporary model behaviors.
2. **Specify the process, not the keystrokes.** State _when_ to invoke a capability and _what outcome_ proves it worked. Assume basic competence and omit sub-steps or tool flags an agent already knows.
3. **One skill, one job.** Constrain an instruction set to its own pure function. Name other skills as dispatch targets directly rather than summarizing their internals, which creates fragile, hidden dependencies.

4. **Verification must be real, not performed.** Demand direct inspection of the actual artifact (outputs, logs, diffs) to catch silent errors or placeholders. Process-completion checks are insufficient.

5. **Every line earns its place.** Relocate provenance, incident IDs, and historical narratives to the change record. Keep only the durable principles in the active instruction.

## The Deletion Test

Evaluate every line: if removing it leaves the median task unaffected, delete it or relocate it. Confine rare-path instructions to the specific skill or reference file owning that path, preserving the token budget of files loaded on every run.

**Self-referential rules keep their evidence.** Before cutting an incident or worked example, check whether it is the sole justification for a rule that constrains how this same file gets edited in future (e.g. "keep this list verbatim," "never merge these"). Deleting that evidence does not lighten the rule — it leaves a bare assertion the next editor has no way to verify, weigh against a plausible-looking shortcut, or cite when refusing one. Relocate it to a `specs/` entry the instruction can point to, per principle 5, rather than deleting it outright.

## The Description Is the Router

A skill's frontmatter description is the only part loaded before invocation. Models under-trigger by default, so descriptions must aggressively advocate for their own selection:

- **Front-load intent:** Open with the skill's purpose and exact trigger conditions using the caller's vocabulary (e.g., "Make sure to use this skill whenever..."). The character cap is 1,024.

- **Define exclusions:** Provide explicit contraindications (e.g., "Exclude this skill when...") to prevent over-triggering and crossover.

- **Consolidate routing:** Keep all triggering data in the description itself to maintain portability across harnesses. The `when_to_use` field is deprecated. Promise only what the body delivers.

## The Body Is a Budget

Skill bodies load into working context, where attention heavily degrades in the middle of long files:

- **Limit length:** Hold operational content under 200 lines. Split skills that outgrow this, as highly focused skills yield significantly higher task-completion rates than exhaustive ones.

- **Segment clearly:** Place load-bearing constraints first or last, and use strong markdown headers (`##`) to provide structural navigation anchors.

- **Use progressive disclosure:** Move dense reference matter (schemas, style guides) into `references/` files exactly one level deep. Explicitly command the agent to read them at the moment of action (e.g., "Use the Read tool on `references/evidence.md` before generating code").

- **Provide shape, not logic:** Supply examples of output _shape_ (schemas, skeletons) and withhold worked examples of _logic_ to prevent the agent from blindly overfitting to the specific example.

## Voice

- **Positive imperatives:** Write affirmative commands paired with functional reasoning (e.g., "Use parameterized queries because the ORM closes injection paths"). Explaining _why_ helps models map and generalize the rule to novel edge cases.

- **Provide escape hatches:** When a prohibition is unavoidable, pair it with the required affirmative alternative and a legitimate escape hatch.
- **Emphasize via structure:** Use document structure for emphasis. Reframe capitalized absolutes ("ALWAYS", "NEVER") into standard text, as aggressive typography decays in efficacy across long contexts and creates attention noise.

## Agent Definition Files

An agent definition (`AGENTS.md` or a subagent prompt) loads on every invocation. Restrict the body to foundational architectural constraints:

1. **Identity/role:** One to three sentences defining the persona.
2. **Behavioral rules:** Terse standing constraints (epistemic standards, delegation rules).
3. **Output schema:** Required report shapes and verdict states.
4. **Routing table:** For orchestrators, a structured table without per-route narrative.

Keep subagent handoff descriptions to a single short sentence; excessive length dilutes the orchestrator's routing heuristic. Maintain permissions and tool allowlists strictly in the frontmatter.

## Task Naming, Filename, and Decision Craft

- **Verb-led titles:** Use brief, descriptive imperatives for task titles (e.g., `Implement X`, `Verify Y`).
- **Strict assignment:** Track ownership exclusively via `assigned_to` frontmatter. Use strictly functional task and file names, omitting personal names entirely.
- **Graph-based decisions:** Represent competing alternatives as mutually exclusive option nodes with blocking edges rather than standalone text tasks. Model unknowns as empirical probe tasks (`classification: spike`).
- **Concise bodies:** Limit task bodies to 50–150 words.
- **Edge economy:** Rely on inherent structural edges (parent/child) and apply lateral sibling edges only for genuine dependencies (data flow, supersedes).

## Schemas Are Contracts

Constrain structured outputs and tool parameters mathematically to prevent argument hallucination. Mark all mandatory fields as `required`, restrict options using `enum`, and set `additionalProperties: false` on every JSON object.

## Integrity Checks

Validate instructions against these failure conditions:

- The instruction relies on a mode, option, or path absent from the runtime.
- A reference pointer is dead (which acts as a missing instruction).
- A gate relies on an undefined term, forcing the agent to improvise.
- Two lines contradict, creating a license to fabricate.

## Common Defect Patterns

- **Compliance framing:** Relying on process-completion checks instead of outcome-based verification.
- **Evidence laundering:** Accepting summaries or partial checks (like a green test suite without inspecting the logs) as proof of success.
- **Shape without source:** Specifying an output format without mandating the data source, causing the agent to hallucinate placeholders to satisfy the structural requirement.

## Validating a Change

Test instructions blind against a fresh agent. If the agent deviates, fix the text rather than the agent. Always curate agent-drafted instructions against this standard, as self-generated skills measurably reduce overall task performance.

## Construction Rule: Static Prefix, Variable Tail

For template rendering, emit all static material first and append variable content last. This maximizes prompt caching, which keys on the longest identical prefix. Move variables to the tail unless doing so breaks critical sentence meaning.
