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
owner: pauli
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
model: opus
version: 0.1.0
permalink: skills-craft
---

# Instruction Craftsmanship Guidelines

Review and audit any agent-facing instructions — task prompts, workflow steps, skill procedures, self-test protocols — to eliminate shallow-execution vulnerabilities. Applies to any Claude agent system, not only this repo's framework.

## Modes of Operation

1. **Author Mode**: Review proposed instructions before deployment to catch execution gaps.
2. **Audit Mode**: Analyze execution transcripts after a failure to trace it back to instruction gaps.

## Quality Criteria: The Defect Classes

Ensure instructions are free of the following defects:

1. **Compliance Framing**: Avoid instructions defined as "did X run?". Require outcome-based verification ("is the output correct, complete, and verified?").
2. **Missing Artifact Chain**: Ensure all output channels (stdout, stderr, log files, JSONL transcripts, schema validations) are checked, not just the primary summary channel.
3. **No Adversarial Checks**: Explicitly check for silent failures (e.g., zero exit code on empty/corrupt outputs, config warn-instead-of-block overrides).
4. **Summary-as-Evidence**: Prohibit using agent summaries or claims as proof of success. Require direct inspection of actual artifacts.
5. **Undefined Boundary Behavior**: Explicitly define fallback search spaces or escalation procedures when standard searches return no results.
6. **Skimped Verification**: Require reading the complete output of files rather than simple grepping, keyword matching, or tail scans.
7. **No Negative Verification**: Check for the absence of unexpected outputs (corruption, credentials leak, placeholders) in addition to the presence of expected results.
8. **Deferred-Read Dispersion**: A rule the agent needs _at the moment of action_ lives in a second file it must go read — a "see `X.md`", a `[[link]]` to "canonical" doctrine, a "read first" pointer. An agent that already has the instructions in hand frequently will **not** make the follow-up read, so a load-bearing rule behind a pointer is a rule that often won't run. Keep the operative instruction where it executes and inline it; reserve pointers for genuinely optional depth, never for a step that is required every time. **Shorter, co-located instructions beat longer, more distributed ones in almost all cases** — when content is mandatory, fold it in and tighten rather than forking it into a referenced file (and never duplicate it across both the summary and the linked file, which is the worst of both). Audit-mode tell: the executing instruction was a pointer, and the missed rule lived one read away.
9. **Output-Shape Without Source-and-Action (Substitution by Path of Least Resistance)**: A required step that specifies what the output should _look like_ but names no source and does not mandate the operation that produces it. An agent satisfies the described _shape_ from whatever is cheapest to hand — material already in the file, a by-product of an adjacent step, prior memory — silently dropping the real criterion (a fresh reconstruction from primary sources). For any step that is required every run, write it as a direct, numbered, imperative instruction that **names the source** ("read `<path>`/query `<tool>`") and **mandates the operation** ("you MUST open them before writing this section"), and forbid the obvious cheap substitute. Diagnostic contrast (audit-mode tell): in the same skill, a sibling step that names its source and forces a live look-up executes correctly while the shape-only step gets substituted. Caveat — name the source and the action, not the keystrokes: over-specified, step-bloated instructions are their own defect (depth is verification specificity, not step count; see the closing note).

These are common patterns, not an exhaustive list. If instructions feel shallow but match no named defect, trust the feeling, say so, and articulate why — and remember depth is verification specificity, not step count.

## Workflow

### Author Mode Workflow

1. Assess the target instructions against the defect classes.
2. Quote any text exhibiting a defect and write a high-depth rewrite.
3. Output a verdict: **SHIP** (no defects), **REVISE** (defects found, edit file in-place with fixes), or **REJECT** (fundamental redesign needed).

### Audit Mode Workflow

1. Identify what the agent missed and locate the executing instruction.
2. Classify the instruction gap under the defect classes.
3. Edit the instruction in-place with a rewrite to prevent the failure.

## Output Expectations

- Respond with structured, direct reviews or audits. Keep lists and verdicts highly concise, citing exact line differences where revisions are made.
