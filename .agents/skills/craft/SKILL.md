---
name: craft
type: skill
category: meta
description: "Instruction quality gate — reviews agent instructions (task bodies, workflow steps, skill procedures, self-test protocols, agent definition files) for shallow-execution vulnerabilities before deployment. Two modes: author (pre-hoc review) and audit (trace a failure back to the instruction gap). The bar is excellence, not compliance."
triggers:
  - "craft"
  - "review these instructions"
  - "instruction quality"
  - "are these instructions good enough"
  - "raise the bar"
  - "why did the agent miss this"
  - "review this agent definition"
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

## Agent Definition Files — Content Boundary

Agent files (`agents/<name>.md`) are identity files loaded on every invocation — every byte is a budget line. The general principles apply; these rules are agent-file-specific.

The body may contain exactly four kinds of content:

1. **Identity/role** — one to three sentences: who the agent is, enough for a caller to route work here.
2. **Behavioral rules** — terse standing constraints the agent must hold regardless of task (epistemic standards, safety invariants, delegation rules).
3. **Output schema** — verdict states and required report shape; not methodology or worked examples.
4. **Routing table** (orchestrators only) — a table, not prose, with no per-route rationale.

Out of scope: skill matter (name the skill; never inline its procedure), documentation and reference material (an explicit exception to documentation-as-code — it belongs in specs/README/PKB), mechanics already enforced by the harness or hooks, paraphrases of the axioms, and authoring-time rationale or design history.

The token-budget test for any passage: **if removed, would the agent behave differently on the median task?** No → cut or relocate. Passages that only matter on rare tasks belong in the relevant skill, not the always-loaded identity file.

Frontmatter/body boundary: permissions, model, tools, and allowlists live in frontmatter only; the body never restates them in prose.

## Construction Rule: Static Prefix, Variable Tail (Prompt-Caching Requirement)

For any code that renders a template with dynamic data (an f-string, `.format()`/`.render()`, or a builder concatenating static scaffolding with session/transcript content): emit all static material first, append variable content last. Prompt caching keys on the longest identical prefix — one variable byte placed early invalidates the cacheable suffix that follows it. Where moving a placeholder to the tail would break meaning for negligible cache gain (a short single-token variable mid-sentence), leave it and say why.

## Output

Structured, direct, concise. Cite exact line diffs where revisions are made.
