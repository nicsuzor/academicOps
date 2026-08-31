---
title: Governance Audit
type: template
category: process
description: Governance and structural audit across repository specifications, indices, and configurations. Select when auditing codebase health, dead files, broken links, or rule compliance. Not for single-file bugfixes (use `feature-dev`).
tags: [audit, governance, hygiene, integrity, verification, process]
---

# Process: Governance Audit

Systematic audit workflow for repository specifications, documentation integrity, and rule enforcement.

## 1. Audit Scope Definition

- Define the target audit domain: specs, plugins, hooks, workflow templates, or documentation (`<audit-domain>`).
- Enumerate authoritative rules, schemas, and axioms governing the domain.

## 2. Automated Integrity Scans

- Run link checkers, markdown linters, schema validators, and test suites (`<audit-suite>`).
- Detect dead links, dangling references, orphaned files, and malformed frontmatter.

## 3. Structural and Semantic Inspection

- Check that index files match actual directory contents.
- Verify that every document adheres to the craft standard (line budget, deletion test, no meta-commentary).
- Confirm that axioms and constraints are consistently enforced across implementations.

## 4. Findings Ledger and Remediation

- Compile findings into a structured ledger: file path, violation type, severity, and remediation action.
- Author remediation plan and route confirmed defects to cleanup tasks.
