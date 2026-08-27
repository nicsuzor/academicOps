---
id: academic-paper
title: Academic Paper Workflow Spine
type: process
category: academic
description: Academic paper lifecycle from idea through drafting, internal review, and submission — the flat spine specialisers pair into
status: ready
requires: [task-tracking]
pairs-with: [[[wf-outbound-review]], [[wf-human-approval]], [[wf-verification]]]
---

# Process: Academic Paper Workflow Spine

A flat single spine covering the lifecycle of an academic research paper from
initial inception to journal or conference submission. Contextual variations and
methodological adaptations are handled through modifier configurations rather than
subtype template proliferation.

## Seedling Mode Awareness

In Stage 1 (situating / seedling mode), keep tasks shallow by design. Do not
pre-generate deep task trees or micro-decompose downstream phases. The initial
pass establishes the spike and preliminary scope; subsequent phases are carved
as uncertainty resolves through rolling-wave elaboration.

## The Spine Phases

1. **Spike** (`spike`)
   - Establish problem statement, research questions, and theoretical hook.
   - Assess feasibility, available resources, and potential contributions.
   - Define preliminary scope and boundaries.

2. **Literature Review** (`lit-review`)
   - Systematic search and mapping of relevant literature and prior art.
   - Situate research within existing theoretical and empirical debates.
   - Identify the specific gap the paper addresses.

3. **Methodology** (`methodology`)
   - Design research protocol, operational definitions, and instrumentation.
   - Establish sampling frame, data source selection, or experimental design.
   - Pre-register analysis plans or hypotheses where applicable.

4. **Ethics Gate** (`ethics`)
   - **Hard gate** before empirical data collection or human subject interaction.
   - Secure or verify institutional ethics approval (IRB / HREC).
   - Verify participant consent protocols, risk mitigations, and data protection compliance.

5. **Data Collection & Ingestion** (`data`)
   - Execute data collection protocol (surveys, interviews, scraping, archival retrieval).
   - Ingest, clean, validate, and store datasets in structured repositories.
   - Ensure reproducible data pipelines and provenance tracking.

6. **Analysis** (`analysis`)
   - Perform quantitative statistical modeling, econometric estimation, or qualitative coding.
   - Conduct robustness checks, sensitivity analyses, or triangulation.
   - Generate summary tables, figures, and analytical outputs.

7. **Writing & Submission** (`writing/submission`)
   - Draft manuscript sections: Introduction, Literature/Theory, Methods, Results, Discussion, Conclusion.
   - Apply venue-specific review criteria and stylistic conventions (e.g. law journal footnote density and normative framing vs empirical journal IMRAD structure).
   - Prepare submission package (cover letter, anonymised manuscript, data/code availability statements).
   - Compose [[wf-outbound-review]] or [[wf-human-approval]] prior to formal external submission.

## Deviations and Specialisers (Modifier Menu)

Customise the spine using modifier configurations without branching into subtype files:

- **Secondary Data Projects**:
  - **Skip**: Primary data collection phase (`data`) is bypassed.
  - **Spike**: Focuses on data access, API licensing, dataset provenance, and extraction feasibility.
  - **Ethics**: Verifies compliance with secondary data terms of use, privacy policies, and de-identification.

- **Theoretical / Conceptual Projects**:
  - **Replace**: `data` and `analysis` phases are replaced with iterative conceptual development, doctrinal synthesis, or formal model building.
  - **Ethics**: Ethics gate is skipped if no human participants, private datasets, or empirical human data are involved.

- **Replication Studies**:
  - **Spike**: Focuses specifically on reproduction feasibility — availability of original code/data, software environment dependencies, and artifact verification.
  - **Analysis**: Re-runs original specifications before executing extended robustness or perturbation checks.

## Anti-Patterns

- **Zero subtype files**: Do NOT create separate files like `law-journal-paper.md` or `empirical-econ-paper.md`. Handle venue and doctrinal requirements as review criteria during the `writing/submission` step.
- **No un-gated data collection**: Never begin empirical data collection without clearing the `ethics` gate.
- **No deep pre-decomposition**: In seedling mode, resist generating dozens of nested tasks before the spike and lit-review settle the direction.
