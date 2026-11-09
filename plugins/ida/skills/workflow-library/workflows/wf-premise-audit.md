---
alias:
  - wf-premise-audit
description: Comparative premise-check and hearsay audit -- automated telemetry assembly, stratified agentic qualitative defect evaluation, and mechanical confusion-matrix tallying across harnesses.
id: wf-premise-audit
tags:
  - wf-template
  - audit
  - premise-check
  - hearsay
  - telemetry
  - evaluation
title: wf-premise-audit
type: template
---

## What this step does

Comparative premise-check and hearsay gate audit across execution surfaces (such as Claude Code and Antigravity). Automates deterministic telemetry querying, census aggregation, candidate dossier extraction, and confusion-matrix synthesis, while routing all qualitative logical-defect and ground-truth evaluation strictly through agentic semantic comprehension.

## Input Contract

- **Evaluation Window / Sessions**: Defined time window (`--since`, `--until`) or explicit target session identifiers.
- **Excluded Sessions**: Identifiers of active audit or development sessions to exclude from population metrics.
- **Target Surfaces**: List of execution harnesses to compare (e.g. `claude-code`, `agy`).

## Stage Procedure

1. **Deterministic Telemetry Census & Dossier Assembly**:
   - Run `phoenix_premise_audit.py census` across the evaluation window to establish macro population counts (total recorded verdicts, mean verdicts per session, armed hearsay gates, overrides, recorder refusals, and gross vs operational distributions).
   - Run `phoenix_premise_audit.py dossier` to extract candidate evaluation records in JSON and Markdown, alongside an empty `annotations.json` template schema.
2. **Stratified Agentic Qualitative Evaluation**:
   - Dispatch capable multimodal agents to inspect extracted candidate dossiers.
   - For rejections (`REVISE` / `FAIL`), evaluate argument premises, warrants, and defeaters semantically without deterministic NLP: classify each rejection into Substantive Catch (`#conflict`, `#insufficient-for-stakes`, `#undercut`, `#missing`, `#scope-drift`, `#unanswered`, `#method-gap`), Structural Bar (`-- ... --` omission or orphan conclusions), or Format/Plumbing Noise.
   - For `PASS` verdicts, audit primary source-of-record verification against rubber-stamp reliance on secondary reports or peer claims.
   - Record qualitative classifications into the structured `annotations.json` file.
3. **Mechanical Confusion-Matrix & Comparative Synthesis**:
   - Run `phoenix_premise_audit.py tally --annotations annotations.json` to deterministically calculate signal-to-noise ratios, substantive shares, pass rigor rates, and confusion-matrix metrics across harnesses.
4. **Verification & Handback**:
   - Verify calculation outputs against telemetry receipts and package findings into an evidence-backed report ending in Chained Toulmin Argdown (`ida:premise-check`).

## Output Contract

- Population census table (`census.md` or embedded Markdown table).
- Agent-evaluated qualitative annotations artifact (`annotations.json`).
- Comparative audit report presenting substantive defect precision, pass rigor, and harness-specific plumbing findings.
