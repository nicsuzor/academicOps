---
title: Framework Constraints
type: instructions
created: 2026-02-23
---
# Framework Constraints

Hard rules for aops framework internals. Enforced by pre-commit hooks where possible, by agents otherwise.

## C1: Workflow file length

**Max 100 lines** for any workflow markdown file (`skills/*/workflows/*.md`, `global_workflows/*.md`).

Workflows that exceed this are too complex to follow reliably. Split into:
- A shorter orchestration workflow that delegates to sub-workflows
- Reference docs (in `references/`) for detail that doesn't need to be in the execution path

**Enforced by**: `check-workflow-length` pre-commit hook (`.pre-commit-config.yaml`).

**Current violations**: Most existing workflows exceed this. Treat as tech debt — enforce on new workflows, refactor existing ones opportunistically.
