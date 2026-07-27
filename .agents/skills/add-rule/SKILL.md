---
name: add-rule
description: Add a project-local rule for this repository. Use when the user asks to "add a rule", "add a project rule", or "make this a rule" — not a universal axiom, and never distributed.
allowed-tools: Read, Edit, Write
---

# Add a project-local rule

Project-local rules live in `.agents/rules/RULES.md`. They bind agents working on
this repository and are never packaged or shipped.

1. Get the rule's content from the user or the immediate context.
2. Add it to `.agents/rules/RULES.md` as one `##` section: a heading that states
   the obligation, then the shortest body that makes it checkable from a diff.
3. If it already has a section there, edit that section rather than adding a
   second one.

A rule earns its place only if a reviewer could name the breach from the diff and
it does not already follow from an axiom. If it is a universal claim, it belongs
in `lib/axioms/` and goes through that directory's review, not here.

Do not touch `lib/axioms/`, `build/`, or `dist/`.
