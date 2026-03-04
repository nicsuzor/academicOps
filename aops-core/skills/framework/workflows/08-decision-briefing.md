---
title: Decision Briefing Workflow
type: instruction
category: instruction
permalink: workflow-decision-briefing
description: Generate user-facing briefing for tasks requiring approval or decision
---

# Workflow 8: Decision Briefing

**When**: User needs to review and make decisions on tasks blocking progress.

**Key principle**: Surface issues requiring human judgment with complete context so the user can make informed decisions quickly. Per AXIOMS #22 (Acceptance Criteria Own Success) - agents cannot make decisions that modify requirements or weaken criteria.

**CRITICAL**: This workflow generates briefings, not recommendations. Agents must not make subjective recommendations - instead provide structured consequence analysis for each option.

**Detailed procedures and examples**: See **[[decision-briefing-details]]**.

## Workflow Phases

1. **Gather Tasks Needing Decision**: Search for RFCs, blocked tasks, experiments, and investigations. If none, exit.
2. **Categorize and Deduplicate**: Group by priority (RFC > Blocked > Investigation > Design Decision > Experiment).
3. **Generate Briefing Document**: Extract and structure context, options, consequence matrix, and dependent tasks.
4. **Present to User**: Format as structured briefing and use AskUserQuestion for batch input.
5. **Execute Decisions**: Parse user response and execute (approve, reject, defer, prioritize) one by one with verification.

## Acceptance Criteria for Briefing

- [ ] Include ALL active tasks matching decision patterns.
- [ ] Provide enough context to decide without reading full issue.
- [ ] Show consequence matrix (not subjective recommendations).
- [ ] Show dependent issues for each decision.
- [ ] Be actionable - user can respond with "approve ns-xyz, defer ns-abc".

## Constraints

- **DO ONE THING**: Generate briefing and capture decisions.
- **DO NOT**: Implement approved changes or make subjective recommendations.
- **VERIFY-FIRST**: Check task status before inclusion and before execution.

**Empty State Handling**: If no tasks need decision, report and exit.
