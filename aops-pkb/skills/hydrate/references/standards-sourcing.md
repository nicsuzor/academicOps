# Standards Sourcing — Report, Don't Compose

`Standards` answers one question: _what QA/review/quality obligations does this class of work
carry?_ You report them; you do not sequence, weight, or compose them into a process — that
composition (selecting and ordering gate/process templates proportionate to stakes) is
`decompose`'s job (see `20-skill-requirements.md` §3).

## Sources, in order

1. **`aops/workflows/INDEX.md` and PKB Workflow Templates** — Read the routing table and
   descriptions in `aops/workflows/INDEX.md` to identify candidate process and workflow templates.
   Because workflow templates (`wf-*` gates) live dynamically in the PKB, you must query the PKB
   (using `pkb__list_documents(tag="wf-template")`) to discover them and fetch their contents
   (using `pkb__get_document(id="wf-...")`) to verify their applicability and stakes.
   If a needed template is missing from both the index and the PKB, report that as a library gap.
2. **Project-local standards** — `.agents/rules/*.md` (e.g. `cite-sources.md`,
   `evidence-immutable.md`, `single-source-of-truth.md`) and any `AXIOMS.md` in the project root, if
   present. These are per-project overrides/extensions, same pattern as the old
   `.agent/WORKFLOWS.md` project-local convention.
3. **Durable memory** — a `retrieve_memory` hit that states a standing constraint (e.g.
   "[[feedback_never_merge_external_without_approval]]") counts as a Standard, not just Context, if
   it's a _process obligation_ rather than a fact. Judgment call: if it changes what the downstream
   worker is allowed to do, it's a Standard; if it's merely useful background, it's Context.

## Output shape

Name the obligation and its source, one bullet each:

```markdown
## Standards

- Outbound-facing deliverable → human review before external send (INDEX.md: outbound-review gate;
  also `.agents/rules/cite-sources.md` for any cited claims).
- No standing standard found beyond general PKB hygiene — flag to decompose: confirm no template
  gap before composing the regime.
```

If nothing applies, write "No applicable standards found beyond general quality practice" — don't
omit the heading (see `SKILL.md` Step 3).

## What NOT to do

- Don't pick _one_ template and call it "the workflow" — that's composing a regime, not reporting
  obligations. List every obligation you find; let `decompose` choose and sequence.
- Don't invent a gate that isn't in the index or project rules because the work "seems risky" —
  under-coverage is a library gap to name, not license to freelance a process.
