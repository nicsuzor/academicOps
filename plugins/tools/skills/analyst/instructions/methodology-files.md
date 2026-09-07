---
title: METHODOLOGY.md Files
type: note
category: instruction
permalink: analyst-chunk-methodology-files
description: Structure, currency, and completion criteria for a research project's root METHODOLOGY.md.
---

# METHODOLOGY.md

Every empirical project maintains a root `METHODOLOGY.md` explaining the research design, theoretical framing, and epistemological choices so reviewers can evaluate validity without inspecting code. Technical implementation details belong in `methods/` (see `instructions/methods-vs-methodology.md`).

## Template skeleton

```markdown
# Methodology: [Project Title]

## Research Questions

[Primary question and specific sub-questions.]

## Theoretical Framework & Research Design

[Guiding literature, design type (experimental, observational, computational).]

### Variables & Unit of Analysis

- **Dependent**: [Outcome measures]
- **Independent & Controls**: [Manipulations, predictors, covariates]
- **Unit of Analysis**: [Individual, case, organization, observation window]

## Measurement Strategy & Analytical Approach

[How theoretical constructs map to operational proxies (links to methods/ files) and planned statistical strategies.]

## Validity, Limitations & Ethics

- **Internal / External / Construct Validity**: [Threats to causal inference and generalizability.]
- **Limitations & Alternatives**: [Known constraints and rejected alternative designs.]
- **Ethics**: [Approval identifiers, data governance, and privacy protections.]
```

## Currency and completion standard

- **Continuous currency**: Update immediately whenever questions, variables, units of analysis, or analytical strategies change. Record reasons in git commit messages.
- **Completion test**: A peer reviewer must be able to evaluate design validity, inferential threats, and generalizability solely from this document. If understanding the design requires inspecting source code, the methodology file is incomplete.
