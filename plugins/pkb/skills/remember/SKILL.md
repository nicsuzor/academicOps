---
name: remember
description: Write knowledge into the PKB and keep it worth trusting. Capture mode persists facts, decisions, and state as they emerge; consolidation mode turns episodic records into durable knowledge and repairs what has drifted. Every write integrates into what is already there and leaves one correct document.
---

# Remember

This skill is the write boundary for `synthesize-not-accrete`
(`lib/axioms/synthesize-not-accrete.md`). A task body is the rule's strictest
instance — goal, checklist, pointers, canonical in
[`../../agents/pauli.md`](../../agents/pauli.md) — where a
knowledge note carries synthesised prose instead, never accreted history in any
form.

The vocabulary you write in — node types, edges, status, weights — is the one
the PKB MCP tool schemas declare (`pkb__create`, `pkb__create_task`, `pkb__update_task` hosted under the `services` MCP server, e.g. `mcp__services__pkb__*`). Read
the schema of the tool you are about to call and write in its terms.
What a good note looks like is [`references/quality.md`](references/quality.md).

> [!NOTE]
> PKB MCP tools may be hosted on the **`services`** MCP server under the `pkb__` tool name prefix.

## Invariants

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

1. **Search** — `pkb__search(query="<topic>")` (`ServerName: "services"`, `ToolName: "pkb__search"`).
2. **Check for the canonical note.** Exactly one note per first-class topic —
   tool, project, skill, agent, concept. If one exists for this topic area, you
   **must** augment it. A broader canonical note covering the area means no new
   note gets created.
3. **Augment** — integrate the new observation into the existing structure and
   rewrite the section it belongs in (`pkb__update_body`). `pkb__append` only where the
   content is genuinely additive and supersedes nothing. Never a new dated
   section bolted on the end. A note reads as current state, never as a
   changelog.
4. **Or create**, only when nothing matches — `pkb__create` for a document,
   `pkb__create_memory` for an atomic memory. Topical, never a session or date file.

Scale the write to the work: one decision is a bullet on an existing note; a few
outcomes are observations on an existing topical note; a genuinely new topic
earns a new note.

Route by kind: agent activity and debug traces stay in the transcript — the
audit surface — and do not enter the PKB at all; what reaches the task is a
checked-off checklist item, or, where the checklist itself changed, the line
rewritten to match — never a narrated delta. Durable episodic records — meeting
notes, daily notes — are saved with the right type. Durable knowledge becomes a
topic note, in prose. Never create a timestamped session log.

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
- Typed relations on a **note** go in a `## Relationships` section:
  `- [related] [[task-id]] — one line on why`. Not on a task body: there the
  relation is a real graph edge (`depends_on`, `supersedes`, `contributes_to`)
  and anything else is one bullet under `## Pointers`. A prose section
  restating an edge is a parallel copy that drifts.
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

## Route what the write surfaces

Capture and consolidation surface work this skill does not own. Invoke the
owning skill now, in this session, as part of the write — do not perform its
work yourself, and do not leave it as a suggestion in your final message.

- **Something went wrong** — friction, a failure, an instruction or contract
  that misled — record the facts, then invoke the `learn` skill (`/pkb:learn`)
  on the incident. Learn owns the diagnosis and where the lesson lands.
- **New work, or an open decision** that needs situating, sizing, or
  decomposition — create the task (`pkb__create_task`, status `inbox`) so the
  graph holds the hook, then invoke the `brief` skill (`/pkb:brief`) on it.
- **If the owning skill cannot be invoked** — not in this agent's skill list,
  or the user has said stop — the inbox node is the fallback contract: it
  exists, carries its edges, and names the owning skill in its body.

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
topic note, then rewrite the body to goal, checklist, pointers.

**Consolidation is synthesis, not collection.** Merging five memories into a list
of five bullets adds nothing over the five memories. Synthesis means finding the
connection the sources do not state — the principle they are all instances of.
If you cannot name one, the material is not ready to consolidate.

When a knowledge note **fully** replaces a memory, delete the memory. When the
source is a primary episodic record — a daily note, a meeting note — mark its
frontmatter `consolidated: <date>` and advance its status, but never change its
content. Primary records are not rewritten. A task body is not a primary
record: it is a checklist, and consolidation rewrites it to one.

## Must not

- Write a dated section onto an existing note.
- Create a second note on a topic that already has a canonical one.
- Leave a superseded note in place with a pointer instead of merging and deleting.
- Assert anything without provenance.
- Modify the content of a primary episodic record.
- Cancel or archive anything because it is old. **Age is not a staleness signal.**
  Only irrelevance established from content justifies retirement, and where that
  is a judgment call, surface it rather than deciding.
- Leave a surfaced incident or follow-on with neither the owning-skill
  invocation nor an inbox node that names it.
