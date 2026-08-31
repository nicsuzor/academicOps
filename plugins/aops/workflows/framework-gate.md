---
title: Framework Gate
type: template
category: process
description: Governance gate to evaluate and route requests that modify framework rules, axioms, or core architecture. Select when a request alters plugins, hooks, specs, or core system behavior. Not for routine application feature work (use `feature-dev`).
tags: [governance, framework, architecture, axioms, gate, process]
---

# Process: Framework Gate

Pre-execution governance check for changes that modify framework infrastructure or shared contracts.

## 1. Framework Modification Detection

- Assess whether proposed change modifies framework infrastructure: plugins, hooks, axioms, shared skills, or global specs (`<framework-targets>`).
- Check if proposed change impacts multiple downstream repositories or projects.

## 2. Impact and Risk Classification

- Categorize proposed change:
  - **Axiom/Rule Modification**: Changes fundamental behavioral constraints (highest severity).
  - **Spec/Contract Change**: Alters interfaces, schemas, or workflow definitions.
  - **Implementation Bugfix**: Fixes internal hook or plugin logic without interface change.

## 3. Specification and RFC Requirement

- For rule or contract changes, require a formal specification update (`develop-specification`).
- Verify backward compatibility and migration path for existing workspaces.

## 4. Audit and Sign-off Routing

- Run framework audit suite (`audit`) and full plugin test harness.
- Route deliverable to human principal for explicit approval (`wf-signoff-loop`) before landing changes.
