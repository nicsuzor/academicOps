---
name: workflow-library
type: skill
description: List, read, add, edit, and retire the workflow templates that `brief` composes from. Use whenever asked what workflows or templates exist, what one covers, whether a kind of work is already covered by a template, or to write, change, or retire one -- "list our workflows", "show me the workflow library", "what processes do we have", "manage our composable workflows". The library spans three tiers and has no registry, so this skill is the only surface that can see or maintain it. Not the harness's built-in `/workflows` progress viewer, which shows running multi-agent jobs and has nothing to do with templates.
---

# /workflow-library -- see and maintain the workflow library

A workflow template is any markdown document carrying `type: template`. `brief`
composes process out of them. This skill is the only surface that reports or
changes the library, so answer from the library itself -- never from an index, a
memory, or a previous listing.

## The three tiers

| Tier         | Where                         | Enumerate with                                 |
| ------------ | ----------------------------- | ---------------------------------------------- |
| 1. Project   | `$CWD/.agents/templates/*.md` | `ls`; absent directory means empty             |
| 2. PKB       | the graph                     | `pkb__list_documents(type="template")`         |
| 3. Universal | `../../workflows/*.md`        | `ls`, catalogued by `../../workflows/INDEX.md` |

Resolution is **project ≻ PKB ≻ universal**. Slugs match case-insensitively,
ignoring a `wf-` prefix and `_`/`-` differences: `feature-dev`, `wf-feature-dev`
and `wf_feature_dev` are one slug. A higher tier shadows a lower one whole --
never merge two tiers' text. Name the tier a template came from, and say what it
shadowed.

Enumerate every tier by running its command, every time. Describing what a tier
would contain reads as a listing and is worth nothing: if you did not run `ls`
against the project path you do not know whether it is empty, and you say that
rather than calling it empty. An absent project directory is the normal case --
report "no project tier here" and move on.

## Modes

Default to `list`.

### list -- what does the library cover?

Enumerate all three tiers and return one table: **slug · tier · what it covers ·
status**. One invocation, with no follow-up reading required of the reader.

Coverage lines come from the templates themselves, because a catalogue's
one-liner is a summary written once and never re-checked, and the two have
already drifted.

- Filesystem tiers (project, universal): the frontmatter `description`, read in
  one command rather than file by file:
  ```bash
  for f in <dir>/*.md; do echo "$(basename "$f" .md): $(sed -n 's/^description: //p' "$f")"; done
  ```
  A file that prints an empty description has no coverage line. Report that; do
  not substitute an index row or a sentence you compose yourself.
- PKB tier: there is no `description` field to read. Take the first sentence
  under `## What this step does`, or under the `## <slug> -- step: …` heading that
  fragments use. Roughly a third of the corpus has a coverage line under neither
  convention: fall back to the first body paragraph, mark the row as having no
  authored coverage line, and count those rows in your report. Never write the
  missing sentence yourself -- an invented coverage line is indistinguishable from
  an authored one on the next read.

Reading ~70 documents buries your context, so delegate the PKB tier to one
subagent that returns table rows only. The two filesystem tiers are one command
each; do them inline.

`../../workflows/INDEX.md` carries the routing tree and a
`Routes / Requires / Pairs with` table. Use it only for those routing
relationships, which live nowhere else. Never use it to say what a template
covers, and never as proof one exists.

Filter out datestamped instance nodes (`-20260820-1430-`), templates scoped to a
project other than this one, and any carrying `status: cancelled` -- and say how
many you filtered. A retired template is deleted, not marked, so none remain in
the corpus to filter.

Report these findings in the same pass, because listing is the only time anyone
looks:

- A template with no coverage line. It cannot be routed to.
- A catalogue row that resolves to no document, or a document absent from the
  catalogue.
- A slug resolving in more than one tier -- name the winner and the shadowed.

### view -- what does this one say?

Resolve the slug through the tiers, read the winner, and show it. State which
tier won and name every other tier the slug resolved in. If it resolves nowhere,
say so and list the near-misses rather than guessing which was meant.

### new -- add one

First run `list` and check the slug and the coverage: most asks for a new
template are asks for one that already exists.

Ask which tier it belongs in, because the answer is not derivable:

- **Project** -- specific to this repository, versioned with its code.
- **PKB** -- personal to Nic, portable across repositories.
- **Universal** -- a minimum standard every project inherits. It ships to
  everyone, so it goes through `framework-gate`.

Write it to the shape below, under about 100 lines. A template says what the
process obliges; explaining how to perform a step is a skill's job, and a
template that teaches technique has swallowed one.

Register it nowhere. Discovery is dynamic, and adding a registry row recreates
the gate the discovery contract repealed. The one exception is
`../../workflows/INDEX.md`'s routing tree for a universal template, which records
routing relationships rather than existence.

### edit -- change one

Read it first, then change it in place: one correct current version, no changelog
section, no dated append, no `.bak` file. What changed and why goes in the
commit.

> [!WARNING]
> Editing a PKB template: `get_document` output is not `update_body` input.
> `get_document` returns the title and frontmatter _above_ the body, so passing
> what it returned back into `update_body` writes a second literal copy of the
> frontmatter into the prose -- and returns success, so nothing tells you it
> happened. Send only the markdown body, starting below the closing `---`, then
> read the document back and confirm it has one frontmatter block.
> Filesystem-tier templates use the ordinary file tools and carry no such hazard.

### retire -- take one out of service

Before writing anything, search the graph for a task that already governs this
retirement (`pkb__task_search` on the template's name). Retirement is usually
already-considered work, and the record routinely carries sequencing the request
does not: a prerequisite that must land first, a durable lesson with nowhere to
go until it does, passages worth salvaging onto another template, other nodes
citing this one as a deliverable. If such a record exists and its prerequisites
are unmet, stop and say so -- report what blocks it and what would have been lost.

Retirement is a deletion. Name what supersedes it before deleting -- a template
retired with nothing named in its place leaves the work it covered with no
process, which `brief` correctly halts on -- then say the canonical id in the
commit or task record, since the retired document will no longer exist to
carry a `superseded_by` field.

1. Delete the document: remove the file for a filesystem-tier template, or
   delete the node (`pkb__delete`) for a PKB-tier template.
2. Remove its routing rows from `../../workflows/INDEX.md` if it is universal.

Retire one named template at a time, and confirm the name with the operator
before deleting. Never sweep the corpus retiring everything you judge stale: a
template you think is dead is load-bearing for someone, another agent may be
halted against its text right now, and deleting it under them breaks the halt
silently.

## Shape

```yaml
---
title: <human name>
type: template
category: process | gate
description: <one line: when to select this, and when not to>
tags: [...]
---
```

Body: what class of work it covers and when _not_ to select it; the steps or
obligations; what must be true to exit. A **process** template says how a class
of work proceeds. A **gate** template is an obligation that blocks acceptance;
those carry the `wf-` prefix and are composed into other templates.

Some templates are fragments -- sub-steps that only make sense composed into
another process, and that must never be dispatched standalone. In the PKB tier
the `planner-data` tag currently marks exactly the fragment set, so it is a good
first cut, but nobody enforces it; fragments also announce themselves in their
first heading (`## <slug> -- step: …`). Confirm against the document, because a
fragment mistaken for a dispatchable template sends a worker at half a process.
When you write a new fragment, say so in its body in plain words rather than
relying on a reader knowing what a tag means.

## Must not

- Answer "what is covered" from an index, a memory, or a previous listing.
- Treat a catalogue row as proof a template exists. Resolve it to a document.
- Register a new template in a registry.
- Merge two tiers' versions of one slug.
- Retire or reclassify a template the operator did not name.
- Compose a process, brief a task, or dispatch work. This skill maintains the
  library; `brief` uses it.
