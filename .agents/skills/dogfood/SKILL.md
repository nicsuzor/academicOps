---
name: dogfood
type: skill
category: meta
description: Delegated instruction testing — write instructions, commission contextless execution, observe friction, iterate, review quality, codify.
triggers:
  - "dogfood"
  - "test these instructions"
  - "instruction testing"
  - "delegated execution test"
modifies_files: true
needs_task: true
mode: execution
domain:
  - meta
  - framework
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, Skill
model: opus
version: 0.1.0
permalink: skills-dogfood
---

# Delegated Instruction Testing Guidelines

Test whether a set of instructions produces correct, complete, and verified outcomes when executed by a contextless agent. Do not perform the work yourself.

## Core Directives

### Phase 0: Verification & Data Landscape Mapping

Before writing instructions or propagating subagent results:

- **Verify verdicts**: Use `/verify` by citation to evaluate the subagent's actual output (freshness, completeness, limitations) against the original brief. Do not blindly accept or relay its self-reported status.
- **Sample data sources**: Open and read sample files directly. Do not assume data formats or presence (e.g. verify if a file contains input vs. output).
- **Map data channels**: Understand how data flows between main agents, subagents, and hooks/logs. Verify the exact delivery mechanism (e.g. tool result vs. system message).
- **Glob safety**: Avoid globbing large directories (10K+ files) with commands like `ls *.md` (which fail silently). Use targeted list/find queries (`find` or `ls | head`).

### Phase 1: Research and Draft

- Write self-contained instructions detailing objectives, exact data paths, sampling parameters, expected output format, and saving locations.
- Work directly in the target skill file for mature instructions. Avoid leaving stray scratch files in the repo.
- Enforce `/craft` author mode review to check for shallow-execution vulnerabilities before delegating.

### Phase 2: Commission Execution

- **Scale incrementally**: Start with a small batch size (e.g. N=2 tasks) to verify the pipeline before scaling.
- **Isolate context**: Launch the subagent with only the instruction file as context. Do not provide verbal coaching.
- **Execution management**: Let the agent run. Do not abort/restart for scope changes; send a redirect message to the running agent instead. Interrupt only for active harm.

### Phase 3: Analyze Friction and Iterate

- Analyze transcripts to classify friction (e.g. missing paths, ambiguous criteria, shallow analysis).
- Update the instructions in-place to address root causes, avoiding over-fitting to the specific test instance.
- Run at least 2 verification trials per condition when verifying that an edit closed a gap.

### Phase 4: Independent Quality Review

- Commission a separate review agent (e.g. `/strategic-review` or `/verify`) to evaluate depth, accuracy, and fitness of the subagent's deliverables.
- Enforce qualitative assessment by agents rather than relying on deterministic script checks.
- For decompose-mode instruction tests, use `references/decomposition-eval.md` (epistemics rubric + worked gold-standard pair).

### Phase 5: Codify & Land

- Promote tested instructions to canonical skills or commands.
- Verify deliverables actually reached their target destinations (e.g., reviews posted, commits pushed, task tracker updated).
- **Always leave a loose thread**: File follow-up tasks for any remaining friction items, promotion work, or subsequent phases before exiting.

## Output Expectations

- Respond with structured, concise summaries of dogfooding outcomes, listing specific instruction defects found, edits made, and verification run verdicts.
