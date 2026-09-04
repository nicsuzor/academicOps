---
name: new-project
description: Scaffold a research project repository end to end — repo creation, directory structure, git hygiene, CI/CD, documentation stubs, issue templates, and PKB registration in one pass, with defaults proposed for approval before anything is written. Use for "new project", "set up a project", "create a repo", "scaffold", "initialize project". Not for adding tooling to a repository that already exists, not for provisioning secrets or credentials, and not for planning the project's work (use `strategize`).
---

# Project Scaffolding

Initialise a research project repository with complete operational infrastructure.

## Gather, then propose

Establish the project title, research type (empirical, qualitative, library, mixed),
collaboration scope, data pipeline choice (dbt, DuckDB, MLflow, DVC), and publication
formats. Propose the resulting repository structure and tooling selection to the user, and
execute only once they approve — scaffolding writes a layout that is expensive to unpick.

Add no tool or directory the user has not selected.

## Execute

Read `instructions/init.md` and follow it to construct the repository. It carries the git
hygiene the layout depends on: an appropriate `.gitignore`, pre-commit hooks, `data/raw/`
configured immutable, documentation stubs, and issue templates.

Provision no secrets or credentials — report the commands the user must run themselves.
Create no tasks, milestones, or epics; point the user at `/ida:strategize` instead.

## Report

Report the initialisation result and list the next-step commands, including the ones
deliberately left for the user.
