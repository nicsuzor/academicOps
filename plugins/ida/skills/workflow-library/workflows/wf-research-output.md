---
description: Sequence an academic output from direction and comparative MADRs through tentative empirical read-only proof, collection sign-off, evidence, review, and release.
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

Sequences an academic output (paper, report, essay, talk, dataset release) across adaptable functional phases -- incorporating fast-to-MVP exploration, tentative build-and-prove read-only verification on empirical projects, user data-collection sign-off, evidence, independent review, and release.

## Functional phases

Phase names, splits, and granularity adapt freely to each project; do not treat headings below as fixed stage numbers. Name each data class's authoritative source of truth explicitly (versioned source files for inputs, warehouses as live access layers, durable storage for crystallised outputs).

- **Direction**: Define the question or claim, sought contribution, discipline, and target reader loosely enough to set analytical standards without fixing form or venue. Multiple audiences sharing one evidence base form separate directions if each output stands alone.
- **Prior work**: Map the intellectual neighborhood -- existing claims, open questions, and adjacent fields using alternative methods.
- **Design exploration and initial choice**: Justify methodology, analytical frame, and required pilots against domain standards plus retrieved personal (PKB) and project-local preferences, without assuming personal defaults.
  - Record fast-to-MVP decision points as concise standard MADRs surfacing trade-offs, flow-on consequences, and guessed unbuilt comparisons against competing options and the chosen implementation.
  - On empirical or computational work, frame initial selections as tentative continuation rather than final collection sign-off.
- **External approvals**: Address ethics, data access, or collaborator approval requirements. Where an approval applies, release `partial` documenting the pending approval in `reason` so `needs`-wired downstream work stays blocked; otherwise record non-applicability.
- **Build and live read-only proof** _(empirical or computational projects)_: Construct needed infrastructure and initial analysis/report interfaces on existing data (tracked new resources only, zero existing edits, zero simulated writes). Verify via an independently evaluated live read-only pass, record new forks as concise comparative MADRs, and lock a partitioned data-to-analysis API contract.
- **Data-collection sign-off** _(empirical or computational projects)_: File the proven specification, initial build, tracked resource log, live proof receipts, MADR log, independent evaluation verdicts, and partitioned API contract before collecting or generating new data.
- **Evidence**: Execute data collection/generation and full analysis (or conceptual development for non-empirical work) to the ratified design and contract, recording a concise comparative MADR for each material methodological or analytical decision.
  - Set sensible run safeguards without hard scripted cost caps: estimate volume and cost before costly runs, test and verify a small batch first, and scale in steps.
- **Form and venue**: Select output form and venue supported by the evidence (recording a concise comparative MADR when competing forms or venues carry material trade-offs), revisiting only if evidence or audience shifts.
- **Output**: Produce the artifact in the chosen form to that audience's standard.
- **Review**: Obtain an independent evaluation (separate session from drafting) on methodological coherence, literature awareness, governance, feasibility, and assumption hygiene; resolve defects before release.
- **Release and reach**: Submit or publish and deliver the output to the target audience via a channel that audience uses.

## Maintained throughout

- **Argument map**: Maintain one canonical Argdown map from Direction onward with every gap, fork, and unmet objection tagged, regenerating visual renderings whenever design choices, findings, reviews, or direction change (never edit renderings by hand).

## Composition

- Cut the task chain (`partial` with `reason`, `needs`-blocked downstream tasks) at external approval boundaries, and before empirical data collection or costly scaling whenever runs await user sign-off or lack confirmed scope, volume, and cost.
- User direction to build satisfies tentative continuation; cut before build-and-prove only when tentative continuation is ungranted or explicitly user-reserved.
- Cut also when form/venue is explicitly reserved by the user and before independent output review; revisit Direction, Prior work, or Design if downstream evidence shifts aims or uncovers unmapped literature.

## Output contract

- Direction statement (audience and discipline), mapped prior work, external approval determinations, and justified design with pilot results and concise comparative MADRs grounded in domain standards and retrieved preferences.
- Empirical proof package filed prior to Evidence: proven specification, tracked initial build, live read-only proof receipts, MADR log, evaluation verdicts, and partitioned data-to-analysis API contract.
- Evidence artifacts, concise comparative MADRs for material execution or venue decisions, output artifact, independent review resolution, and release record naming channel and destination.

## When to include

Any initiative producing a reader-facing academic output (empirical, computational, or theoretical) from initial scholarly direction through publication or release.
