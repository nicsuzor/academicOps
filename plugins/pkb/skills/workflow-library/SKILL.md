---
name: workflow-library
type: skill
description: List, read, add, edit, and retire the workflow templates that `brief` composes from. Use whenever asked what workflows or templates exist, what one covers, whether some kind of work is already covered by a template, or to write, change, or retire one — including phrasings like "list our workflows", "show me the workflow library", "what processes do we have", "manage our composable workflows". The library spans three tiers and has no registry, so this skill is the only surface that can see or maintain it. Not to be confused with the harness's built-in `/workflows` progress viewer, which shows running multi-agent jobs and has nothing to do with templates.
---

# /workflow-library: see and maintain the workflow library

A workflow template is a short markdown document describing how a class of work
proceeds. `brief` §5 composes process out of them. Nothing else in the framework
lets a person see what the library holds or change it, so this skill is the only
surface for both.

You are answering for a reader who has never opened the library. Never send them
to an index to find out what is covered — an index is a claim about the library,
and this skill's whole job is to report the library.

## The three tiers

| Tier         | Where                                 | Enumerate with                                 |
| ------------ | ------------------------------------- | ---------------------------------------------- |
| 1. Project   | `$CWD/.agents/templates/*.md`         | `ls`; absent directory means empty             |
| 2. PKB       | graph documents with `type: template` | `pkb__list_documents(type="template")`         |
| 3. Universal | `../../workflows/process/*.md`        | `ls`, catalogued by `../../workflows/INDEX.md` |

**Resolution: project ≻ PKB ≻ universal.** Slugs match case-insensitively,
ignoring a `wf-` prefix and `_`/`-` differences: `feature-dev`, `wf-feature-dev`
and `wf_feature_dev` are one slug. A higher tier shadows a lower one whole; never
merge two tiers' text. Always name the tier a template came from, and say what it
shadowed.

Absence of the project directory is the normal case, not a fault. Report it as
"no project tier here" and move on.

## Modes

Pick from what was asked. Default to `list`.

### list — what does the library cover?

Enumerate all three tiers and return one table: **slug · tier · what it covers ·
status**. One invocation, no follow-up reading required of the reader.

**Coverage lines come from the templates themselves, never from a catalogue.**
A catalogue's one-liner is a summary of a summary, written once and never
re-checked; the template's own `description` is what its author last stood
behind. The two have already drifted.

- Filesystem tiers (project, universal): the frontmatter `description`. One
  command reads all of them at once — do not open the files one by one and do
  not reach for the index instead:
  ```bash
  for f in <dir>/*.md; do echo "$(basename "$f" .md): $(sed -n 's/^description: //p' "$f")"; done
  ```
  A file that prints an empty description has no coverage line. Report it; do
  not substitute a row from the index or a sentence you compose yourself.
- PKB tier: there is no `description` field to read — one document out of 47 has
  one. Take the first sentence under `## What this step does` where it exists
  (about half the corpus), or under the `## <slug> — step: …` heading fragments
  use. **Roughly a third of PKB templates have no coverage line under any
  convention.** For those, fall back to the first body paragraph, mark the row as
  having no authored coverage line, and count them in your report. Do not write
  the missing sentence yourself: an invented coverage line is indistinguishable
  from an authored one on the next read.

`../../workflows/INDEX.md` carries the routing tree and a
`Routes / Requires / Pairs with` table. Use it for the routing relationships,
which live nowhere else — which templates require or pair with which. Never use
it to say what a template covers, and never as proof one exists.

Reading ~70 documents will bury your context. **Delegate the PKB tier** to one
subagent and have it return the table rows only. The two filesystem tiers are
one command each; do them inline.

Report these as findings in the same pass, because listing is the only time
anyone looks:

- A template with no coverage line. It cannot be routed to and is effectively
  invisible.
- A catalogue row that resolves to no document, or a document absent from the
  catalogue.
- A slug resolving in more than one tier — name the winner and the shadowed.
- A retired template still carrying no retirement marker (see **retire**).

Filter out, and say how many you filtered: retired documents, datestamped
instance nodes (`-20260820-1430-`), and templates scoped to a project other than
this one.

**Retirement is not reliably in the frontmatter.** Some templates are retired
only in their body — an opening `# RETIRED` heading, or a `## Retired —
superseded by …` section — with no `status` field and no `retired` tag. A filter
that reads frontmatter alone will compose them. Read each document's opening
lines, and treat `status: cancelled` as retired too. Where you find one, say so:
it is a document that needs its marker fixed, and until it is, every other
composing pass will keep picking it up.

### view — what does this one say?

Resolve the slug through the tiers, read the winner, and show it. State which
tier won and name every tier the slug also resolved in. If it resolves nowhere,
say so and list the near-misses rather than guessing which was meant.

### new — add one

First establish it is not already covered: run `list` and check the slug and the
coverage. Most asks for a new template are asks for one that exists.

Ask which tier it belongs in, because the answer is not derivable:

- **Project** — specific to this repository, versioned with its code.
- **PKB** — personal to Nic, portable across repositories.
- **Universal** — a minimum standard every project inherits. This is a framework
  change: it ships to everyone, so it goes through `framework-gate`.

Write it to the shape the tier uses (see **Shape** below). Keep it under about
100 lines. A template says what the process obliges; it never explains how to
perform a step — that is a skill's job, and a template that teaches technique has
swallowed one.

Do not register it anywhere. Discovery is dynamic; there is no registry to add a
row to, and adding one recreates the gate the discovery contract repealed. The
one exception is `../../workflows/INDEX.md`'s routing tree for a universal template, which
records routing relationships rather than existence.

### edit — change one

Read it first. Change it in place: one correct current version, no changelog
section, no dated append, no `.bak` file. Say what changed and why in the commit,
not in the document.

> [!WARNING]
> **Editing a PKB template: `get_document` output is not `update_body` input.**
> `get_document` returns the title and frontmatter _above_ the body. Passing what
> it returned back into `update_body` writes a second literal copy of the
> frontmatter into the prose — and returns success, so nothing tells you it
> happened. Send only the markdown body, starting below the closing `---`, and
> read the document back after writing to confirm it has one frontmatter block.
> Filesystem-tier templates are edited with the ordinary file tools and have no
> such hazard.

### retire — take one out of service

**Before writing anything, search the graph for a task that already governs this
retirement** (`pkb__task_search` on the template's name). Retirement is usually
already-considered work, and the record routinely carries sequencing the request
does not: a prerequisite that must land first, a durable lesson that has nowhere
to go until it does, passages worth salvaging onto another template, and other
nodes citing this one as a deliverable. Retiring ahead of that order does not
just skip steps — it destroys the reason the node was still worth reading.

If such a record exists and its prerequisites are unmet, **stop and say so.** The
retirement is not yours to perform yet. Report what blocks it and what would have
been lost.

Retirement is a marker on the document, not a deletion. A composing pass excludes
a template when it carries **either** `status: retired` **or** a `retired` /
`superseded` tag, so set both — a document with only one is a document that half
the passes still compose.

1. Frontmatter: `status: retired`, `superseded_by: <canonical-id>`, and add
   `retired` to `tags`.
2. Body, at the top:
   ```markdown
   > [!IMPORTANT]
   > **RETIRED**: superseded by [[<canonical-id>]]. Do not compose.
   ```
3. Remove its routing rows from `../../workflows/INDEX.md` if it is a universal template.

Name what supersedes it. A template retired with nothing named in its place
leaves the work it covered with no process, which `brief` will correctly halt on.

**Retire one named template at a time, and confirm the name with the operator
before writing.** Never sweep the corpus retiring everything you judge stale. A
template you think is dead is load-bearing for someone: another agent may be
halted against its text right now, and changing it under them breaks the halt
silently.

## Shape

Frontmatter:

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
obligations; what must be true to exit. A **process** template says how a class of
work proceeds. A **gate** template is an obligation that blocks acceptance — those
carry the `wf-` prefix and are composed into other templates.

Some templates are fragments: sub-steps that only make sense composed into
another process, and that must never be dispatched standalone. In the PKB tier
the `planner-data` tag currently marks exactly the fragment set and nothing else,
so it is a good first cut — but it is a convention nobody enforces, and the
fragments also announce themselves in their own first heading
(`## <slug> — step: …`). Confirm against the document. A tag is a hint, never the
answer, and a fragment mistaken for a dispatchable template sends a worker at
half a process.

When you write a new fragment, say so in its body in plain words. Do not rely on
a reader knowing what a tag means.

## Must not

- Answer "what is covered" from an index, a memory, or a previous listing.
  Enumerate the tiers.
- Treat a catalogue row as proof a template exists. Resolve it to a document.
- Register a new template in a registry, or restore the rule that a PKB template
  exists only once it is listed.
- Merge two tiers' versions of one slug. The winner shadows the loser whole.
- Retire or reclassify a template the operator did not name.
- Compose a process, brief a task, or dispatch work. This skill maintains the
  library; `brief` uses it.
