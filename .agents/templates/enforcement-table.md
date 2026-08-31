---
title: Enforcement Map Generation
type: template
category: process
description: Create or audit a flat 4-column enforcement map connecting rules and affordances to concrete implementation mechanisms and escalation severity. Select when auditing governance or rule enforcement.
tags: [enforcement, governance, architecture, audit, map, process]
---

# Process: Enforcement Map Generation

Audit and mapping process to trace governance rules to concrete enforcement mechanisms.

## 1. Rule and Affordance Discovery

- Enumerate all declared rules, axioms, and behavioral constraints for `<domain>`.
- Identify the source document (spec, axiom, instruction) governing each rule.

## 2. Mechanism Mapping

- For each rule, locate the exact code mechanism enforcing it:
  - Static linters / schema validators
  - Runtime hooks / pre-execution checks
  - Review gates / verifier subagents
- Record specific source file paths and line numbers (`<path:line>`).

## 3. Severity Classification

- Classify enforcement severity for each rule:
  - `BLOCKING`: Hard error; aborts execution immediately.
  - `ADVISORY`: Emits warning or guidance; execution continues.
  - `UNENFORCED`: Policy exists only in documentation; no code enforcement.

## 4. Map Synthesis and Gap Remediation

- Generate standard 4-column table: **Rule · Source Spec · Enforcement Mechanism · Severity**.
- Identify un-enforced critical rules and file issues to build automated enforcement.
