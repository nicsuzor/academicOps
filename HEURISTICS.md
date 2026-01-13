---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

## Skills Contain No Dynamic Content (P#19)

**Statement**: Current state lives in $ACA_DATA, not in skills.

**Derivation**: Skills are shared framework infrastructure. Dynamic content in skills creates merge conflicts and state corruption.

---

## Semantic Link Density (P#54)

**Statement**: Related files MUST link to each other. Orphan files break navigation.

**Derivation**: Links create navigable knowledge graphs. Orphans are undiscoverable.

---

## File Category Classification (P#56)

**Statement**: Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

**Derivation**: Mixed-category files are hard to maintain. Clear classification enables appropriate handling.

---

## No Horizontal Line Dividers (P#63)

**Statement**: Use headings for structure, not horizontal lines (`---`, `***`, `___`). Horizontal lines are visual noise.

**Derivation**: Headings provide semantic structure. Horizontal lines are purely visual and don't convey meaning.

---
