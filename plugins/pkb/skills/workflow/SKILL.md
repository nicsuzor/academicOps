---
name: workflow
description: Compose the process this piece of work runs under, by reading templates from the shipped library, the user's own layer, and the PKB's workflow templates. Read and compose in context — never parse, never solve. Fires whenever decompose or a dispatcher needs a process, and whenever an ask needs routing to the right one.
agent: "aops-pkb:pauli"
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

Resolved in this order; later layers win by **filename**.

1. **Shipped library** — [`../../workflows/`](../../workflows/). Process
   templates in `process/`, routed by [`../../workflows/INDEX.md`](../../workflows/INDEX.md).
2. **The user's layer** — `$ACA_DATA/.agents/workflows/`. A file here with the
   same name as a shipped template replaces it outright; a file with a new name
   extends the library. `$ACA_DATA` comes from the environment and has no
   default. If it is unset, or the directory does not exist, there simply is no
   user layer — that is not an error, and it is not something to work around.
3. **Workflow templates in the PKB** — the `wf-*` gates. These are **not files**.
   They live in the PKB as documents tagged `wf-template` and are discovered at
   runtime: `list_documents(tag="wf-template")` to enumerate, `get_document(id)`
   to read one. The library index names the ones it expects, but the PKB is the
   authority — never compose a `wf-*` obligation from the index table alone, and
   never assume a template exists because the index mentions it.

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

Name the composed process explicitly on the task — the templates by name, the
order, and the one-sentence proportionality call. A process referred to vaguely
("the usual review") is not composed; nobody downstream can check it was
followed, and the evaluator has nothing to audit against.

State it once, as the current process. When the process changes, restate it —
do not leave the superseded version beside the new one with a note about which
came first.

## Must not

- Parse, evaluate, or solve a template. Read it.
- Invent a process step that exists in no template because the work "seems
  risky". Under-coverage is a gap to name.
- Write how-to detail into a workflow. That is a skill; a workflow that explains
  how to do a step has swallowed one.
- Embed a workflow inside a skill. A skill may carry procedures — instructions
  meaningless outside that skill — but never orchestration.
- Hardcode a path to `$ACA_DATA`, or fall back to a default when it is unset.
