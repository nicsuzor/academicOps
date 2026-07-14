---
name: add-rule
type: skill
category: meta
description: Add a project-local rule to .agents/rules/ in Antigravity's native rule format. Use when the user asks to "add a rule", "add a project rule", "make this a rule", or wants a quick binding constraint recorded for this project only — not a universal axiom, not for distribution.
triggers:
  - "add a rule"
  - "add a project rule"
  - "new local rule"
  - "add to .agents/rules"
modifies_files: true
mode: execution
allowed-tools: Read, Write
version: 0.1.0
permalink: skills-add-rule
---

# Add Project-Local Rule

Record a project-local rule as one new file in `.agents/rules/`, in the same native frontmatter format as every file already there. Keep the rule body to **one sentence** — this is for a quick, binding, project-specific constraint, not a universal axiom (those live in `aops/axioms/` and go through `AXIOMS-REVIEW.md` governance) and it is never packaged or distributed.

## Steps

1. Get the rule's one-sentence content from the user (or the immediate context) and derive a short kebab-case slug for the filename.
2. Write `.agents/rules/<slug>.md`:

   ```
   ---
   trigger: always_on
   description: <the same sentence, or a short label for it>
   ---

   <One sentence rule.>
   ```

   Match existing sibling files' frontmatter keys exactly (`trigger`, `description`). Do not add a heading, anchor, or `_Review:_` footer — that ceremony belongs to formally-reviewed universal axioms, not ad hoc project rules.
3. Do not touch `aops/axioms/`, `dist/`, or `scripts/build.py` — those are the distribution pipeline for universal axioms and are out of scope here.

## Why no further wiring is needed

Both surfaces already pick up everything in `.agents/rules/` automatically:

- Antigravity/agy reads `.agents/rules/*.md` directly.
- Claude reads it via `./CLAUDE.md` → `.agents/CORE.md`, which points agents at `.agents/rules/*.md` for project rules alongside `.agents/AXIOMS.md` for universal ones.

If either `./CLAUDE.md` (a one-line `@.agents/CORE.md` import, mirroring the existing `./GEMINI.md`) or that pointer in `.agents/CORE.md` is ever missing, fix that first — the rule file alone won't reach Claude without it.
