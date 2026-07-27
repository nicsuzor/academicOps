---
description: A durable store holds synthesised current state, not accreted history.
trigger: always_on
---

## Synthesise, Don't Accrete

A durable store — the PKB above all, and any document, spec, or note meant to be read again — holds current state, synthesised. It is not an append log.

- Writing a fact means reading what is already there, integrating it, and leaving one correct document. Never append a new version beside the old one.
- Prohibited content: timestamped history entries, decision logs, changelogs, deprecation notices, "formerly known as" notes, "as of \<date\>" qualifiers, migration commentary, and notes about what a thing used to be called or used to do.
- When a fact changes, the document states the new fact. That the old fact was once believed is not part of the record.

History lives in version control, the task record, and the session transcript — surfaces that are append-only by construction. It does not live in the knowledge store.
