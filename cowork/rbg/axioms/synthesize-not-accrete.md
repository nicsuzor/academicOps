---
description: A durable store holds synthesised current state, not accreted history.
trigger: off
---

## Synthesise, Don't Accrete

A durable store — the PKB above all, and any document, spec, or note meant to be read again — holds current state, synthesised. It is not an append log.

- Writing a fact means reading what is already there, integrating it, and leaving one correct document. Never append a new version beside the old one.
- Prohibited content: timestamped history entries, decision logs, changelogs, deprecation notices, "formerly known as" notes, "as of \<date\>" qualifiers, migration commentary, notes about what a thing used to be called or used to do, and meta-commentary about the writing process itself (why a section was added, what was cut, how the document evolved).
- When a fact changes, the document states the new fact. That the old fact was once believed is not part of the record.

History lives in version control and the session transcript — surfaces that are append-only by construction. It does not live in the knowledge store, and a task record is not exempt: a task body is a checklist of work to be done, rewritten in place as items complete, never a log of what happened. A workflow template is not exempt either: it states the current process, never the prior one it replaced. Target nodes (`type: target`) are pure graph weight and carry no state or measurement logs.

A date-stamped observation left unsynthesised is accretion, not knowledge: it sits beside the topic note it should have updated, competing with it in search and going stale the moment either one changes. Synthesise every observation into the topic note's current-state prose in the same write, or remove it — never let it stand alone. Problems and bugs go on GitHub only.
