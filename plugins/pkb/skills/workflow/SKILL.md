---
name: workflow
description: Compose the process this piece of work runs under, by reading templates from the shipped library, the user's own layer, and the PKB's workflow templates. Read and compose in context — never parse, never solve. Fires whenever a dispatcher needs a process, and whenever an ask needs routing to the right one.
agent: "pauli"
---

# Workflow Composition

A workflow says **what steps this work takes and in what order**. A skill says
**how** one step is done. You compose the first from a library; you never write
the second here.

Templates are short markdown files you **read and compose by comprehension**.
They are not a rule language: there is no solver, no evaluation, no resolution
algorithm. You read the candidates, you understand what they oblige, and you
assemble a process for the work actually in front of you. A template that seems
to need parsing is a template being misused.

## The three layers

Resolved in this order; later layers win by **template name** — the filename on
disk, the permalink in the PKB.

1. **Shipped library** — [`../../workflows/`](../../workflows/). Process
   templates in `process/`, routed by [`../../workflows/INDEX.md`](../../workflows/INDEX.md).
2. **The user's layer** — `$ACA_DATA/.agents/workflows/`. A file here with the
   same name as a shipped template replaces it outright; a file with a new name
   extends the library. `$ACA_DATA` comes from the environment and has no
   default. If it is unset, or the directory does not exist, there simply is no
   user layer — that is not an error, and it is not something to work around.
3. **The PKB layer** — dynamic templates that live in the knowledge base, behind
   `get_document("pkb-workflow-index")`. Read the index, then `get_document` each
   template listed there that looks applicable.

A template from any of the three layers is the same kind of thing: the same four
frontmatter hints, one namespace resolved by name, later layers winning. The
`wf-*` obligation templates are a naming convention inside that namespace, not a
fixed or privileged set — treat one discovered in the PKB exactly as you treat a
shipped `process/` file.

**Resolving a bare name against the `wf-` convention.** A shipped template names
what it needs bare — `[[verification]]`, `[[human-approval]]` — while the PKB
carries the same template under its prefixed permalink, `wf-verification`. So a
name with no file in `process/` is not yet a gap: try it prefixed with `wf-` in
the PKB layer before you conclude anything. Every review obligation the shipped
library names resolves this way and no other, so an agent that skips the prefixed
lookup finds nothing, obliges no review, and reports a clean pass. Only a name
that resolves neither bare nor prefixed, in any layer, is the library gap.

**Never compose a template you have not read.** A catalogue row — in the shipped
index, in the PKB index, anywhere — tells you a template may exist and what it is
for. It is not the template. Read the document before composing its obligation
in, and where a row resolves to nothing, that row is the finding.

Reconcile the PKB layer once per composition: `list_documents(tag="wf-template")`
against the index's entries. A template tagged but unlisted, or listed but
unresolvable, is an index defect — **report it, do not repair it here and do not
route around it.** If the index document itself does not exist, compose from the
tag enumeration and report the missing index.

If a template you need exists in none of the three, that is a library gap.
**Name it. Do not freelance a process to fill it.**

## Route first

Read the decision tree in [`../../workflows/INDEX.md`](../../workflows/INDEX.md)
and route the ask to a process template.

Multiple intents in one prompt split and route independently — one template per
intent, never one blended process for all of them. If nothing matches, say so and
ask; do not force the nearest template onto work it was not written for.

## Then compose

Each template's frontmatter carries four hints. They are the whole vocabulary you
reason over:

- **`requires`** — fragments this template always pulls in.
- **`pairs-with`** — templates and gates composed **proportionate to stakes**,
  not always. This is where your judgment goes.
- **`recommends`** — a soft suggestion; take it or leave it, and say which.
- **`conflicts`** — mutually exclusive. If two routed intents conflict, they are
  two processes, not one.

Compose two things:

- The **outer** process: how this whole body of work reaches acceptance.
- The **inner** process, per subtask: how one unit reaches done.

**Door type is expressed as which templates get composed in.** There is no
separate reversibility mechanism — a one-way step is one that pulls in the
approval and review templates, and a two-way step is one that does not. When
reversibility is ambiguous, treat it as one-way.

Proportion is the whole skill. The same work under a heavier process than its
stakes warrant is process theatre; under a lighter one, it ships unreviewed.
Pick against real consequence, and say in one sentence why you picked what you
picked.

## Emit

Write the composed process onto an atomic task as its checklist, in the body
shape [`../../agents/pauli.md`](../../agents/pauli.md) states canonically: one
`- [ ] <step>` line per composed step, in order, plus one pointer bullet naming
the templates and the one-sentence proportionality call — never a paragraph
describing the process. A process referred to vaguely ("the usual review") is
not composed; nobody downstream can check it was followed, and a checklist line
nobody can point at a template for has nothing to audit against.

## Must not

- Parse, evaluate, or solve a template. Read it.
- Invent a process step that exists in no template because the work "seems
  risky". Under-coverage is a gap to name.
- Write how-to detail into a workflow. That is a skill; a workflow that explains
  how to do a step has swallowed one.
- Embed a workflow inside a skill. A skill may carry procedures — instructions
  meaningless outside that skill — but never orchestration.
- Hardcode a path to `$ACA_DATA`, or fall back to a default when it is unset.
- Carry a process in this skill's own text. Every template is loaded from a layer
  at runtime; one written down here is one the user can never override.
