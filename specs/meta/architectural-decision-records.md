---
title: Architectural Decision Records (MADR)
status: ready
---

# Architectural Decision Records (MADR)

Captures, structures, and preserves significant architectural decisions, evaluated alternatives, and downstream consequences in aOps using Markdown Architectural Decision Records (MADR). It serves developers, researchers, and reviewers by establishing an immutable, repository-local record of architectural choices in `specs/decisions/`, isolating point-in-time design deliberations from lean target-state specifications.

## User experience flow

```mermaid
flowchart LR
    Dev(["Developer / Researcher"]) -->|Proposes architectural choice| ADR["specs/decisions/NNNN-slug.md"]
    ADR -->|Updates index| Index["specs/decisions/INDEX.md"]
    Dev -->|Queries prior choices| Index
    Index -->|Inspects rationale on-demand| ADR
```

## Capabilities and user stories

### US-1 Record an architectural decision

As a developer or researcher designing a subsystem, I want to capture significant architectural choices in Markdown Architectural Decision Records (MADR), so that contributors and reviewers understand why the architecture was chosen and what alternatives were rejected.

- **AC-1.1** Given a significant architectural fork or design decision, when recorded, then it is authored as an immutable Markdown file adhering to the minimal MADR structure in `specs/decisions/NNNN-<slug>.md` with YAML frontmatter containing `status`, `date`, and `decision-makers`.
- **AC-1.2** Given an ADR document, when structured, then it contains concise sections for `Context and Problem Statement`, `Considered Options`, `Decision Outcome` with justification, and positive and negative `Consequences`.
- **AC-1.3** Given an accepted ADR, when placed in the workspace, then it resides in `specs/decisions/` named with a sequential number and kebab-case active-imperative slug (`NNNN-<slug>.md`) containing no personal names.
- **AC-1.4** Given an existing decision that is superseded or reversed, when a new decision is adopted, then the previous ADR's frontmatter status transitions to `superseded by ADR-NNNN`, a new ADR is minted capturing the updated context and trade-offs, and affected subsystem specifications in `specs/` are updated in the same PR to maintain atomic consistency.
- **AC-1.5** Given any commit that creates, modifies, deprecates, or supersedes an ADR, then `specs/decisions/INDEX.md` is updated in the same commit to prevent index drift.

### US-2 Inspect decision history without context window bloat

As a developer or auditor designing or evaluating a subsystem, I want to inspect a compact index of prior decisions, so that design tasks and agent prompts avoid re-evaluating rejected options without exhausting context windows.

- **AC-2.1** Given `specs/decisions/INDEX.md`, when queried for architectural history, then it provides a compact tabular summary (ID, Date, Title, Status, Summary Rationale) consuming approximately 40-50 tokens per decision entry.
- **AC-2.2** Given an active subsystem specification in `specs/`, when describing target behavior, then the specification states only current target behaviors and contracts without historical deliberations, optionally referencing governing decisions via frontmatter `decisions: [ADR-NNNN]` for traceability.
- **AC-2.3** Given a subsystem design task, when checking settled trade-offs, then `specs/decisions/INDEX.md` enables selective retrieval of only the specific ADR documents whose scope intersects the target subsystem.

## Shared interface contract

### Document Structure & Template Reference

Architectural decisions in aOps follow the minimal Markdown Architectural Decision Records (MADR) format defined in the `/madr` skill ([`plugins/tools/skills/madr/SKILL.md`](../../plugins/tools/skills/madr/SKILL.md)) and its minimal starting template ([`plugins/tools/skills/madr/template.md`](../../plugins/tools/skills/madr/template.md)).

In aOps repositories, MADRs carry the following repository-local conventions:

- **Frontmatter**: Standard YAML frontmatter specifying `status` (`proposed | accepted | rejected | deprecated | superseded by ADR-NNNN`), `date` (`YYYY-MM-DD`), and `decision-makers` (role names, e.g. `["framework-architect"]`).
- **Filenames**: Stored in `specs/decisions/` as `NNNN-<kebab-case-title>.md` (e.g. `specs/decisions/0001-use-madr-for-architectural-decisions.md`). The title is active imperative. Personal names and persona prefixes are strictly prohibited.
- **Brevity**: Decision documents are strictly concise (typically 40-80 lines).

## Document size management & two-level retrieval

To ensure contributors and agents understand settled trade-offs without ballooning context windows:

1. **Separation of Target State vs Rationale**:
   - Subsystem specifications (`specs/<subsystem>/<name>.md`) define target contracts and observable invariants. Specs carry zero historical debates or discarded options.
   - ADRs (`specs/decisions/`) define _why_ an architecture was chosen over alternatives.
   - Subsystem specifications remain lean and self-contained; specs may optionally declare governing decision IDs in YAML frontmatter (e.g. `decisions: [ADR-0001]`).
2. **Compact Decision Index (`specs/decisions/INDEX.md`)**:
   - Maintains a structured Markdown table summarizing all records: `ID`, `Date`, `Title`, `Status`, and `Summary Rationale` (a 1-sentence synopsis of ≤10 words).
   - Consumes approximately 40-50 tokens per entry (~2,500 tokens for 50 decisions).
3. **On-Demand Retrieval**:
   - Planning and design processes consult `specs/decisions/INDEX.md` during option generation.
   - The full ADR file is loaded only when its scope matches the active subsystem.

## Invariants and repository boundaries

1. **Project-Local Single Source of Truth**: All decision records reside in `specs/decisions/` and are committed directly to git alongside specifications and source code. No external databases, network services, or MCP servers are required to read or validate ADRs.
2. **Data Boundaries**: ADRs authored in the repository must never contain private PKB note identifiers, user machine paths, or internal telemetry URLs.
3. **Optional PKB Projection**: When operating in connected environments, agents may optionally project a node into the PKB graph using canonical node type `reference` (tag `adr`, `source: <repo-relative-path>`, and attributes `repo, adr_id, title, status`). The git repository remains the sole authoritative text.
4. **Atomic Index Synchronization**: Any commit that adds, modifies, deprecates, or supersedes an ADR must update `specs/decisions/INDEX.md` in the same commit.
5. **Atomic Spec Synchronization on Supersession**: When a new ADR supersedes an existing decision, any affected subsystem specifications in `specs/` whose target contracts change must be updated in the same PR.
