---
description: Build and prove a research pipeline live read-only on existing data under tentative approval, delivering MADRs and a partitioned data-to-analysis API contract.
id: wf-research-prove-readonly
tags:
  - wf-template
  - template
  - research
  - verification
  - api-contract
title: Research Build and Live Read-Only Proof Workflow
type: template
---

## What this step does

Executes a research project's build-and-prove phase under tentative continuation: reads live data and configs, builds strictly needed infrastructure and initial analysis/report interfaces on existing data, verifies quality via an independently evaluated live read-only pass, and locks the data-to-analysis API contract for user sign-off.

## Obligations

- **Ground in tentative choices and preferences**: Read tentative design choices, initial MADRs, live data sources, and live project configs, retrieving personal (PKB) and project-local preferences alongside domain best practices and confirming zero new data collection or generation is authorized in this pass.
- **Name the source of truth**: Record where authoritative inputs live (typically versioned source files) and treat any query warehouse as a live access layer, not the record.
- **Build fast-to-MVP with zero wasted effort**: Build strictly the infrastructure, transforms, client-side analysis tooling, and report interface the project needs anyway, documenting explicit assumptions about eventual data-phase inputs and outputs.
  - Untouched boundary: never modify existing systems, live configs, or immutable source datasets.
  - Permitted boundary: create required new resources only when every created resource and action is logged on the record.
  - Prohibited boundary: never build simulated write paths, dummy data sinks, throwaway mocks, or placeholder report prose.
- **Set sensible run safeguards**: Before any costly or hard-to-reverse run (large query scans, thousands of model or API calls, expensive models), estimate volume and cost, test and verify a small batch first, and scale up in steps; judge the safeguards each run needs without hard scripted cost caps.
- **Execute full live read-only run-through**: Run the real pipeline end to end on existing data except data collection or generation -- reading live sources/configs, running real transforms, executing real analysis, and rendering real reports. Halt and route to an authorized execution surface rather than mocking live runs if credentials are missing.
- **Evaluate quality and record newly surfaced MADRs**: Obtain an independent evaluation (separate session from build) of live run outputs, rendered reports, and client-side tooling against purpose and domain standards, refining until evaluation passes. Record any newly uncovered fork as a concise standard MADR (30-60 lines) surfacing trade-offs, flow-on consequences, and a guessed (unbuilt) assessment against competing choices and the chosen implementation.
- **Deliver partitioned data-to-analysis API contract**: Specify and verify the contract linking upstream collection/generation with downstream processing and analysis (schemas, formats, provenance keys, deterministic invariants, expected cost and failure modes), partitioning explicitly into **live-proven paths** (exercised on existing data) and **inferred data-phase assumptions** (awaiting collection).

## Composition

- Run independent evaluation via an in-session separate-context reviewer under `/supervise`, or via a `needs`-chained downstream review task when split onto the task graph.
- When downstream data collection or scaling up awaits user sign-off or confirmed scope, volume, and cost, cut at the boundary: release `partial` with the pending decision in `reason` (keeping `needs`-blocked downstream tasks unstarted, and minting no follow-up tasks as a plain leaf `/pull` worker).

## Output contract

- Proven specification, working initial infrastructure, and analysis/report interface built on existing data with zero wasted artifacts, zero simulated writes, and zero edits to existing resources.
- Log of tracked new resources/actions, live read-only execution receipts covering real analysis and rendered reports, and MADR log for newly surfaced forks.
- Evaluation receipts (plus independent review verdict when executed in-session) and partitioned data-to-analysis API contract filed on the record for user sign-off.

## When to include

Any research pipeline build task tentatively authorized to construct and prove infrastructure, transformations, and client-side analysis live and read-only prior to user sign-off on data collection or generation.
