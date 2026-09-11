---
alias:
  - wf-qa
description: Universal QA gate -- assemble criteria, critically evaluate live output, effect, or artifact, and return a per-criterion qualitative assessment with evidence.
id: wf-qa
title: Quality Assurance Workflow
type: template
---

## What this step does

Universal QA instructions, qualitatively critiquing live outputs, effects, or artifacts against established acceptance criteria.

## Procedure

1. **Assemble Criteria**: Record acceptance criteria verbatim from the task specification before inspecting outputs.

2. **Evaluate**: Perform a practical, live evaluation of the artifact based on the criteria.

- Composition note: This step should be in a separate task to design and development stages: the evaluator should be independent of the artifact author.

- This step requires a _critical_, _qualitative_ assessment of the _outputs_ against the _acceptance criteria_. It is not sufficient to analyse the source, methodology, inputs, or test results; or to rely on hypothetical or attested descriptions of the outputs.
- The evaluator must examine the live artifact as it is actually produced, in situ, with real inputs. For code this means actually running a real process; documents and interfaces must be rendered and assessed visually; the substance of the output has to be carefully critiqued.
- A qualitative test means this step cannot be reduced to a pass/fail result. The artifact must be assessed against each criterion in context -- its purpose, audience, standards, congruency with existing work, compliance with genre expectations, aesthetic fit, etc. These questions always use a qualitative, continuous scale expressed textually; they cannot and should not be reduced to a numerical or binary rating.

3. **Confirm per-criterion**: Return an itemized report containing:
   - **Criterion**: Verbatim requirement from step 1.
   - **Evaluation**: Summary of overall critique
   - **Reasons**: A short assessment against each of the criteria (short form dot points preferred, each with pinpoint citation (`file:line`, extracted output, visual region)).
