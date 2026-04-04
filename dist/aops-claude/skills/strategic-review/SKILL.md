---
name: strategic-review
type: skill
category: instruction
description: Three-agent review pipeline. Commissions pauli (Logician) for strategic abstraction iteratively until quality threshold met, then rbg (Judge) for axiom compliance, then marsha (QA) for verification.
triggers:
  - "strategic review"
  - "pre-hoc plan evaluation"
  - "adversarial review"
  - "plan review"
  - "review this document"
  - "review this proposal"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
  - quality-assurance
allowed-tools: Task,Read
version: 2.0.0
permalink: skills-strategic-review
---

# /strategic-review — Strategic Review Pipeline

Three-agent review pipeline for documents, plans, and proposals. Produces reviews that operate at the instance, class, and systems level — then verifies axiom compliance and confirms the work is complete.

**Pipeline**: pauli (strategic abstraction, iterative) → rbg (axiom compliance, single pass) → marsha (verification, single pass)

**pauli** carries the 10 cognitive moves of expert review. This skill commissions pauli, evaluates output against 7 dimensions, coaches if needed, and iterates until quality threshold is met. Then hands off to rbg for compliance checking, then marsha for final verification.

## When to invoke

Use this when a document needs strategic review, not proofreading:

- Plans and implementation proposals
- Research proposals and grant applications
- PR reviews where architectural or epistemological problems may exist
- Design decisions and specs
- Any time the question "is this actually good, or just coherent?" matters

## What to do

You are the SUPERVISOR. Commission pauli, evaluate its output, coach if needed, iterate until quality threshold is met. Then run rbg for compliance, then marsha for verification.

### Phase 1: Understand the document

Read the document. Identify:

- What type of document is this (plan, grant, PR, proposal)?
- What is it trying to accomplish?
- What is the claimed contribution or benefit?
- What context does the reviewer need?

### Phase 2: Commission pauli

Dispatch pauli to produce a strategic review:

```
Agent(subagent_type="aops-core:pauli", model="opus", prompt="
## Document to Review

[Full document text]

## Context
- Document type: [plan/grant/PR/proposal/other]
- What it's trying to accomplish: [1-2 sentences]
- Any relevant background: [domain, constraints, prior work]

Apply the 10 cognitive moves and produce a structured strategic review using the Strategic Review Output Format.")
```

### Phase 3: Score pauli's output

Evaluate across 7 dimensions. Score each: Pass / Partial / Fail.

| Dimension                      | What to look for                                                                  |
| ------------------------------ | --------------------------------------------------------------------------------- |
| **1. Multi-level abstraction** | Does it address instance AND class AND system? Or only surface?                   |
| **2. Meta-reasoning**          | Does it question whether the right question is being asked?                       |
| **3. Negative space**          | Does it identify what's MISSING, not just what's wrong?                           |
| **4. Fatal vs. fixable**       | Does it calibrate severity? Or treat everything as equal weight?                  |
| **5. Causal chain**            | Does it trace inputs→process→outputs→impact? Or evaluate components in isolation? |
| **6. Knowledge grounding**     | Does it reference what already exists / is already known?                         |
| **7. Actionable guidance**     | Does it specify what to change, not just what's wrong?                            |

**Pass threshold**: At least 5/7 Pass, AND dimensions 1, 2, 3 must all pass (these are the highest-leverage moves).

### Phase 4: Coach and retry if insufficient

If the review doesn't pass, identify which dimensions failed and generate targeted coaching:

For **dimension 1 failure** (stayed at surface level):

> "You reviewed the specific [plan/proposal]. Now: what CLASS OF PROBLEM does this represent? What is this an instance of? Step up: what SYSTEM is this embedded in, and what does the system need that this doesn't provide?"

For **dimension 2 failure** (answered the question rather than questioning it):

> "You engaged with the question as posed. Now: is the question itself well-formed? Is the right problem being diagnosed? Would an expert reviewer answer this question, or reframe it first?"

For **dimension 3 failure** (reviewed what's present, missed what's absent):

> "You reviewed what's in the document. Now: what should be here that isn't? What process, mechanism, check, or feedback loop is absent? The most important critique is often about what's NOT there."

Re-dispatch pauli with: original document + coaching instructions. Maximum 3 iterations.

### Phase 5: Commission rbg for axiom compliance

Once pauli's output passes (or after 3 iterations), commission rbg for a single compliance pass:

```
Agent(subagent_type="aops-core:rbg", model="haiku", prompt="
[Provide the session audit file path or inline the document + pauli's review]

Enforcement Mode: warn
")
```

Record the rbg verdict (OK / WARN / BLOCK). On BLOCK, surface the issue to the user before proceeding.

### Phase 6: Commission marsha for verification

Commission marsha for a single verification pass:

```
Agent(subagent_type="aops-core:marsha", model="opus", prompt="
Verify the review is complete.

**Original request**: [what was asked for]

**Acceptance criteria**:
1. Strategic review covers all 10 cognitive moves
2. Fatal/fixable distinction is made
3. Specific actionable recommendations are provided
4. rbg compliance check passed

**Work completed**:
- pauli's strategic review (above)
- rbg compliance: [OK/WARN/BLOCK + any issue]

Check all three dimensions and produce verdict.
")
```

### Phase 7: Produce final output

```
## Strategic Review

[Pauli's final review — verbatim, not paraphrased]

---

## Compliance Check

**RBG verdict**: [OK / WARN: [issue] / BLOCK: [issue]]

---

## Verification

**Marsha verdict**: [PASS / FAIL: [issues] / REVISE: [what to fix]]

---

## Supervisor Observation Log

**Document reviewed**: [name]
**Pauli iterations**: [n of 3 max]

**Initial quality** (after iteration 1):
- Multi-level abstraction: [Pass/Partial/Fail]
- Meta-reasoning: [Pass/Partial/Fail]
- Negative space: [Pass/Partial/Fail]
- Fatal vs. fixable: [Pass/Partial/Fail]
- Causal chain: [Pass/Partial/Fail]
- Knowledge grounding: [Pass/Partial/Fail]
- Actionable guidance: [Pass/Partial/Fail]

**Coaching delivered** (if applicable):
[Exact coaching instructions provided]

**Final quality**:
[Dimension scores after final iteration]

**Honest assessment**:
[What did the pipeline produce? Where does it fall short? What would a human expert catch that this didn't?]
```

## Design rationale

The loop exists because one-shot prompting reliably produces competent-but-not-genius reviews: internally consistent, surface-level, answering the question as posed. The supervisor's job is to force elevation — from instance to class, from artifact to process, from "is this right?" to "is this the right question?".

The pass threshold is intentionally high on dimensions 1-3. A review that doesn't operate at multiple abstraction levels, doesn't question the question, and doesn't identify negative space is not a strategic review — it's a proofreading session with better vocabulary.

The three-agent pipeline separates concerns: pauli does the strategic thinking, rbg checks the rules, marsha verifies the outcome. Each agent is optimised for one job.
