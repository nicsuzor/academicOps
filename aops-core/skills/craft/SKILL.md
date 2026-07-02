---
name: craft
type: skill
category: meta
description: "Instruction quality gate — reviews agent instructions (task bodies, workflow steps, skill procedures, self-test protocols) for shallow-execution vulnerabilities before deployment. Two modes: author (pre-hoc review) and audit (trace a failure back to the instruction gap). The bar is excellence, not compliance."
triggers:
  - "craft"
  - "review these instructions"
  - "instruction quality"
  - "are these instructions good enough"
  - "raise the bar"
  - "why did the agent miss this"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - meta
  - framework
  - quality-assurance
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
model: opus
version: 0.2.0
permalink: skills-craft
---

# Instruction Craftsmanship

Review and audit agent-facing instructions — task prompts, workflow steps, skill procedures, self-test protocols — for excellence. Applies to any Claude agent system, not only this repo's framework.

## First Principles

Good instructions trust a capable, improving agent to exercise judgment; they do not try to mechanically pre-solve every case.

1. **Trust the harness, not today's quirks.** Agents and their tools improve continuously. Never write an instruction to patch a specific client's current limitation, plug a gap that will close on its own, or hard-code a workaround for how one version of an agent happens to behave. If a rule is only true "for now," it does not belong in a durable instruction.
2. **Specify the process, not the keystrokes.** State _when_ to invoke which capability and _what outcome_ proves it worked. Do not spell out sub-steps, tool flags, or branching logic a competent agent already knows how to perform (opening a PR, formatting a table, running a routine lookup). Name the judgment call, not the click-path.
3. **One skill, one job.** An instruction set is constrained to its own pure function. Naming another skill as a delegation or dispatch target is fine; explaining, restating, or summarizing that other skill's internals, procedures, or file layout is not — that creates a hidden dependency that silently rots when the referenced skill changes shape.
4. **Verification must be real, not performed.** "Did the step run?" is not evidence of anything. Instructions must demand direct inspection of the actual artifact — outputs, logs, diffs — with an eye for the failure that looks like success (silent errors, plausible-but-wrong data, a summary standing in for the thing itself).
5. **Every line earns its place.** Brevity is a feature. Cut anything that does not change what the agent does: provenance ("on the 2026-06-25 session…"), incident IDs, and recipes tuned to one past failure all belong in the PR/issue/memory that records _why_ a rule exists — not in the instruction loaded every run. Write the durable principle the incident illustrates, not the incident.

These are lenses, not a checklist to tick. If instructions feel shallow but match nothing below, trust the feeling and say why — depth is verification specificity, not step count.

## Common Defect Patterns

Instances of the principles above, worth naming because they recur:

- **Compliance framing.** "Did X run?" instead of "is the output correct, complete, and verified?" Require outcome-based checks, not process-completion checks.
- **Evidence laundering.** Accepting an agent's summary, a partial artifact-channel check (just stdout, not logs/exit-code/schema), or a green test suite as proof — without inspecting the actual output for silent failures, corruption, or placeholders. (Principle 4.)
- **Deferred-read dispersion.** A rule the agent needs _at the moment of action_ lives one pointer away ("see X.md") instead of inline. An agent that already has the instructions in hand frequently won't make the follow-up read. Inline mandatory content; reserve pointers for genuinely optional depth — never fork required content across a summary and a linked file.
- **Shape without source.** A step names what the output should _look like_ but not where it comes from or what operation produces it, so the agent satisfies the shape from whatever's cheapest — recycled material, an adjacent step's by-product, memory — silently dropping the real criterion. Name the source, mandate the read, prohibit substitution — without over-specifying the keystrokes (Principle 2's over-specification is the opposite failure).
- **Cross-skill coupling.** See Principle 3.
- **Mechanical HOW over judgment WHEN.** See Principle 2.
- **Over-fitting and ballast.** See Principles 1 and 5.

## Construction Rule: Static Prefix, Variable Tail

For any code that renders a template with dynamic data (an f-string, `.format()`/`.render()`, or a builder concatenating static scaffolding with session/transcript content): emit all static material first, append variable content last. Prompt caching keys on the longest identical prefix — one variable byte placed early invalidates the cacheable suffix that follows it. Where moving a placeholder to the tail would break meaning for negligible cache gain (a short single-token variable mid-sentence), leave it and say why.

## Modes

**Author** — review proposed instructions before deployment.

1. Assess against the principles and patterns above.
2. Quote any text exhibiting a defect and write a high-depth rewrite.
3. Verdict: **SHIP** (no defects), **REVISE** (edit in place with fixes), or **REJECT** (fundamental redesign needed).

**Audit** — trace an execution failure back to its instruction gap.

1. Identify what the agent missed and locate the executing instruction.
2. Classify the gap against the principles above.
3. Edit the instruction in place to prevent recurrence — as the durable principle the failure illustrates, not a recipe tuned to this one instance (Principle 5).

## Output

Structured, direct, concise. Cite exact line diffs where revisions are made.
