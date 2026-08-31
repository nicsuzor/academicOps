---
title: Constraint Check
type: template
category: gate
description: Verify that an artifact or plan complies with non-negotiable negative constraints and boundary invariants. Select when validating safety, data immutability, or policy invariants.
tags: [constraints, invariants, safety, verification, gate]
---

# Gate: Constraint Check

Policy compliance gate to enforce negative constraints and architectural boundaries.

## 1. Invariant Enumeration

- Enumerate applicable non-negotiable constraints for `<target>`:
  - Data immutability: research raw data must never be overwritten in place.
  - Scope boundaries: no unsolicited modifications outside designated directories.
  - Secret protection: no API keys or credentials committed to repository.
  - Craft axioms: line budget, no meta-commentary, outcome-based steps.

## 2. Direct Inspection

- Inspect git diff, modified file paths, and generated artifacts against each constraint.
- Check execution logs for forbidden operations or command patterns.

## 3. Verdict Emission

- Emit compliance verdict:
  - `COMPLIANT`: All constraints respected.
  - `VIOLATION`: Specific constraint violated; cite exact file, line, or command and halt.

## Exit Condition

`COMPLIANT` verdict confirmed by direct artifact diff inspection.
