# Architectural Decision Records

This directory contains the immutable Architectural Decision Records (ADRs) for this project, formatted according to [Markdown Architectural Decision Records (MADR)](https://adr.github.io/madr/) and governed by [`specs/meta/architectural-decision-records.md`](../meta/architectural-decision-records.md).

## Decision Index

| ID | Date | Title | Status | Summary Rationale |
| :- | :- | :- | :- | :- |
| [ADR-0001](0001-use-madr-for-architectural-decisions.md) | 2026-11-08 | Use MADR for Architectural Decisions | Accepted | Track git-local rationale separately from specs without external PKB dependencies. |

## Guidance for Agents

- **Pre-Design Check**: Before authoring new specifications (`wf-spec`) or proposing architectural components, scan the table above to identify existing constraints, settled trade-offs, and previously rejected alternatives.
- **On-Demand Reading**: Read only the specific ADR files relevant to the active subsystem. Do not load all ADR files into routine operational contexts.
- **Authoring**: Use [`adr-template.md`](adr-template.md) to draft new decisions. Ensure titles are active imperative and filenames follow `NNNN-<slug>.md`.
