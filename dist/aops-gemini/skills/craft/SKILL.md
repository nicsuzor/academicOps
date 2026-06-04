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

# /craft — Instruction Craftsmanship

## The Problem

Agents optimise for the shallowest valid interpretation of their instructions. An instruction that says "run tests and report results" produces an agent that reads the last line of pytest output and declares green — even when the hook logs contain schema validation errors, the JSONL transcript records silent failures, and the full output pipeline is broken.

The gap isn't in the agent. It's in the instruction. Shallow instructions produce shallow execution. No amount of downstream enforcement fixes this.

This skill is the quality gate that prevents shallow instructions from reaching agents.

## Two Modes

**Author mode** — you have instructions (a task body, a workflow step, a self-test protocol, a polecat dispatch brief). Before deploying them, invoke `/craft` to review for shallow-execution vulnerabilities.

**Audit mode** — an agent underperformed or missed something. You have the transcript. Invoke `/craft audit` to trace the failure back to the instruction gap and propose a rewrite.

## Author Mode: The Seven Defects

Review the instructions against these defect classes. Any one is sufficient to reject.

### 1. Compliance framing

The instruction defines success as "did it run?" instead of "did it produce correct, complete, verified output?"

| Defect                         | Fix                                                                                                                                                                                                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Run tests and report results" | "Run tests. Read the full output — not just the summary line. Read every line and note anything unexpected: errors, warnings, deprecations, schema mismatches, permission denials. Report the count AND any anomalies found anywhere in the output." |
| "Check the output"             | "Read every line of `<specific file>`. Verify that `<specific expected content>` is present and `<specific error patterns>` are absent."                                                                                                             |
| "Confirm it works"             | "Invoke `<specific action>`. Verify the output matches `<specific expected state>`. If it doesn't, report exactly what you observed."                                                                                                                |

**Test:** If an agent could satisfy the instruction by reading a single summary line and reporting "all good," the instruction has compliance framing.

### 2. Missing artifact chain

The instruction names the primary output channel but not the secondary ones where failures hide.

Every system has multiple output channels. A polecat dispatch produces stdout (summary), JSONL transcript (raw session), hook logs (hook events including errors), session JSON (gate states), and enforcer reports. A CI run produces stdout, stderr, exit code, artifact uploads, and log files. Instructions that only check one channel miss failures in the others.

**Test:** List every artifact the system produces. If the instruction doesn't name at least the top three, it has a missing artifact chain.

### 3. No adversarial checks

The instruction doesn't ask "what would fail silently?" Silent failures are the most dangerous class — the system appears healthy, the agent declares success, and the actual failure propagates undetected.

Common silent failure patterns:

- Hook output rejected by schema validation (error logged but output discarded — agent never sees the advisory)
- Data written to wrong location (file exists, but at wrong path — subsequent reads silently return stale data)
- Process completes with exit 0 but produces empty/malformed output
- Gate configured to `warn` instead of `block` (warning emitted but agent continues regardless)

**Test:** Can you name a failure mode that would produce zero visible errors in the primary output channel? If yes, and the instruction doesn't check for it, this defect is present.

### 4. Summary-as-evidence

The instruction accepts a summary or claim as evidence instead of requiring independent verification.

| Defect                                | Fix                                                                                                                                                      |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "The agent reported all tests passed" | "Read the test output file directly. Count passed/failed/error yourself."                                                                                |
| "No errors were found"                | "Read `<specific files>` in full. For each file, state what you observed. If you found nothing unexpected, say so explicitly and name what you checked." |
| "The task completed successfully"     | "Verify the expected output artifact exists at `<path>`, contains `<expected content>`, and was modified after `<timestamp>`."                           |

**Test:** If the instruction's verification step could be satisfied by quoting the agent's own summary, it has summary-as-evidence.

### 5. Undefined boundary behavior

The instruction doesn't tell the agent what to do when it reaches the edge of its search space and finds nothing.

The most dangerous instruction gap: the agent finds no problems in the obvious place, concludes there are no problems, and stops. It never looks in the non-obvious places because the instruction didn't tell it to.

| Defect                      | Fix                                                                                                                                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Check the logs for errors" | "Check `<primary log>` for errors. If you find none, also check `<secondary log>` and `<tertiary source>` before declaring clean."                                                            |
| "Verify the hook fired"     | "Verify the hook output appears in `<expected channel>`. Also verify it does NOT appear in `<wrong channel>` (routing inversion). Also check `<error log>` for schema validation rejections." |

**Test:** If the instruction has a verification step with only one place to look, and the agent finds nothing there, what does it do? If the answer is "declare success," this defect is present.

### 6. Skimping on verification

The instruction doesn't require the agent to actually read all the output. It assumes a summary or a grep is enough.

QA is expensive. It is always expensive. The instruction must not flinch from that cost. When an agent runs a system and needs to verify correctness, the instruction must require reading the full output of every artifact — not skimming, not grepping for keywords, not reading the last 10 lines. Reading. Every. Line.

Keyword grep is shitty NLP (P#49). An agent that greps for `error` and finds nothing declares success — but the actual failure said `Hook JSON output validation failed` or `Invalid input` or used vocabulary the grep didn't anticipate. The fix is not a better grep. The fix is to read the output and understand it.

| Defect                              | Fix                                                                                                                                                                                                        |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Grep the logs for errors"          | "Read the full hook log. For each entry, verify the output was accepted by the consumer. Report any entries where the output was rejected, malformed, or produced an unexpected result."                   |
| "Check the last 10 lines of output" | "Read the complete output. Note anything unexpected — not just errors, but warnings, deprecations, schema mismatches, permission denials, and any line that doesn't match the expected happy-path output." |
| "Scan for failures"                 | "Read every artifact the system produced. For each one, state what you observed. If an artifact is missing that should exist, note that. If an artifact contains content that doesn't belong, note that."  |

**Test:** Does the instruction use "grep", "scan", "check for", or "look for" as its verification verb? If so, it's asking the agent to pattern-match instead of comprehend. Replace with "read" and "verify."

### 7. No negative verification

The instruction only checks for the presence of expected output, never for the absence of unexpected output.

Positive verification ("does the expected thing exist?") catches omissions. Negative verification ("does anything unexpected exist?") catches corruption, leakage, and unintended side effects.

| Defect                                      | Fix                                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| "Verify the config file exists"             | "Verify the config file exists AND contains no unexpected keys, no `TODO`/`FIXME`, no template variables like `{placeholder}`." |
| "Confirm the hook output reached the agent" | "Confirm the hook output reached the agent AND did not also leak to the user surface."                                          |

**Test:** If the instruction only uses "verify X exists" or "confirm X happened" without any "also verify Y did NOT happen," this defect is present.

## Author Mode Workflow

1. Read the instructions being reviewed.
2. For each defect class, assess: is this defect present? Quote the specific instruction text that exhibits the defect (or note its absence).
3. For each defect found, propose a rewritten instruction that eliminates it.
4. Produce a verdict: **SHIP** (no defects), **REVISE** (defects found, rewrites proposed), **REJECT** (instructions are fundamentally compliance-framed and need a full rewrite).
5. If REVISE or REJECT: edit the instruction file in-place with the improvements.

## Audit Mode Workflow

Given: a transcript where an agent failed, underperformed, or missed something the user had to catch.

1. **Identify the failure.** What did the agent miss? What should it have done?
2. **Find the instruction.** What instruction was the agent executing? (Task body, workflow step, skill procedure, polecat dispatch prompt.)
3. **Classify the instruction gap.** Which of the seven defects is present? Most failures trace to 1-2 defects.
4. **Propose the rewrite.** What should the instruction have said to prevent this specific failure?
5. **Extract the general principle.** Is there a class of instruction that needs this fix, not just this one instance?
6. **File the fix.** Edit the instruction in-place. If the instruction is in a skill or workflow, update it directly. If it's a task body pattern, update the relevant skill's instruction-writing guidance.

## The Bar

This skill exists because academicOps is building a world-leading AI framework. The instructions we write for our agents define the upper bound of their performance. An agent cannot exceed the ambition of its instructions.

The standard is not "would a competent agent succeed with these instructions?" The standard is "do these instructions make it impossible for an agent to declare success without actually verifying success?"

Compliance is the floor. Excellence is the bar. The difference is in the instructions.

## Relationship to Other Skills

- **`/dogfood`** tests instructions by running them against a contextless agent. `/craft` reviews instructions by reading them. Use `/craft` before `/dogfood` Phase 2 (Commission Execution) as a pre-flight quality gate. If `/craft` says REVISE, fix the instructions before spending compute on a dogfood run.
- **`/design-rubric`** designs fitness criteria for user-facing deliverables. `/craft` designs quality criteria for agent-facing instructions. Same shape (design-time quality gate), different domain.
- **`/verify`** checks artifacts for correctness. `/craft` checks instructions for depth. An instruction is a type of artifact, but its quality criteria are about what it will PRODUCE, not what it IS.
- **`/survey retro`** reviews transcripts for problems. When retro finds a shallow-execution failure, classify it as root cause category "Instruction Gap" and reference `/craft audit` for the fix.

## Anti-Patterns

| Anti-pattern                                                   | Why it fails                                                                                                                                                          |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "The instructions are clear enough"                            | Clear is not deep. "Check the output" is perfectly clear — and perfectly shallow.                                                                                     |
| Adding more steps without more depth                           | Ten shallow steps are not better than three deep ones. Depth is verification specificity, not step count.                                                             |
| Specifying tools instead of goals                              | "Run `grep -r error`" is brittle. "Search for error patterns in all output channels" is resilient. Name what to find, not how to find it.                             |
| Reviewing instructions without the system's failure vocabulary | You can't assess adversarial coverage without knowing how the system fails silently. Read the system's error handling before reviewing its instructions.              |
| Declaring SHIP because no defects are obvious                  | The seven defects are common patterns, not an exhaustive list. If the instructions feel shallow but don't match a named defect, trust the feeling and articulate why. |
