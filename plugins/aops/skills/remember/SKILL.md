---
name: remember
description: Write knowledge into the PKB and keep it worth trusting. Capture mode persists facts, decisions, and state as they emerge; consolidation mode turns episodic records into durable knowledge and repairs what has drifted. Use it for anything worth remembering — a decision and its reasoning, a fact about a system or a person, a technique, a constraint, an idea ruled out — and for "save that", "consolidate the graph", "clean up these notes". Every write integrates into what is already there and leaves one correct document. Not for filing bugs (GitHub issues), and not for agent activity or debug traces, which stay in the transcript.
---

# Remember

This skill is the write boundary for `synthesize-not-accrete`
(`lib/axioms/synthesize-not-accrete.md`). A knowledge note carries synthesised
prose stating current state, never accreted history in any form.

Write in the vocabulary the PKB MCP tool schemas declare -- node types, edges,
status, weights. The tools may be hosted bare or under the `services` server with
the `pkb__` prefix (`mcp__services__pkb__*`); read the schema of the tool you are
about to call and write in its terms. What a good note looks like is
[`references/quality.md`](references/quality.md). Prioritisation, severity, and
edge weights follow [[kb_pauli_prioritisation_doctrine]]; importance-measure
authority follows [[kb_ccc17177]].

## Invariants

- **Search before you write.** Every time, including before asserting a fact you
  think you already know.
- **Never fabricate.** Extract what a source actually states or clearly implies.
  Record what happened and what was learned, not opinions about what should have
  been done differently.
- **Preserve contradictions.** A new claim that contradicts an existing one gets
  recorded alongside it, with both sources and a flag. Do not overwrite silently,
  and do not pick a winner on your own authority.
- **Target nodes never hold state.** `type: target` nodes carry purely graph
  weight -- contribution edges and severity magnitude. No current-state sections,
  measurement logs, or "as at" findings.
- **Task files hold no state.** Task bodies are work checklists rewritten in
  place; the graph as a whole is not a log.
- **Observations are not PKB content.** An observation is either synthesised into
  durable knowledge that is the single source of truth for what it claims, or it
  is removed. No undigested notes.
- **Bugs go on GitHub only.** System, tooling, and framework defects are GitHub
  issues, never PKB node bodies, appended findings, or "current state" sections.
- **Age is not a staleness signal.** Never cancel or archive anything because it
  is old. Only irrelevance established from content justifies retirement, and
  where that is a judgment call, surface it rather than deciding.

## Capture

Capture continuously, as facts emerge. If the user has to say "can you save
that?", you have already failed. Do not announce it, do not interrupt to ask, and
do not wait for the end of the session. For turn-level and session-handover
capture, the bounded capture floor in [`../../agents/pauli.md`](../../agents/pauli.md)
governs as a subordinate special case and caps what may be written.

What earns a write: decisions and their reasoning, facts about systems and people
and processes, techniques, patterns that recur across sources, constraints,
strategic insight, and ideas ruled out with the reason why. What does not:
implementation minutiae git already holds, routine status, and debugging steps
that generalise to nothing.

**The sequence is mandatory.**

1. **Search** -- `pkb__search(query="<topic>")`.
2. **Check for the canonical note.** Exactly one note per first-class topic --
   tool, project, skill, agent, concept. If one exists for this topic area you
   **must** augment it; a broader canonical note covering the area means no new
   note gets created.
3. **Augment** -- rewrite the section the fact belongs in so the note states
   **current state only** (`pkb__update_body`). A superseded fact is replaced, not
   annotated: no dated blocks, no "previously X", no correction notices, no
   provenance narration. Keep bodies short enough that a full rewrite is cheap --
   that is what makes this affordable, and why `pkb__append` is not needed.
   Evidence grounding a claim gets its own node and a `[[wikilink]]`; the claim
   itself stays one plain attributed sentence.
4. **Or create**, only when nothing matches -- `pkb__create` for a document,
   `pkb__create_memory` for an atomic memory. Topical, never a session or date
   file.

Scale the write to the work: one decision is a bullet on an existing note; a few
outcomes are observations on an existing topical note; a genuinely new topic earns
a new note.

Route by kind. Agent activity and debug traces stay in the transcript -- the audit
surface -- and do not enter the PKB at all; what reaches the task is a checked-off
checklist item, or the line rewritten to match where the checklist itself changed,
never a narrated delta. Durable episodic records -- meeting notes, daily notes --
are saved with the right type. Durable knowledge becomes a topic note, in prose.
Never create a timestamped session log.

Report what you wrote: the tool, the title, the returned id. Not filesystem
paths. Where a session produced nothing durable, say so explicitly -- a
declared zero beats a forced write.

### Reconciliation is part of the write

Search for duplicate and peer notes as you write. Merge the unique content into
the stronger note, update the wikilinks that pointed at the weaker one, and
**delete** the weaker one -- git holds the history. A superseded file left behind
carrying a pointer is duplication with extra steps.

### Graph integration

- **Exhaustively densify relationships.** An isolated note with a single parent
  link is a failure. When creating or updating a node, actively search
  (`pkb__search`, `pkb__semantic_neighbors`) for deeper theoretical frameworks,
  peer concepts, and relevant Maps of Content to wire into. Every note carries
  multiple `[[wikilink]]` pointers in prose. A note nothing links to is a note
  nobody will find.
- Wikilink proper nouns; use markdown links for external issues and PRs. Wikilinks
  go in prose only -- never inside code blocks, inline code, or technical tables --
  and there is no "See Also" section: links live where the thing is discussed.
- Typed relations on a **note** go in a `## Relationships` section:
  `- [related] [[node-id]] -- one line on why`. Never on a task body: there the
  relation between two tasks is a real graph edge (`depends_on`, `supersedes`,
  `contributes_to`, parentage) and nothing else, because a prose copy of an edge
  is a parallel source of truth that drifts while the edge stays correct.
  Wikilinks in a task body point at knowledge the executor must open, never at
  tasks.
- Capture the generalisable pattern, not the local implementation detail.
- A `type: knowledge` note carries provenance in frontmatter: `sources`,
  `synthesized`, `last_reviewed`, `confidence`, and
  `maturity: seedling|budding|evergreen`.
- A Map of Content is earned, not scheduled: five or more real notes on one topic,
  `type: moc`.

## Route what the write surfaces

Capture and consolidation surface work this skill does not own. Invoke the owning
skill now, in this session, as part of the write -- do not perform its work
yourself, and do not leave it as a suggestion in your final message.

- **Something went wrong** -- friction, a failure, an instruction or contract that
  misled -- record the facts, then invoke `learn` (`/aops:learn`) on the incident.
  Learn owns the diagnosis and where the lesson lands.
- **New work, or an open decision** that needs situating, sizing, or
  decomposition -- create the task (`pkb__create_task`, status `inbox`) so the
  graph holds the hook, then invoke `brief` (`/aops:brief`) on it.
- **If the owning skill cannot be invoked** -- not in this agent's skill list, or
  the user has said stop -- the inbox node is the fallback contract: it exists,
  carries its edges, and names the owning skill in its body.

## Consolidate

Turn episodic records into durable knowledge, and repair what has drifted. Run on
an explicit request or a scheduled cycle. Read
[`references/consolidation.md`](references/consolidation.md) and follow it; the
shape of it is:

```
daily notes · meeting notes · transcripts                    (episodic)
        ↓  identify the first-class topic each insight is about
canonical topic notes                                        (durable)
        ↓  once a topic area has five or more
Maps of Content                                              (navigation)
```

A task body found carrying an episodic log -- dated sections, resume stacks,
progress entries -- is drift. Repair it: lift anything durable into the right topic
note, then rewrite the body to goal, checklist, pointers. The same repair applies
to notes, and to three forms that list misses: a retained "superseded" or
"historical" block, a correction notice, and provenance narration ("derived
from …"). Delete all three -- what was durable in them is already a plain sentence
of current state, or it is evidence and belongs in its own node. **Length is the
diagnostic**: a body too long to rewrite in one pass is the defect, not a reason
to append.

**Consolidation is synthesis, not collection.** Merging five memories into a list
of five bullets adds nothing over the five memories. Synthesis means finding the
connection the sources do not state -- the principle they are all instances of. If
you cannot name one, the material is not ready to consolidate.

When a knowledge note **fully** replaces a memory, delete the memory. When the
source is a primary episodic record -- a daily note, a meeting note -- delete it
once its knowledge is verified at the destination note. A task body is not a
primary record: it is a checklist, and consolidation rewrites it to one.
