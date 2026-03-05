---
title: Framework Constraints
type: instructions
created: 2026-02-23
---

> **Curated by audit skill** - Regenerate with Skill(skill="audit")

# Framework Constraints

Hard rules for aops framework internals. Enforced by pre-commit hooks where possible, by agents otherwise.

## C2: Framework integrity (SKILLS.md + WORKFLOWS.md + wikilinks)

Skills in `aops-core/skills/` MUST have entries in `SKILLS.md`. Workflows referenced in `WORKFLOWS.md` MUST exist on disk. Wikilinks in framework files MUST resolve.

**Enforced by**: `check-framework-integrity` pre-commit hook (`scripts/check_framework_integrity.py`), runs on changes to `WORKFLOWS.md`, `SKILLS.md`, workflow `.md` files, and `SKILL.md` files.

**CI only**: Full codebase wikilink scan (`--full`) runs in CI, not on local commits (too slow).

---

## C1: Workflow file length

**Max 100 lines** for any workflow markdown file (`skills/*/workflows/*.md`, `global_workflows/*.md`).

Workflows that exceed this are too complex to follow reliably. Split into:

- A shorter orchestration workflow that delegates to sub-workflows
- Reference docs (in `references/`) for detail that doesn't need to be in the execution path

**Enforced by**: `check-workflow-length` pre-commit hook (`.pre-commit-config.yaml`).

**Current violations**: Most existing workflows exceed this. Treat as tech debt — enforce on new workflows, refactor existing ones opportunistically.
