---
name: project
type: skill
category: instruction
description: >
  Scaffold research project repositories with smart defaults — repo creation,
  directory structure, CI/CD, documentation, and PKB integration in one pass.
triggers:
  - "new project"
  - "set up a project"
  - "create a repo"
  - "scaffold"
  - "initialize project"
  - "/project"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - operations
  - research
---

# Project Scaffolding Guidelines

Initialize and configure research project repositories with complete operational infrastructure.

## Core Directives

1. **Information Gathering**: Learn the project title, research type (empirical, qualitative, library, mixed), collaboration team scope, data pipeline choice (dbt, DuckDB, MLflow, DVC), and publication formats. Propose sensible defaults before execution.
2. **Infrastructure Rules**:
   - Establish git hygiene (add appropriate `.gitignore` and configure pre-commit hooks).
   - Ensure raw research data directories (`data/raw/`) are configured as immutable.
   - Create documentation stubs and issue templates.
3. **Execution**: Follow the setup procedure in `instructions/init` to construct the repository.

## Exclusions

- Do not add tools or directories unless explicitly selected by the user.
- Do not configure secrets or credentials (provide instructions instead).
- Do not create task logs, milestones, or epics (delegate to `/planner`).

## Output Expectations

- Present the proposed repository structure and tooling selection concisely to the user.
- Once approved, execute, report successful initialization, and list next-step commands.
