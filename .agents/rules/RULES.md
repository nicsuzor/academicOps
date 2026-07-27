---
description: Project-local rules for the academicOps repository, applied on top of the axioms.
---

# Project Rules

These apply to this repository in addition to the axioms in `lib/axioms/`, never
in place of them. A rule belongs here only if it states a project-level
commitment a reviewer can name from the diff, and cannot be derived from an
axiom alone.

## Enforcement changes update the spec in the same PR

Any change that adds, modifies, escalates, or retires an enforcement mechanism
updates [`specs/enforcement/enforcement.md`](../../specs/enforcement/enforcement.md)
in the same PR, so the spec still describes reality after merge.

An enforcement mechanism is any measure intended to shape how an agent behaves —
hooks, review lenses, branch protection, and equally instructions, project rules,
and agent-persona edits. The test is not "which file did I touch?" but "does this
diff change what any agent is made to do?"

New rule content carried by a mechanism the spec already describes owes no new
section. Touch the spec only when the mechanism itself — its trigger, surface, or
scope — changed.

## Documentation goes where the taxonomy says

Any change to an instruction, skill, or documentation file complies with
[`specs/meta/doc-taxonomy.md`](../../specs/meta/doc-taxonomy.md). Placement is not
discretionary.
