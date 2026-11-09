---
status: "accepted"
date: 2026-11-08
decision-makers: ["framework-architect", "review-supervisor"]
---

# Use MADR for Architectural Decisions

## Context and Problem Statement

The aOps framework utilizes lean specifications (`specs/<subsystem>/<name>.md`) defining target system behaviors and contracts. Per `specs/meta/writing-specs.md`, specifications are concise and carry no historical provenance, dead-end debates, or discarded alternatives. However, during subsystem design and architectural evolution, developers and reviewers need to understand _why_ an architecture was chosen and _what alternatives were previously evaluated and rejected_.

Without an architectural decision mechanism, contributors face architectural amnesia, repeatedly re-evaluating rejected options or introducing regressions. Conversely, embedding decision histories into specifications causes context window bloat and violates specification standards.

## Decision Drivers

- **Version-Controlled Traceability**: Track architectural choices, drivers, and rejected options in git alongside code.
- **Context Budget Preservation**: Keep specifications lean and protect LLM context windows during routine runs.
- **Zero External Dependencies**: Operate entirely within git without requiring external databases, daemons, or network credentials.
- **Agentic Usability**: Enable fast tabular scans during pre-design checks.
- **Axiomatic Alignment**: Complies with `single-source-of-truth`, `proportionate`, `no-over-engineering`, and `data-boundaries`.

## Considered Options

- **Option 1: Repository-Local MADR 4.0.0 (specs/decisions/) with Two-Level Indexing**
- **Option 2: Inline Decision Deliberations Inside Feature Specifications**
- **Option 3: Centralized PKB-Only Decision Graph Nodes**
- **Option 4: Bespoke JSON/YAML Decision Registry with Custom CLI Tooling**

## Decision Outcome

Chosen option: "Option 1: Repository-Local MADR 4.0.0 (specs/decisions/) with Two-Level Indexing", because it cleanly separates target system contracts (in `specs/`) from historical rationale (in `specs/decisions/`), provides zero-dependency git-local traceability, protects LLM context windows via a compact index table (`INDEX.md`), and adheres to proven industry standards without adding custom code or maintenance burdens.

### Consequences

- Good, because specifications remain declarative and concise while architectural history is permanently preserved in git.
- Good, because developers and agents can scan `INDEX.md` (~40–50 tokens per ADR) to avoid re-litigating settled trade-offs without loading full decision texts.
- Good, because git-local operation requires zero external services or PKB dependencies.
- Good, because private PKB note IDs and personal infrastructure paths are completely prevented from leaking.
- Bad, because sequential numbers may require conflict resolution during parallel branch merges.

## Pros and Cons of the Options

### Option 1: Repository-Local MADR 4.0.0 with Two-Level Indexing

- Good, because it adheres to the MADR standard, enabling compatibility with developer tools and markdown viewers.
- Good, because `INDEX.md` enables two-level retrieval, solving the context-window bloat dilemma.
- Good, because it requires zero executable code or CLI wrappers, adhering to `no-over-engineering` and `proportionate`.
- Bad, because sequential numbers may require conflict resolution during parallel branch merges.

### Option 2: Inline Decision Deliberations Inside Feature Specifications

- Good, because contributors open a single file per feature.
- Bad, because it violates `specs/meta/writing-specs.md` ("No provenance... Non-goals, exclusions stay out").
- Bad, because specifications become bloated historical diaries rather than crisp contracts.

### Option 3: Centralized PKB-Only Decision Graph Nodes

- Good, because it leverages graph-relationship decision structures for global queries.
- Bad, because committing private PKB node IDs into repository files violates the `data-boundaries` axiom.
- Bad, because git history is decoupled from architectural rationale.

### Option 4: Bespoke JSON/YAML Decision Registry with Custom CLI Tooling

- Good, because structured data allows programmatic queries.
- Bad, because custom CLI tools and parsers violate `no-over-engineering` and `judgment-non-delegable`.
- Bad, because plain Markdown is more natural and readable for both human reviewers and LLM agents (`human-readability-first`).

## More Information

Governed by [`specs/meta/architectural-decision-records.md`](../meta/architectural-decision-records.md). Composed during specification authoring and architectural design.
