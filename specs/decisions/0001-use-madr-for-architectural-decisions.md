---
status: "accepted"
date: 2026-11-08
decision-makers: ["framework-architect", "james"]
---

# Use MADR for Architectural Decisions

## Context and Problem Statement

The aOps framework utilizes lean specifications (`specs/<subsystem>/<name>.md`) that define target system behaviors and contracts. Per `specs/meta/writing-specs.md`, specifications are strictly concise and carry no historical provenance, dead-end debates, or discarded alternatives. However, during system evolution and agent design tasks, agents and human contributors need to understand _why_ a particular architecture was chosen and _what alternatives were previously evaluated and rejected_.

Without a dedicated architectural decision mechanism, agents suffer from architectural amnesia, frequently re-proposing rejected options or introducing regressions. Conversely, attempting to embed decision histories directly into specifications causes context window bloat, violates the specification genre standard, and inflates routine token costs. Furthermore, aOps runs in third-party target repositories where external collaborators and CI environments lack access to a central Personal Knowledge Base (PKB).

## Decision Drivers

- **Version-Controlled Traceability**: Architectural choices, drivers, and rejected options must be tracked in git alongside code.
- **Context Budget Preservation**: Frequent operational runs and specification reads must remain lean and not suffer token exhaustion from historical deliberations.
- **Third-Party Workspace Portability**: The decision format must operate hermetically in external git repositories without requiring central PKB infrastructure or network credentials.
- **Agentic Usability**: Autonomous agents must easily parse the index table for pre-design checks and author structured decisions without complex external tooling.
- **Axiomatic Alignment**: Complies with `single-source-of-truth`, `proportionate`, `no-over-engineering`, and `data-boundaries`.

## Considered Options

- **Option 1: Project-Local MADR 4.0.0 (specs/decisions/ or docs/decisions/) with Two-Level Indexing**
- **Option 2: Inline Decision Deliberations Inside Feature Specifications**
- **Option 3: Centralized PKB-Only Decision Graph Nodes**
- **Option 4: Bespoke JSON/YAML Decision Registry with Custom CLI Tooling**

## Decision Outcome

Chosen option: "Option 1: Project-Local MADR 4.0.0 (specs/decisions/ or docs/decisions/) with Two-Level Indexing", because it cleanly separates target system contracts (in `specs/`) from historical rationale (in `specs/decisions/`), provides zero-dependency portability in third-party repositories, protects LLM context windows via a compact single-line index table (`INDEX.md`), and adheres to proven industry standards without adding custom code or maintenance burdens.

### Consequences

- Good, because specifications remain declarative and concise while architectural history is permanently preserved in git.
- Good, because agents can scan `INDEX.md` (~15 tokens per ADR) to avoid re-litigating settled trade-offs without loading full decision texts.
- Good, because third-party repositories and CI runners have 100% functionality with zero dependency on central PKB services.
- Good, because private PKB note IDs and personal infrastructure paths are completely prevented from leaking into public repositories.
- Bad, because cross-project querying across separate repositories requires scanning local directories or relying on an optional PKB projection.
- Bad, because agents must follow numbering hygiene (`NNNN-<slug>.md`) when creating concurrent records across git branches.

## Pros and Cons of the Options

### Option 1: Project-Local MADR 4.0.0 with Two-Level Indexing

- Good, because it adheres to the MADR standard, enabling compatibility with existing developer tools and IDE markdown viewers.
- Good, because `INDEX.md` enables two-level retrieval, solving the document size and context-window bloat dilemma.
- Good, because it requires zero executable code or CLI wrappers, adhering to `no-over-engineering` and `proportionate`.
- Bad, because sequential numbers may require conflict resolution during parallel branch merges.

### Option 2: Inline Decision Deliberations Inside Feature Specifications

- Good, because developers and agents only have to open a single file per feature.
- Bad, because it directly violates `specs/meta/writing-specs.md` ("No provenance... Non-goals, exclusions stay out").
- Bad, because every rejected idea expands the specification indefinitely, degrading prompt precision and burning tokens on every routine execution.
- Bad, because specifications become bloated historical diaries rather than crisp contracts.

### Option 3: Centralized PKB-Only Decision Graph Nodes

- Good, because it leverages existing graph-relationship decision structures (`alternative`, `settles` edges) and enables global search across all projects.
- Bad, because it completely breaks in third-party repositories where contributors and CI have no access to the user's private PKB.
- Bad, because committing private PKB node IDs into public repositories violates the `data-boundaries` axiom.
- Bad, because git history is decoupled from architectural rationale.

### Option 4: Bespoke JSON/YAML Decision Registry with Custom CLI Tooling

- Good, because structured data allows deterministic programmatic queries and validation.
- Bad, because building and maintaining custom CLI tools and parsers violates `no-over-engineering` and `judgment-non-delegable`.
- Bad, because plain Markdown is more natural and readable for both human reviewers and LLM agents (`human-readability-first`).

## More Information

Governed by [`specs/meta/architectural-decision-records.md`](../meta/architectural-decision-records.md). Composed during specification authoring via workflow template `wf-spec`.
