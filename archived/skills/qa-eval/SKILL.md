---
name: qa-eval
title: QA Evaluation Skill
category: instruction
type: skill
description: Black-box quality assurance for verifying work against specifications and user requirements
permalink: skills/qa-eval
tags: [qa, verification, compliance, specification]
---

# QA Evaluation Skill

Rigorous, cynical verification that work **actually achieves** what the user needs.

**Specification**: [[specs/qa-eval.md]]

## When to Invoke

- After completing significant work (before claiming "done")
- When verifying output matches a specification
- When checking process compliance against workflow requirements
- When something "should work" but you want independent verification

## Core Principle

**Tests passing ≠ success. Success = the system works as intended with real data.**

**Default assumption: IT'S BROKEN.** Your job is to PROVE it works, not confirm it works.

## Required Inputs

You need TWO things to evaluate:

1. **Specification** - What the work SHOULD produce
   - File path to spec document
   - Inline specification text
   - Reference to requirements/acceptance criteria

2. **Work Output** - What was actually produced
   - File path to output
   - Command to execute and capture output
   - Reference to created artifacts

## Workflow

**IMMEDIATELY call TodoWrite** with these steps:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Load specification - read what work SHOULD produce", status: "pending", activeForm: "Loading specification"},
  {content: "Step 2: Load work output - read/execute what was actually produced", status: "pending", activeForm: "Loading work output"},
  {content: "Step 3: Run output quality checks - compare actual vs expected", status: "pending", activeForm: "Checking output quality"},
  {content: "Step 4: Run process compliance checks - verify workflow was followed", status: "pending", activeForm: "Checking process compliance"},
  {content: "Step 5: Run semantic checks - apply cynical verification", status: "pending", activeForm: "Running semantic checks"},
  {content: "Step 6: Detect red flags - scan for common failure patterns", status: "pending", activeForm: "Detecting red flags"},
  {content: "Step 7: Produce report - structured findings with verdict", status: "pending", activeForm: "Producing report"}
])
```

## Step 1: Load Specification

Read the specification that defines expected behavior:

```python
Read(file_path="[path to spec]")
```

Extract:

- Required outputs (what should exist)
- Expected content/format
- Success criteria
- Constraints/guardrails

## Step 2: Load Work Output

Read or execute to capture actual output:

```python
# For files:
Read(file_path="[path to output]")

# For commands:
Bash(command="[command that produces output]")
```

**CRITICAL**: Capture FULL output. No truncation. No summaries.

## Step 3: Output Quality Checks

Compare actual vs expected for each specification requirement:

| Check           | Expected (from spec) | Actual (observed) | Status |
| --------------- | -------------------- | ----------------- | ------ |
| [requirement 1] | [spec says]          | [you observed]    | ✓/✗    |
| [requirement 2] | [spec says]          | [you observed]    | ✓/✗    |

**For each check**:

- Quote the specific spec requirement
- Quote the actual output (exact text)
- Mark pass (✓) or fail (✗)

## Step 4: Process Compliance Checks

Verify the workflow was followed:

| Requirement              | Evidence              | Status |
| ------------------------ | --------------------- | ------ |
| [process step from spec] | [how you verified it] | ✓/✗    |

**Common process checks**:

- Was TDD followed? (test written before implementation)
- Was plan-mode used for framework changes?
- Was critic review invoked?
- Were acceptance criteria defined before work?
- Was work committed and pushed?

## Step 5: Semantic Checks (Cynical Verification)

Apply the **Triple-Check Protocol**:

### 5a. READ THE FULL OUTPUT

- [ ] I read every line of output, not just first/last
- [ ] I verified content is SUBSTANTIVE, not just present
- [ ] Output length is appropriate for the complexity

### 5b. CHECK FOR EMPTY/PLACEHOLDER DATA

- [ ] No empty sections between headers
- [ ] No placeholder text (`{variable}`, `TODO`, `TBD`)
- [ ] No duplicate/repeated elements that indicate bugs

### 5c. VERIFY SEMANTIC MEANING

- [ ] Content makes sense for its purpose
- [ ] Data is REAL, not garbage or filler
- [ ] Output would actually be USEFUL to its consumer

## Step 6: Red Flag Detection

Scan for these patterns (ANY triggers HALT and investigation):

**Structural Red Flags**:

- [ ] Repeated section headers (template bug)
- [ ] Empty sections between headers
- [ ] Malformed structure (unclosed tags, broken formatting)

**Content Red Flags**:

- [ ] Placeholder variables visible in output
- [ ] Suspiciously short output for complex operation
- [ ] "Success" claimed without showing evidence

**Process Red Flags**:

- [ ] Tests check existence but not content
- [ ] Silent error handling (try/except swallowing)
- [ ] Verification skipped "to save time"

## Step 7: Produce Report

Use this exact format:

```markdown
## QA Evaluation Report

**Subject**: [What was evaluated]
**Specification**: [Reference to spec used]
**Verdict**: PASS | PASS WITH NOTES | FAIL

### Dimension 1: Output Quality

| Check   | Expected    | Actual     | Status |
| ------- | ----------- | ---------- | ------ |
| [check] | [from spec] | [observed] | ✓/✗    |

**Findings**: [Summary]

### Dimension 2: Process Compliance

| Requirement | Evidence       | Status |
| ----------- | -------------- | ------ |
| [step]      | [verification] | ✓/✗    |

**Findings**: [Summary]

### Dimension 3: Semantic Correctness

- [x/] Content makes sense for its purpose
- [x/] No placeholder or garbage data
- [x/] No structural anomalies
- [x/] Output useful to intended consumer

**Findings**: [Summary]

### Red Flags Detected

[List any, or "None detected"]

### Recommendation

**Verdict justification**: [Why this verdict]

**If FAIL or PASS WITH NOTES**:

- Issue 1: [description] → [suggested fix]
```

## Scoring Criteria

| Verdict             | Criteria                                                    |
| ------------------- | ----------------------------------------------------------- |
| **PASS**            | All dimensions pass, no red flags, cynical checks satisfied |
| **PASS WITH NOTES** | Minor issues that don't affect core functionality           |
| **FAIL**            | Any critical dimension fails OR any red flag detected       |

## What You Do NOT Do

- Trust agent self-reports without verification
- Skip verification steps to save time
- Approve work without real-world testing
- Modify specifications to match output
- Rationalize failures as "edge cases"
- Make implementation decisions (you evaluate, don't fix)

## Example Invocation

```
Skill(skill="qa-eval")
```

Then provide:

- "Evaluate [output file] against [spec file]"
- "Verify the hydrator output matches the hydrator spec"
- "Check if the session context extraction is working correctly"

## Axiom Grounding

- **#7 Fail-Fast**: If verification cannot complete, HALT
- **#13 Verify First**: Check actual state, never assume
- **#18 No Excuses**: Everything must work
- **#22 Acceptance Criteria Own Success**: Only spec determines completion
- **H37c Execution Over Inspection**: Run it to prove it works
