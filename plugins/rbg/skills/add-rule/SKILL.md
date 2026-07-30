---
name: add-rule
description: Add a project-local rule for the repository you are working in. Use when the user asks to "add a rule", "add a project rule", or "make this a rule" — not a universal axiom, and never distributed.
allowed-tools: Read, Edit, Write
---

# Add a project-local rule

Project-local rules live in `$CWD/.agents/rules/RULES.md`. They bind agents
working on this repository, and they are never packaged or shipped with it.

## First, check it belongs here

@include doctrine/lesson-routing.md

If the answer is any row other than the project row, stop and route it there
instead. Writing a task-scoped preference into this file is the characteristic
misuse of this skill: every future worker on the repository then inherits it as
standing law.

## Then write it

1. Get the rule's content from the user or the immediate context.
2. Add it to `.agents/rules/RULES.md` as one `##` section: a heading that states
   the obligation, then the shortest body that makes it checkable from a diff.
3. If it already has a section there, edit that section rather than adding a
   second one.
4. Check that the file's frontmatter carries `trigger: always_on`. Without it the
   file is reference material, and the in-session rule check never sends it.

Touch nothing else. A universal claim — one binding every project, not just this
one — is not yours to write here, and the framework's axioms are a gated
destination reachable only from the framework's own source tree.
