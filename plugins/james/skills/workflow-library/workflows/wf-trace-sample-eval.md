---
alias:
  - wf-trace-sample-eval
description: Live trace comparative evaluation -- sample historical OTel traces to evaluate agent behavior across paired prompt classes before and after changes.
id: wf-trace-sample-eval
tags:
  - wf-template
  - testing
  - traces
  - otel
  - evaluation
  - comparison
title: wf-trace-sample-eval
type: template
---

## What this step does

Behavioral and qualitative comparative evaluation between baseline and candidate versions using genuine execution telemetry. Assesses response relevance, retrieval fidelity, and constraint compliance across representative query classes.

**Quiescence rule.** Never evaluate an intermediate spinner, loading indicator, or in-flight tool batch. Wait until the final response and prompt have settled.

## Sampling Methodology

1. **Live data strongly preferred.** Using existing live execution data is STRONGLY preferred over generating new data. Query OpenTelemetry (OTel) tracing to assemble a genuine sample of historical sessions and prompt interactions.
2. **Before and after pairing.** Collect paired call-and-response traces representing baseline (Bucket A) and candidate (Bucket B) executions.
3. **Fallback generation.** Only if recorded responses do not exist in historical traces for a required evaluation class should new test sessions be actively generated.
4. **Class-based comparison (not automated unit tests).** Prompts in Bucket A and Bucket B do NOT need to be identical strings. They must represent roughly similar classes of queries or tasks (such as conceptual lookups, explicit ID resolutions, multi-step delegations, or constraint boundary tests) to evaluate qualitative performance and drift.

## Evaluation Procedure

1. **Assemble trace sample.** Query OTel spans for sessions matching target test criteria and extract prompt-response pairs.
2. **Populate buckets.** Group interactions by prompt class into baseline and candidate sets. Supplement with generated interactions only where gaps exist.
3. **Qualitative grading.** Evaluator reads complete responses and scores output on:
   - Relevance and completeness against prompt intent.
   - Exact resolution of explicit references (such as task IDs or wikilinks).
   - Adherence to behavioral rules and safety constraints.
   - Absence of hallucinated tools or missing context.
4. **Drift and regression audit.** Compare qualitative grades across prompt classes between Bucket A and Bucket B to identify behavioral regressions or latency anomalies.

## Output contract

A qualitative evaluation report containing:

- Sample inventory: OTel session / conversation ID and span IDs for Bucket A and Bucket B with prompt class categorization.
- Comparative evaluation table: Prompt class, baseline response receipt, candidate response receipt, qualitative assessment, and regression verdict.
- Defect tickets filed for any observed regression (one task per root cause).
