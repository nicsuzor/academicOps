---
name: axioms
title: Universal Principles
type: instruction
category: instruction
description: Inviolable rules and their logical derivations.
---

# Universal Principles

## Data Boundaries (P#6)

**Statement**: NEVER expose private data in public places. Everything in this repository is PRIVATE unless explicitly marked otherwise.

**Derivation**: Privacy is a fundamental right. Accidental exposure of private data causes irreversible harm.

---

## Fail-Fast (Code) (P#8)

**Statement**: No defaults, no fallbacks, no workarounds, no silent failures.

**Corollaries**:

- Fail immediately when configuration is missing or incorrect
- Demand explicit configuration

**Derivation**: Silent failures mask problems until they compound catastrophically. Immediate failure surfaces issues when they're cheapest to fix.

---

## Self-Documenting (P#10)

**Statement**: Documentation-as-code first; never make separate documentation files.

**Derivation**: Separate documentation drifts from code. Embedded documentation stays synchronized with implementation.

---

## Single-Purpose Files (P#11)

**Statement**: Every file has ONE defined audience and ONE defined purpose. No cruft, no mixed concerns.

**Derivation**: Mixed-purpose files confuse readers and make maintenance harder. Clear boundaries enable focused work.

---

## Skills Are Read-Only (P#23)

**Statement**: Skills MUST NOT contain dynamic data. All mutable state lives in $ACA_DATA.

**Derivation**: Skills are framework infrastructure shared across sessions. Dynamic data in skills creates state corruption and merge conflicts.

---

## Trust Version Control (P#24)

**Statement**: We work in git repositories - git is the backup system.

**Corollaries**:

- NEVER create backup files: `_new`, `.bak`, `_old`, `_ARCHIVED_*`, `file_2`, `file.backup`
- NEVER preserve directories/files "for reference" - git history IS the reference
- Edit files directly, rely on git to track changes
- Commit AND push after completing logical work units

**Derivation**: Backup files create clutter and confusion. Git provides complete history with branching, diffing, and recovery.

---

## Research Data Is Immutable (P#42)

**Statement**: Source datasets, ground truth labels, records/, and any files serving as evidence for research claims are SACRED. NEVER modify, convert, reformat, or "fix" them.

**Corollaries**:
If infrastructure doesn't support the data format, HALT and report the infrastructure gap. No exceptions.

**Derivation**: Research integrity depends on data provenance. Modified source data invalidates all downstream analysis.

---
