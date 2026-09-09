---
alias:
- wf-qa-wf-qa
- wf-qa
category: gate
created: 2026-07-20T07:23:37.722328387+00:00
description: The universal QA gate -- assemble criteria, evaluate through a named child workflow, return a per-criterion verdict with evidence. Select it whenever an artifact must be judged before it is accepted; not for diagnosing a failure whose cause is unknown, and not for work with nothing checkable to hand back.
id: wf-qa
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
permalink: wf-qa
tags:
- wf-template
- v0.4
- module-f
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
