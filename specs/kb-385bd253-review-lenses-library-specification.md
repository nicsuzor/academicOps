---
id: kb-385bd253
title: "Review Lenses Library Specification"
type: knowledge
created: 2026-05-17T03:15:40.567223905+00:00
modified: 2026-05-17T03:15:40.567223905+00:00
alias:
  - "kb-385bd253-review-lenses-library-specification"
  - "kb-385bd253"
permalink: kb-385bd253
---

## Intent

Design a library of independent, composable review agents ("lenses") that bring specific critical perspectives to academic and framework work.

## Distinction from Old Approach (Custodiet Hooks)

- **Old Approach (Custodiet):** Over-engineered coordination using enforcement hooks (blocking PRs or commits dynamically).
- **New Approach (Lenses):** Review lenses are explicitly instantiated as **tasks in the graph**.
- They are composed and sequenced by the `/planner` skill based on the project type.
- Agents do not self-enforce or block hooks; they produce structured findings (verdicts) on a task. Humans or orchestrators (like James) decide what to do with the findings. The agent that produced the work MUST NOT be the one reviewing it.

## Lens Specification Format

To add a new lens, it must declare the following:

- **Mandate:** The specific, narrow critical perspective the lens brings (e.g., "Is the approach rigorous?").
- **Evidence Gathering Method:** Explicit instructions on how the agent must find evidence (e.g., "Extract all claims and search Zotero", "Run code and check output"). Defaulting to "fast and plausible" is overridden by these strict procedural constraints.
- **Verdict Format:** The structured output required (e.g., PASS / FAIL / ESCALATE per section, with rationale).

## Composition Mechanism

How the planner selects and sequences lenses:

- The `/planner` evaluates the type of the parent deliverable (e.g., academic paper, PR, benchmarking report).
- The planner instantiates each required lens as a **child task** of the deliverable.
- Lenses are sequenced based on the iterative review pattern (per `mem-a156079f`):
  - **Round 1 (Factual/Structural):** Focus on correctness (e.g., Citation Verification, Quality, Rubric Fidelity).
  - **Round 2 (Analytical Depth):** Focus on substance (e.g., Methodology Critique, Argument Review, Completeness).
  - **Round 3 (Editorial):** Focus on presentation (e.g., Voice Review, Alignment).
- Each task is assigned to a specific expert agent (e.g., Pauli for strategy, Marsha for QA) with the lens's specification included in the task body.

## Specified Review Lenses

### Lens 1: Methodology Critique

- **Mandate:** Evaluate the rigor of the methodology. "What would a skeptical reviewer say? What alternatives weren't considered?"
- **Evidence Gathering Method:** Extract the methodology section. List unstated assumptions, identify missing control variables or alternative approaches, and compare against standard empirical practices for the specific domain. Do not accept claims of rigor at face value; demand proof of variance testing or controls.
- **Verdict Format:**
  - **STRENGTHS:** [List of robust methodological choices]
  - **VULNERABILITIES:** [List of weak points, unstated assumptions, or missing alternatives]
  - **VERDICT:** PASS / ESCALATE (Escalate if fundamental flaws or lack of rigor exist).

### Lens 2: Citation Verification

- **Mandate:** Ensure empirical validity of references. "Does each reference exist? Does the claim match the actual source text?"
- **Evidence Gathering Method:** Extract all citations and quotes. Cross-reference them with the provided bibliography or Zotero library. Check if the source text genuinely supports the specific claim made, rejecting fabricated or "fast and plausible" hallucinated citations.
- **Verdict Format:**
  - **CITATION CHECK:** [List of verified vs. unverified/missing citations]
  - **CLAIM ALIGNMENT:** [List of claims that misrepresent or overstate the source text]
  - **VERDICT:** PASS / FAIL (Fail if any citation is fabricated, hallucinated, or misrepresents the source).

### Lens 3: Argument Review

- **Mandate:** Assess the logic and fairness of the argument. "Is the framing fair? Are interpretations defensible? What's the strongest counterargument?"
- **Evidence Gathering Method:** Trace the causal chain of the argument from premises to conclusion. Identify logical leaps, straw-man counterarguments, or unfair framing of opposing views. Generate the strongest possible counterargument and evaluate if the text survives it.
- **Verdict Format:**
  - **CAUSAL CHAIN:** [Summary of the argument's underlying logic]
  - **COUNTERARGUMENTS:** [Identify the strongest counterarguments not addressed by the text]
  - **VERDICT:** PASS / REVISE (Revise if argument relies on logical fallacies, ignores major counterarguments, or uses unfair framing).

### Lens 4: Rubric Fidelity

- **Mandate:** Ensure marking follows the rubric consistently across all subjects.
- **Evidence Gathering Method:** Extract all grades/feedback and map them against the rubric criteria. Identify instances where similar work received different grades or where feedback contradicts the stated rubric descriptors.
- **Verdict Format:**
  - **RUBRIC ALIGNMENT:** [Summary of how well feedback matches rubric]
  - **INCONSISTENCIES:** [List of grading/feedback inconsistencies]
  - **VERDICT:** PASS / REVISE.

### Existing Lenses (For Context)

- **Alignment Review:** "Does this serve its stated purpose?"
- **Quality/Consistency Review:** "Are numbers, figures, cross-refs correct?"
- **Voice Review:** "Is tone appropriate for audience?"
- **Critic Review (Adversarial Plan):** "Fast pre-hoc critique using 10 cognitive moves."

## Extension Pattern

To add a new lens:

1. Define the lens using the **Lens Specification Format** (Mandate, Evidence Method, Verdict Format).
2. Append the new lens definition to this library specification.
3. Update the `/planner` instructions (or relevant task generation templates) to include the new lens as an option for the applicable deliverable types.
4. Ensure the lens task template explicitly requires the standard PASS/FAIL/ESCALATE/REVISE verdict so that human or orchestrator review can process the findings uniformly.
