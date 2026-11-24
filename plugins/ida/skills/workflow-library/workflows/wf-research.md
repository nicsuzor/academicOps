---
description: Investigate problem spaces, retrieved personal/project preferences, constraints, and options fast-to-MVP with comparative trade-offs and flow-on MADRs.
id: wf-research
tags:
  - wf-template
  - research
  - template
  - madr
title: Research Investigation Workflow
type: template
---

## What this step does

Investigates a problem space, existing system or literature context, retrieved preferences, and candidate approaches fast-to-MVP -- surfacing trade-offs, flow-on consequences, and guessed comparative assessments in concise standard MADRs before commitment.

## Procedure

- **Define scope and MVP bounds**: Frame primary research questions, explicit unknowns, and minimum requirements needed now without speculative builds.
- **Investigate context and retrieve preferences**: Examine existing codebases, live data/configs, literature, constraints, and domain best practices, searching the personal knowledge base (PKB) and project-local specifications for personal and project preferences rather than assuming personal defaults.
- **Compare alternatives without building them**: Identify mutually distinct options including the simplest fast-to-MVP baseline. Evaluate trade-offs (complexity, validity, performance, cost, coupling, maintenance) and downstream **flow-on consequences** at every decision point, formulating an explicit **guessed (not built) comparative assessment** of each unbuilt option against competing choices and the chosen implementation.
- **Record concise MADRs per decision**: For each material decision, write a concise 30-60 line standard MADR (`# Title`, `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome`, and `### Consequences` with `Good, because...` and `Bad, because...` bullets nested under `## Decision Outcome`).
  - Attribute each force in plain prose under `Context and Problem Statement`, distinguishing domain baselines from named personal or project preference sources.
  - Present each option scannably (concise bullets or compact comparison) surfacing trade-offs, flow-on consequences, and the guessed unbuilt comparative assessment against competing choices and the chosen route.
  - For empirical research pipelines, state in plain prose under `Decision Outcome` whether approval is tentative pending read-only proof or ratified.
- **Document findings with citations**: Ground claims in pinpoint primary evidence (`file:line`, command outputs, literature, or specs) and state the recommended direction.

## Output contract

- Concise answers to primary research questions citing primary evidence and retrieved personal/project preferences.
- Concise 30-60 line standard MADR per material decision containing comparative trade-offs, flow-on consequences, and guessed unbuilt assessments against competing options and the chosen route.
- For empirical research pipelines preceding data collection or high-commitment execution, explicit tentative-continuation framing separating build-and-prove authorization from final collection sign-off.
- Channel format: persisted notes and MADRs use clear Markdown; internal agent handbacks use clean Argdown prose quoting deciding evidence inline.

## Composition

- For directed research tasks outside empirical collection boundaries, retain candidate options in the task body and treat user direction as delegating route selection (completing groundwork, selecting the recommended route, and unblocking downstream work), releasing `partial` with `reason` or assigning to the user only for an explicitly user-reserved choice or confirmed approval boundary.
- For empirical research pipelines preceding new data collection, mark exploration outputs as tentative continuation for read-only proving rather than final data-collection sign-off.
- Structure follow-up work as internal subtasks or prerequisite-chained child tasks, never loose siblings.

## When to include

Any task where the problem space, method, architecture, or technology choice is uncertain and needs grounded fast-to-MVP exploration before specification, build-and-prove, or execution.
