---
name: remember
description: Write knowledge into the PKB and keep it worth trusting. Capture mode persists facts, decisions, and state as they emerge; consolidation mode turns episodic records into durable knowledge and repairs what has drifted. Every write integrates into what is already there and leaves one correct document.
agent: "aops-pkb:pauli"
---

# Remember

The PKB holds **current state, synthesised**. It is not an append log, and it is
not a diary.

Writing a fact means reading what is already there, integrating the new fact, and
leaving **one** correct document. When a fact changes, the document states the
new fact; that the old one was once believed is not part of the record. This is
the `synthesize-not-accrete` axiom, and it is the reason this skill exists in the
shape it does.

**Prohibited content, in every write:** timestamped history entries, dated
session sections, progress logs, decision logs, changelogs, deprecation notices,
"formerly known as" notes, "as of \<date\>" qualifiers, migration commentary, and
`superseded_by:` pointers left behind instead of a merge. The audit surface is
separate and outside the PKB: session transcripts and telemetry hold what
happened; version control holds what changed. Nothing episodic enters the PKB —
and a task body is the strictest case of the rule.

The vocabulary you write in is
[`../graph-maintenance/references/taxonomy.md`](../graph-maintenance/references/taxonomy.md).
What a good note looks like is [`references/quality.md`](references/quality.md).

## Invariants

- **Writes go through the PKB tools.** Never `Write` or `Edit` a file under
  `$ACA_DATA` — direct filesystem writes bypass indexing, deduplication, and the
  write boundary. Never `Glob` or `Grep` it either; `search` is the instrument.
- **Search before you write.** Every time, including before asserting a fact you
  think you already know.
- **Never fabricate.** Extract what a source actually states or clearly implies.
  Never editorialise — record what happened and what was learned, not opinions
  about what should be done differently.
- **Preserve contradictions.** A new observation that contradicts an existing one
  gets recorded alongside it, with both sources and a flag. Do not overwrite
  silently and do not pick a winner on your own authority.

## Capture

Capture continuously, as facts emerge. If the user has to say "can you save
that?", you have already failed. Do not announce it, do not interrupt to ask, do
not wait for the end of the session.

What earns a write: decisions and their reasoning, facts about systems and people
and processes, techniques, patterns that recur across sources, constraints,
strategic insight, and ideas ruled out with the reason why. What does not:
implementation minutiae that git already holds, routine status, debugging steps
that generalise to nothing.

**The sequence is mandatory.**

1. **Search** — `search(query="<topic>")`.
2. **Check for the canonical note.** Exactly one note per first-class topic —
   tool, project, skill, agent, concept. If one exists for this topic area, you
   **must** augment it. A broader canonical note covering the area means no new
   note gets created.
3. **Augment** — integrate the new observation into the existing structure and
   rewrite the section it belongs in (`update_body`). `append` only where the
   content is genuinely additive and supersedes nothing. Never a new dated
   section bolted on the end. A note reads as current state, never as a
   changelog.
4. **Or create**, only when nothing matches — `create` for a document,
   `create_memory` for an atomic memory. Topical, never a session or date file.

Scale the write to the work: one decision is a bullet on an existing note; a few
outcomes are observations on an existing topical note; a genuinely new topic
earns a new note.

Route by kind: agent activity and debug traces stay in the transcript — the
audit surface — and do not enter the PKB at all; what reaches the task is the
synthesized state delta (what is now true, decided, or next), written by
rewriting the body section it changes. Durable episodic records — meeting
notes, daily notes — are saved with the right type. Durable knowledge becomes a
topic note. Never create a timestamped session log.

Report what you wrote: the tool, the title, the returned id. Not filesystem
paths.

### Reconciliation is part of the write

Search for duplicate and peer notes as you write. Merge the unique content into
the stronger note, update the wikilinks that pointed at the weaker one, and
**delete** the weaker one. Git holds the history. Do not leave a superseded file
behind carrying a pointer — that is duplication with extra steps.

### Graph integration

- Every note carries at least one `[[wikilink]]` in prose to a parent concept,
  project, goal, or entity. A note nothing links to is a note nobody will find.
- Wikilink proper nouns. Use markdown links for external issues and PRs.
- Wikilinks in prose only — never inside code blocks, inline code, or technical
  tables. No "See Also" section; links live where the thing is discussed.
- Typed relations go in a `## Relationships` section:
  `- [related] [[task-id]] — one line on why`.
- Capture the generalisable pattern, not the local implementation detail.
- Factual claims in an episodic note carry an observation callout:

  ```
  > [!observation] The factual statement
  > Source: [[source-note]]
  > Confidence: <0.0–1.0>   (≥0.8 established · 0.4–0.79 provisional · <0.4 speculative)
  ```

- A `type: knowledge` note carries provenance in frontmatter: `sources`,
  `synthesized`, `last_reviewed`, `confidence`, and
  `maturity: seedling|budding|evergreen`.
- A Map of Content is earned, not scheduled: five or more real notes on one
  topic, `type: moc`.

## Consolidate

Turn episodic records into durable knowledge, and repair what has drifted. Run on
an explicit request or a scheduled cycle.

Full procedure: [`references/consolidation.md`](references/consolidation.md).

The shape of it:

```
daily notes · meeting notes · transcripts                    (episodic)
        ↓  identify the first-class topic each insight is about
canonical topic notes                                        (durable)
        ↓  once a topic area has five or more
Maps of Content                                              (navigation)
```

A task body found carrying an episodic log — dated sections, resume stacks,
progress entries — is drift. Repair it: lift anything durable into the right
topic note, then rewrite the body as pure current state.

**Consolidation is synthesis, not collection.** Merging five memories into a list
of five bullets adds nothing over the five memories. Synthesis means finding the
connection the sources do not state — the principle they are all instances of.
If you cannot name one, the material is not ready to consolidate.

When a knowledge note **fully** replaces a memory, delete the memory. When the
source is a primary episodic record — a daily note, a meeting note — mark its
frontmatter `consolidated: <date>` and advance its status, but never change its
content. Primary records are not rewritten. A task body is not a primary
record: it is a state document, and consolidation rewrites it.

**Consolidation mode mutates the graph.** `batch_merge`, `merge_node`,
`batch_reparent`, `batch_reclassify`, and `batch_archive` all need pauli's tool
grant, and they all default to `dry_run=true` — a call that omits it previews and
changes nothing.

## Must not

- Write a dated section onto an existing note.
- Create a second note on a topic that already has a canonical one.
- Leave a superseded note in place with a pointer instead of merging and deleting.
- Assert anything without provenance.
- Modify the content of a primary episodic record.
- Cancel or archive anything because it is old. **Age is not a staleness signal.**
  Only irrelevance established from content justifies retirement, and where that
  is a judgment call, surface it rather than deciding.
