---
name: quality-rubric
title: Quality Rubric
category: spec
---

# Framework Component Rubric (The Gold Standard)

This rubric defines the "Constitutional Requirements" for any component in `academicOps`. Use this to audit existing components and design new ones.

## 1. Constitutional Principles (From AXIOMS.md)

_Non-negotiable rules. Violations are critical defects._

- [ ] **Categorical Imperative**: Is the component's behavior justifiable as a universal rule? (Axiom 1)
- [ ] **Data Boundaries**: Does it respect `$ACA_DATA` (private) vs `$AOPS` (public framework)? Does it NEVER expose private data? (Axiom 5)
- [ ] **Project Independence**: Does it work without cross-project dependencies? (Axiom 6)
- [ ] **Fail-Fast**: Does it halt immediately on missing config/errors? No silent defaults? (Axiom 7, 8, 16)
- [ ] **Single Purpose**: Does it have ONE defined audience and ONE purpose? (Axiom 10)
- [ ] **Standard Tools**: Does it use the golden path (`uv`, `pytest`, `pre-commit`)? (Axiom 12)
- [ ] **Read-Only Skills**: Is the code in `skills/` immutable/read-only at runtime? (Axiom 14)
- [ ] **One Spec Per Feature**: Is there exactly one timeless spec defining it? (Axiom 29)

## 2. Visionary Alignment (From VISION.md)

_Does this further the framework's goals?_

- [ ] **Self-Curating**: Does it contribute to the system's self-awareness or improvement (logs errors, creates diagnostics)?
- [ ] **Zero Friction**: Does it minimize user effort (e.g., auto-capture)?
- [ ] **Maintenance Free**: Does it avoid requiring constant "babysitting"?

## 3. Operations & Architecture (From FRAMEWORK-PATHS.md + Best Practices)

_Is it built right?_

- **Location**:
  - Code: `$AOPS/skills/<name>/`
  - Scripts: `$AOPS/skills/<name>/scripts/`
  - Tests: `$AOPS/tests/skills/<name>/` (or collocated if accepted pattern)
  - Data: `$ACA_DATA/<domain>/` (NEVER in framework dir)
- **Documentation**:
  - `SKILL.md`: Exists, follows specific frontmatter schema.
  - `README.md`: If complex script logic exists.
  - In-code: Docstrings for all functions.
- **Execution**:
  - Scripts use `uv run` for dependency management.
  - No hardcoded paths (uses env vars `AOPS`, `ACA_DATA`).
