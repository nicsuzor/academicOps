---
title: METHODOLOGY.md Files
type: note
category: instruction
permalink: analyst-chunk-methodology-files
description: Structure, currency, and completion bar for a research project's METHODOLOGY.md
---

# METHODOLOGY.md

Every research project carries one `METHODOLOGY.md` at its root, holding the
research design and epistemological approach for the whole project: the
question, why it matters, the theoretical frame, the design type, the variables
and unit of analysis, how outcomes are measured, what limits the approach, and
what alternatives were rejected. Write it so a peer reviewer can evaluate the
design without reading code.

Which statements belong here rather than in `methods/`: read
`instructions/methods-vs-methodology.md`.

## Structure

```markdown
# Methodology: [project]

## Research Questions

[Primary question and sub-questions.]

## Theoretical Framework

[The literature and theory this work builds on.]

## Research Design

[Experimental, observational, mixed-methods, computational.]

### Variables

**Dependent**: [what is measured]
**Independent**: [what is manipulated or examined]
**Controls**: [what is held constant or adjusted for]

### Unit of Analysis

[Cases, users, time periods, decisions.]

## Data Sources

[Overview only; provenance and schema live in the data README.]

## Measurement Strategy

[How each theoretical construct is operationalised: the construct, the
observable proxies chosen for it, and a pointer to the methods file that
computes them.]

## Analysis Approach

[The analytical strategy conceptually; implementation lives in methods/.]

## Validity and Limitations

[Internal validity: what threatens causal inference. External validity: what
the findings generalise to. Construct validity: whether the measures capture
what is claimed. Then the constraints, biases, and weaknesses, honestly.]

## Alternative Approaches Considered

[What else was considered, and why it was rejected.]

## Ethical Considerations

[Ethics approval, data privacy, potential harms.]
```

## Currency

This file states what the project actually does, in the tense in which it
actually happened. A design that has moved on and a file that still describes
the old one is a misreported method, so stop and update it the moment the
research question refines, the design changes, variables are added or
redefined, the unit of analysis moves, the analytical approach shifts, or a new
limitation surfaces — then resume. Commit the update with the reason for the
change in the message, so the evolution of the design stays recoverable.

## Complete when

A peer reviewer can, from this file alone, understand the design, evaluate its
validity, assess what the findings generalise to, identify the threats to
inference, and follow references to `methods/` for anything technical. If they
would have to read code to understand the design, it is not finished.
