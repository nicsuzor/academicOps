---
name: root-index
title: academicOps Root Index
type: index
category: framework
description: Root entry point for the academicOps framework.
---

# academicOps Root Index

Welcome to the academicOps framework. This index provides entry points to the various components of the system.

## Core Framework (aops-core)

The core logic, hooks, agents, and skills are located in the `aops-core/` directory.

- [[aops-core/INDEX.md|Core Index]]
- [[aops-core/SKILLS.md|Skills Reference]]
- [[aops-core/WORKFLOWS.md|Workflows]]
- [[aops-core/RULES.md|Rules (Axioms & Heuristics)]]

## Documentation & Specifications

- [[docs/VISION.md|Vision Statement]]
- [[specs/INDEX.md|Specifications Index]] (planned)
- [[docs/walkthrough.md|Framework Walkthrough]]

## Directories

| Path | Purpose |
|------|---------|
| `aops-core/` | Core framework components |
| `docs/` | General documentation |
| `specs/` | Feature and workflow specifications |
| `scripts/` | Framework maintenance and utility scripts |
| `tests/` | Framework test suite |
| `lib/` | Shared libraries and submodules |

## Maintenance

Run `python3 scripts/audit_framework_health.py` to check framework health.
Run `python3 scripts/generate_context_index.py` to update the project context for agents.
