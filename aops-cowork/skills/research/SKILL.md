---
name: research
type: skill
description: >
  Academic research methodology guardian. Ensures agents working on empirical
  research maintain methodological integrity: research questions drive all
  design decisions, methods are appropriate and justified, data collection
  quality is verified before proceeding, and convenience shortcuts that
  compromise validity are caught and refused.
category: instruction
triggers:
  - "research project"
  - "methodology"
  - "research question"
  - "data collection"
  - "empirical analysis"
  - "dry run"
  - "research methodology"
  - "empirical research"
  - "methodological integrity"
  - "pilot study"
modifies_files: false
needs_task: false
mode: advisory
domain:
  - academic
allowed-tools: Read,Grep,Glob,Bash
version: 0.1.1
permalink: skill-research
---

# Research Methodology Guidelines

Enforce methodological integrity across all academic research design, execution, and reporting.

## Core Directives

1. **Research Question Driven**:
   - Every design, model, or data handling decision must directly serve the defined research question.
   - If a research question is not defined in `METHODOLOGY.md` or a user directive, halt and request clarification. Do not infer research questions or hypotheses.

2. **Methodological Justification**:
   - Ensure all model, variable, and sample choices are justified by the research design, not by computational convenience.
   - Do not drop variables, models, or conditions, or simplify experimental designs unless there is a clear methodological justification. Preserve all theoretically meaningful distinctions.

3. **Dry Run / Pilot Verification**:
   - Before full-scale execution, run a qualitative pilot audit.
   - Evaluate representative samples of actual outputs for content substance, completeness across all conditions, edge-case behavior, and face validity.
   - Do not declare a dry run successful based on error-free execution or aggregate statistics alone.

4. **Data Immutability**:
   - Keep source datasets, ground-truth labels, and experimental configurations immutable. Never modify or reformat raw source data.

5. **Report as Argument**:
   - Structure research reports as cohesive arguments where every chapter, section, and visualization directly supports a specific claim.
   - Ground all reported metrics in their practical and theoretical implications.
   - Collaborate section-by-section with the user to refine narrative framing.

## Documentation Requirements

- Document all methodological decisions (alternatives considered, assumptions, and limitations) in `METHODOLOGY.md` according to the canonical documentation structure.
- Document technical step-by-step implementation in separate files under `methods/`.

## Output Expectations

- Respond with clear, direct methodological feedback. Keep explanations concise, structured, and evidence-supported.
