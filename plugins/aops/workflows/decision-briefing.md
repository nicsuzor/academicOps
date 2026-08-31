---
title: Decision Briefing
type: template
category: process
description: Formulate a structured consequence briefing for a blocked or high-stakes decision. Select when work cannot proceed without an authoritative choice between competing approaches. Not for routine execution tasks (use `feature-dev`).
tags: [decision, briefing, governance, trade-offs, process]
---

# Process: Decision Briefing

Decision support framework to present structured options and trade-offs to the principal.

## 1. Decision Frame and Background

- State the core decision required, triggering context, and what work is currently blocked (`<decision-topic>`).
- Define the evaluation criteria (e.g. implementation complexity, performance, maintainability, risk).

## 2. Option Formulation

- Formulate 2-3 mutually exclusive, actionable options.
- For each option, document:
  - **Mechanism**: How it works and what changes.
  - **Pros & Cons**: Key advantages and drawbacks.
  - **Consequences**: Downstream impacts on architecture, maintenance, and users.

## 3. Evidence and Recommendation

- Provide empirical evidence, test results, or codebase citations supporting each option.
- State the recommended option and functional rationale.

## 4. Principal Gate

- Compose `wf-signoff-brief` with the options table and a single, explicit open question at the end.
- Halt execution and await principal decision before proceeding with implementation.
