---
description: Sequence an empirical or computational research project from exploration and MADRs through tracked read-only proof, an API contract, sign-off, and data execution.
id: wf-research-project
tags:
  - wf-template
  - template
  - research
  - composite
  - madr
title: Research Project Workflow
type: template
---

## What this step does

Sequences an empirical or computational research project from fast-to-MVP exploration through tentative continuation, live read-only proving, and a verified data-to-analysis API contract to user sign-off before collecting or generating new data, followed by ratified data execution and full analysis.

## Functional phases

Phase names below specify adaptable functional contracts, never fixed stage numbers; projects rename, split, or merge phases to fit. Govern baseline practice by domain standards (durable versioned preservation, immutable source records, transforms separated from presentation), apply retrieved personal (PKB) and project-local preferences alongside them, and name where each data class's authoritative copy lives (typically versioned source files for inputs with durable backup, treating query warehouses as live access layers unless independently versioned and backed up, and crystallising run outputs into durable storage as official records).

- **Approach exploration and initial choice**: Clarify the research question, source realities, domain standards, and retrieved preferences to design the simplest fast-to-MVP route without speculative scaffolding.
  - Record material decisions as concise standard MADRs surfacing comparative trade-offs, flow-on consequences, and a guessed (unbuilt) assessment against competing choices and the chosen implementation.
  - Frame initial choices for tentative build-and-prove continuation rather than final collection sign-off.
- **Build and live read-only proof**: Under tentative continuation, build only infrastructure, transforms, and initial analysis/report interfaces needed anyway on existing data.
  - Read live sources and configs, creating required new resources only with tracked actions and zero edits to existing resources or immutable data.
  - Run an independently evaluated full live read-only pass (zero simulated writes, zero new data collection) including real analysis, refine as needed, record newly uncovered decision forks as concise comparative MADRs, and lock the partitioned data-to-analysis API contract.
- **Final data-collection sign-off**: File the proven specification, initial build, tracked resource log, live run receipts, MADR log, independent evaluation verdicts, and partitioned API contract on the record before collecting or generating new data.
- **Data collection and full analysis**: Once user sign-off is recorded, execute data collection or generation and full analysis against the ratified API contract, recording a concise comparative MADR for each material decision.
  - Set sensible run safeguards without hard scripted cost caps: estimate volume and cost before costly or hard-to-reverse runs (large scans, expensive model or API batches), test and verify a small batch first (cutting to a `needs`-blocked task when scaling up requires unconfirmed scope, volume, and cost or user approval), and scale up in steps.

## Composition

- User direction authorizing infrastructure or analysis build satisfies tentative continuation and unblocks build-and-prove without a mid-chain pause; cut to a `needs`-blocked build task (`partial` with pending go-ahead in `reason`) only when tentative continuation is ungranted or explicitly user-reserved.
- Cut before new data collection or generation whenever collection awaits user sign-off or lacks confirmed scope, volume, and cost (`partial` with the pending decision in `reason`, leaving collection tasks `needs`-blocked); never pause interactively mid-task.

## Output contract

- Exploration decision package (retrieved preferences, concise comparative MADRs, and recommended tentative build scope).
- Proven specification, initial build and analysis/report interface on existing data, tracked new-resource log, live read-only proof receipts, MADR log, independent evaluation receipts, and partitioned data-to-analysis API contract filed for user sign-off.
- Post-sign-off execution deliverables: collected datasets, ratified full analysis artifacts, and concise comparative MADRs for material execution decisions.

## When to include

Empirical or computational research pipelines where infrastructure, transformations, and client-side analysis must be built and proven live read-only before committing to new data collection or generation.
