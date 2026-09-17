---
name: new-project
description: Scaffold a research project repository end to end -- repo creation, directory structure, git hygiene, CI/CD, documentation stubs, issue templates, and PKB registration in one pass, with defaults proposed for approval before writing. Use for "new project", "set up a project", "create a repo", "scaffold", "initialize project". Not for existing repos, provisioning credentials, or planning project work (use strategize).
---

# Project Scaffolding

Initialise a research project repository with complete operational infrastructure.

## Gather, then propose

1. Establish project title, research type (empirical, qualitative, library, mixed), collaboration scope, data pipeline (dbt, DuckDB, MLflow, DVC), and publication formats.
2. Propose repository structure and tooling selection for user approval before writing files. Add no unselected tool or directory.

## Execute

Follow `instructions/init.md` to construct the repository:

- Git hygiene: `.gitignore`, pre-commit hooks, immutable `data/raw/`.
- Documentation stubs and issue templates.
- Provision no secrets or credentials; report commands for the user to run.
- Create no tasks or epics; direct the user to `/ida:strategize`.

## Report

Print initialisation results and remaining manual setup commands.
