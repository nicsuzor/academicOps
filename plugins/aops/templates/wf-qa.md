---
alias:
  - wf-qa
category: gate
description: Universal QA gate -- assemble criteria, evaluate through a named child workflow, and return a per-criterion verdict with evidence.
id: wf-qa
tags:
  - wf-template
  - qa
title: wf-qa
type: template
---

## What this step does

Universal QA step establishing criteria, evaluator independence, and evidence standards. 

## Procedure

1. **Assemble Criteria**: Record acceptance criteria verbatim from the task specification before inspecting outputs.
2. **Evaluate**: Perform a practical, live integration test or evaluation of the artifact based on the criteria. The evaluator must be independent of the artifact author.
3. **Confirm per-criterion**: Return an itemized report containing:
   - **Criterion**: Verbatim requirement from step 1.
   - **Status**: Binary `MET` or `UNMET` (record reason if uncheckable).
   - **Evidence**: Pinpoint citation (`file:line`, command output, visual region).
