---
title: Investigation
type: template
category: process
description: Hypothesis-probe-conclude cycle for root-causing defects or unexpected system behavior when the underlying cause is unknown. Select when an issue occurs but its cause has not been proven. Not for implementing known fixes (use `feature-dev`) or runtime-only repro loops (use `live-fix-loop`).
tags: [debugging, investigation, root-cause, diagnostics, process]
---

# Process: Investigation

Diagnostic workflow to establish the verified root cause of an unexplained defect or system behavior before attempting code changes.

## 1. Symptom Capture and Reproduction

- Record the observed failure mode verbatim: error messages, stack traces, exit codes, or anomalous output for `<symptom>`.
- Isolate the minimal reproduction command or script (`<repro-command>`).
- Confirm the reproduction is reliable and deterministic before proceeding.

## 2. Hypothesis Formulation

- State candidate hypotheses that could explain the observed symptom.
- For each hypothesis, identify a falsification probe: what specific observation would prove the hypothesis false?
- Prioritize hypotheses by likelihood and inspection cost.

## 3. Diagnostic Probing

- Execute diagnostic probes in order: inspect logs, trace execution paths, or run isolated read-only queries.
- Probes must not mutate persistent system state or mask the original symptom.
- Record the exact outcome of each probe against its falsification condition.

## 4. Root Cause Determination

- Identify the single verified root cause supported by direct evidence.
- State why earlier hypotheses failed and why this mechanism explains all observed symptoms.
- If no hypothesis holds, formulate a new hypothesis set based on probe findings and repeat step 3.

## 5. Conclusion and Handoff

- Document the verified root cause and reproduction path.
- Route to `feature-dev` if a code change is required, or `develop-specification` if an architectural defect was discovered.
