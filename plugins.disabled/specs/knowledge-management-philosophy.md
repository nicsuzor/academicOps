---
title: Knowledge Management Philosophy
permalink: knowledge-management-philosophy
type: spec
category: spec
status: draft
tags: [knowledge-management, pkb, design]
---

# Knowledge Management Philosophy

Capture everything. Deliver just-in-time. This states the constraints a
knowledge store must satisfy to serve that; the write and synthesis rules
themselves are axioms ([`durable-capture`](../../lib/axioms/durable-capture.md),
[`synthesize-not-accrete`](../../lib/axioms/synthesize-not-accrete.md)) and are
not restated here.

## Storage substrate

Non-negotiable properties of the store. Every design decision must preserve
them.

| #  | Property                                                             | Why                                                              |
| -- | -------------------------------------------------------------------- | ---------------------------------------------------------------- |
| S1 | Readable in a text editor with no tooling                            | No lock-in; survives any tool failure                            |
| S2 | Markdown with YAML frontmatter and wikilinks                         | Works with Obsidian, VS Code, GitHub, and whatever comes next    |
| S3 | Git-native versioning                                                | Time travel, incremental backup, diff-friendly                   |
| S4 | Syncable a subset at a time, without full-repo operations            | Works on slow links and selective device sync                    |
| S5 | The files **are** the data, not a cache of a database                | Resilient, inspectable, portable                                 |
| S6 | Capture from agent conversations is automatic and needs no prompting | Conversations generate insight that manual extraction would lose |

**Every smart feature is an overlay, never a replacement.** Semantic search,
embeddings, an MCP server, a graph index — each is derived from the markdown
files and rebuildable from them. If the overlay dies, the files remain fully
usable, which is what makes S1–S5 hold under a store that gets cleverer over
time.

## Why capture is comprehensive rather than selective

Academic work generates cross-cutting themes that span decades — copyright work
from 2006 resurfacing in ML copyright in 2024 — so future relevance is not
predictable at capture time. Three alternatives were tried and rejected:

| Approach            | Why it fails                                                            |
| ------------------- | ----------------------------------------------------------------------- |
| Selective capture   | Can't predict future relevance; triage drains energy; loss is permanent |
| Folder hierarchies  | Cross-cutting themes don't fit; retrieval needs the structure recalled  |
| Proactive summaries | Overload, wrong detail level, delivered when not needed                 |

The trade this makes is explicit: storing everything is only tractable because
retrieval is semantic. The old constraint was "store less because search is
hard"; the standing bet is "store everything because search is good". A
retrieval layer that stops being good invalidates the capture policy, so search
quality is a first-class obligation, not an optimisation.

## Retrieval

- **Query-driven, never anticipatory.** Information surfaces in response to a
  need. Every unrequested notification is an interruption; a query costs nothing
  when nobody asks.
- **Depth on demand.** Answer at title level, then summary, then observations,
  then relations, then full text — escalating only when the caller needs more.
- **Temporal context is first-class metadata,** not just a `created` date:
  active period, completion date, and current-versus-historical relevance. Over
  a multi-decade store, undated archives pollute every current-domain query.
