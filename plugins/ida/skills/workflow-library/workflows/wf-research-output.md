---
description: Sequence an academic output (paper, report, essay, talk, dataset release) from direction and audience through design, external approvals, evidence, form selection, independent review, and release.
id: wf-research-output
tags:
  - wf-template
  - composite
  - research
  - output
title: Research Output Workflow
type: template
---

## What this step does

Sequences research aimed at an audience-facing academic output. Each stage defines a contract satisfied by domain-appropriate components, deferring form and venue commitments until the evidence justifies them.

## Stages

1. **Direction**: Define the question or claim, sought contribution, discipline, and target reader loosely enough to set analytical standards without fixing form or venue. Multiple audiences sharing one evidence base form separate directions if each output stands alone.
2. **Prior work**: Map the intellectual neighborhood -- existing claims, open questions, and adjacent fields using alternative methods.
3. **Design**: Justify a methodology, analytical frame, and required pilots against the question and audience standards, recording forks where alternatives compete.
4. **External Approvals**: Address external approvals (ethics, data access, collaborator agreements). Where an external approval applies, end the task in `partial` documenting the external approval in `reason` so dependent work remains strictly blocked until approval is recorded; wire downstream work with `needs: [<approval_task_id>]`. Where none applies, record that finding and why.
5. **Evidence**: Execute data collection and analysis (or conceptual development) to the design's standard.
6. **Form and venue**: Choose output form and venue supported by the evidence, revisiting only if evidence or audience shifts.
7. **Output**: Produce the artifact in the chosen form to that audience's standard.
8. **Review**: Obtain an independent evaluation (separate session from Stage 7) on methodological coherence, literature awareness, governance, feasibility, and assumption hygiene; resolve defects before release.
9. **Release and reach**: Submit or publish and deliver the output to the Stage 1 audience via a channel that audience uses.

## Maintained throughout

- **Argument map**: Maintain one canonical Argdown map from Stage 1 onward with every gap, fork, and unmet objection tagged, regenerating any visual rendering in the same task whenever design choices, findings, reviews, or direction change (never edit renderings by hand).

## Composition

Cut the task chain at every Stage 4 authorization boundary, at Stage 6 when venue/form is explicitly reserved by the user, and before Stage 8 independent review. Revisit Stage 1 if Stage 2 or 3 shifts direction; revisit Stage 2 if Stage 5 uncovers unmapped literature.

## Output contract

- Direction statement naming audience and discipline, mapped prior work, and justified design with pilot results.
- External approval determinations (approvals recorded or non-applicability documented) and evidence artifacts required by the design.
- Output artifact in chosen form, independent review verdict with resolution, and release record naming channel and destination.

## When to include

Any initiative producing an academic output for an audience, from initial concept through release.
