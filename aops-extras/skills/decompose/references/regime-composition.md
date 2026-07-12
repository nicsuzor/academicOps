# Regime Composition — detail and record format

Full doctrine: [[10-workflow-library]] (what a template is, requirements) and
[[two-layer-decomposition]] §Gates. This file is the how; `SKILL.md` Step 2 is the contract.

## Composing, not inventing

A template is a short markdown file another skill reads and composes **in-context, by
comprehension** — you are not running a solver over `requires`/`pairs-with`/`conflicts`/`recommends`
frontmatter, you are reading the index, judging fit against the epic's stakes, and naming your
selection. Two kinds live in `aops-extras/workflows/`:

- **Process templates** — how a class of work proceeds (routing signals, unique steps, exit
  routing). Select the one (or composite) that matches the epic's shape.
- **Gate templates** — reusable QA/vetting/approval obligations. These are what door-type policy
  selects among: two-way vs. one-way is expressed as _which gate templates get composed in_, not a
  separate mechanism.

Read `aops-extras/workflows/INDEX.md` for name + one-line routing description per template before
selecting anything. If a hydrate bundle's `## Standards` section already surfaced candidate
obligations for this task, cross-check your selection against it rather than re-deriving from zero —
hydrate reports obligations, you sequence and compose them into a regime.

## Door-type → gate weight

| Door-type              | Examples                                  | Composed gate weight                                                                            |
| ---------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Two-way (reversible)   | drafts, analysis, read-only investigation | Light or automated evaluator-optimizer loop; gate templates like `qa`/`verification` suffice    |
| One-way (irreversible) | send, publish, prod, spend, delete, merge | Hard gate: a distinct evaluator identity, usually **plus human authorisation**, before crossing |

Gate at real junctures only (DO-CONFIRM), not between every step. When a subtask's reversibility is
genuinely ambiguous, classify it one-way — the cost of an unnecessary evaluator pass is far lower
than the cost of a missed hard gate on something that turns out irreversible.

## The traceability record (what Step 3 persists)

State the composed regime once, at epic level, by name — not folk knowledge, not re-derived per
subtask:

```markdown
### Composed regime (traceable to named templates)

- **Process:** <template name(s)> — applies to <which subtasks>
- **Gates:** <template name(s)> — <door-type each protects, which DAG node realises it>
- **Standing:** <template name(s) that apply to every subtask regardless, e.g. commit/handover/
  task-tracking/memory-capture>
- **Gap flagged:** none | <what obligation the stakes call for that no template covers — name it
  as a library issue, do not invent a substitute here>
```

## Gap-flagging, concretely

If Step 2 turns up a stakes-level obligation with no matching template (for example: an approval
shape the library hasn't modelled yet), do not draft ad hoc process text to cover it. Instead:

1. Name the missing template's intended purpose in the `Gap flagged` line above.
2. Note which DAG node needs it (so the gap is inherited when the library adds it later).
3. Leave that node's regime as the best available approximation from existing templates, clearly
   marked as provisional in the same line — never silently substitute a lesser gate and call it
   composed.

This keeps the library the single source of process truth: a missing template is surfaced for the
library's owner to add, not quietly worked around here, epic by epic.
