---
title: Architectural Decision Records (MADR)
status: ready
---

# Architectural Decision Records (MADR)

Captures, structures, and preserves significant architectural decisions, their evaluated alternatives, and downstream consequences across aOps workspaces using Markdown Architectural Decision Records (MADR). It serves planning and design agents, review supervisors, implementing workers, and human developers by establishing an immutable, version-controlled record of architectural choices that remains fully portable across both native framework repositories and third-party target workspaces.

## User stories

### US-1 Record an architectural decision

As an architect or agent designing a subsystem, I want to capture a significant architectural choice in a standardized MADR format, so that downstream implementers and reviewers understand why the architecture was chosen and what alternatives were rejected.

- **AC-1.1** Given a significant architectural fork or design decision, when recorded, then it is authored as an immutable Markdown file adhering to the MADR 4.0.0 structure with YAML frontmatter containing `status`, `date`, and `decision-makers`.
- **AC-1.2** Given an ADR document, when structured, then it contains concise sections for `Context and Problem Statement`, `Decision Drivers`, `Considered Options`, `Decision Outcome` with justification, and positive and negative `Consequences`.
- **AC-1.3** Given an accepted ADR, when placed in the workspace, then it resides in the project decision directory (`specs/decisions/` in native aOps repositories, or `docs/decisions/` in third-party projects) named with a sequential number and kebab-case active-imperative slug (`NNNN-<slug>.md`) containing no personal names.
- **AC-1.4** Given an existing decision that is superseded or reversed, when a new decision is adopted, then the previous ADR's frontmatter status transitions to `superseded` referencing the new ADR ID, a new ADR is minted capturing the updated context and trade-offs, and affected subsystem specifications in `specs/` are updated in the same PR to maintain atomic consistency.
- **AC-1.5** Given any commit that creates, modifies, deprecates, or supersedes an ADR, then `specs/decisions/INDEX.md` (or `docs/decisions/INDEX.md`) is updated in the same commit to prevent index drift.

### US-2 Inspect decision history without context window bloat

As an agent initiating a design or planning task, I want to discover previously evaluated options and architectural constraints without loading hundreds of full decision documents, so that my active context window remains lean while avoiding re-proposing rejected options.

- **AC-2.1** Given a workspace containing ADRs, when an agent queries architectural history, then it inspects a compact index table (e.g. `specs/decisions/INDEX.md` or `docs/decisions/INDEX.md`) containing one-line summaries with status, core rationale, and pointers, consuming approximately 40–50 tokens per decision entry.
- **AC-2.2** Given an active subsystem specification in `specs/`, when describing target behavior, then the specification states only current target behaviors and contracts without historical deliberations, optionally referencing governing decisions via frontmatter `decisions: [ADR-NNNN]` for traceability.
- **AC-2.3** Given an agent evaluating architectural alternatives during planning or design, when inspecting prior decisions, then the decision index enables selective retrieval of only the specific ADR documents whose scope intersects the target subsystem.

### US-3 Deploy portably in third-party target workspaces

As a developer or agent working in an external target repository outside the core framework repo, I want architectural decision records to function entirely within the local repository using native file and git operations, so that decision records travel with the codebase and work in third-party CI pipelines without leaking private knowledge base identifiers.

- **AC-3.1** Given an external repository with no connection to an external PKB, when an agent creates, indexes, or reads ADRs, then all operations execute using local filesystem and git operations without errors, fallbacks, or external network calls.
- **AC-3.2** Given an ADR authored for publication or version control in a target workspace, when validated, then it contains no private PKB note identifiers, user machine paths, or private deployment domains, adhering strictly to data boundary invariants.
- **AC-3.3** Given a connected environment where PKB graph services are active, when an ADR is accepted in a project workspace, then the agent optionally projects an external reference pointer to the PKB graph linking to the local repository path without duplicating ADR body text into the PKB.

## Design

### 1. Document Structure & Template

Architectural decisions follow the MADR (Markdown Architectural Decision Records) 4.0.0 bare-minimal format adapted for aOps agentic conventions:

```markdown
---
status: "{proposed | accepted | rejected | deprecated | superseded by ADR-NNNN}"
date: YYYY-MM-DD
decision-makers: ["role-name"]
---

# {Active imperative title: e.g. Use SQLite for Session State}

## Context and Problem Statement

{2-4 sentences defining the architectural challenge, constraints, and operational context.}

## Decision Drivers

- {Driver 1: e.g. Low-latency local read performance}
- {Driver 2: e.g. Zero external daemon dependencies}

## Considered Options

- {Option 1: Title}
- {Option 2: Title}
- {Option 3: Title}

## Decision Outcome

Chosen option: "{Option 1}", because {justification explaining why this option satisfies decision drivers better than the alternatives}.

### Consequences

- Good, because {positive architectural consequence}
- Bad, because {trade-off, operational overhead, or accepted limitation}

## Pros and Cons of the Options

### {Option 1}

- Good, because {advantage}
- Bad, because {disadvantage}

### {Option 2}

- Good, because {advantage}
- Bad, because {disadvantage}
```

Metadata and naming constraints enforce consistency:

- **Filenames**: `NNNN-kebab-case-title.md` (e.g. `specs/decisions/0001-use-madr-for-architectural-decisions.md` in native aOps repositories, or `docs/decisions/0001-*.md` in third-party projects). The title is active imperative. Personal names and persona prefixes are prohibited in titles and filenames.
- **Frontmatter**: Standard YAML fields: `status`, `date`, `decision-makers`. When superseded, `status` becomes `superseded by ADR-NNNN`.
- **Brevity**: ADR documents are strictly concise (typically 40–100 lines). Extensive historical logs or large code snippets belong in external branch diffs or benchmark artifacts, not the ADR body.

### 2. Document Size Management & Two-Level Retrieval

Frequent reading of large decision logs exhausts LLM context windows and degrades prompt precision. To ensure agents understand what has been tried and decided before without ballooning context tokens, the framework implements a two-level retrieval architecture:

```
┌────────────────────────────────────────────────────────┐
│ Level 1: Compact Decision Index (INDEX.md)             │
│ - 1-line summary per ADR (ID, title, status, reason)   │
│ - Injected/read during design intake (~40–50 tok/ADR)  │
└──────────────────────────┬─────────────────────────────┘
                           │ Agent selects relevant ADR
                           ▼
┌────────────────────────────────────────────────────────┐
│ Level 2: Isolated ADR Files (specs/decisions/NNNN-*.md)│
│ - Full context, options, pros/cons, consequences       │
│ - Loaded on-demand only for matching subsystems        │
└────────────────────────────────────────────────────────┘
```

1. **Separation of Target State vs Rationale**:
   - Subsystem specifications (`specs/<subsystem>/<name>.md`) define _what_ the system does and its observable invariants. Specs carry no historical provenance, dead-end debates, or discarded options.
   - ADRs define _why_ a specific architecture was chosen over alternatives.
   - Subsystem specifications remain self-contained and uncoupled from historical debates. To support lean traceability, subsystem specifications may optionally declare governing decision IDs in YAML frontmatter (e.g. `decisions: [ADR-0001]`), but must not inline rationale, debates, or superseded options into specification prose.
2. **Compact Decision Index (`INDEX.md`)**:
   - The decision directory maintains an `INDEX.md` containing a structured Markdown table summarizing all records.
   - Each row specifies: `ID`, `Date`, `Title`, `Status`, and `Summary Rationale` (a 1-sentence synopsis of why the winning option was chosen and what primary alternative was rejected).
   - An index of 50 decisions consumes fewer than 2,500 tokens, enabling comprehensive historical awareness during feature planning without significant token spend.
3. **On-Demand Retrieval**:
   - Planning and design processes instruct agents to consult the decision index during initial option generation.
   - If a proposed technology or architectural approach matches an existing or superseded decision, the agent reads that specific ADR file to examine documented failure modes and trade-offs.

### 3. Repository-Local SSoT & Third-Party Deployment Support

aOps workflows execute across diverse repository topologies, from the core framework repository to private academic codebases, student projects, and isolated container environments. Third-party deployment requires strict architectural independence:

1. **Project-Local Git Repository as Single Source of Truth (SSoT)**:
   - The decision directory resides within the target workspace's root (`specs/decisions/` in native aOps repositories, or `docs/decisions/` in third-party projects).
   - Every decision record is committed directly to the project's git repository alongside the source code and specifications it governs.
   - No external database, network service, or MCP server is required to read, write, or validate ADRs. External collaborators, CI runners, and polecat containers operate without credentials or network tunnels.
2. **Data Boundaries Invariant**:
   - Decision records authored in target repositories must never include private personal knowledge base (PKB) identifiers, private machine paths, user names, or internal telemetry URLs.
   - All references within ADRs use repository-relative paths (`specs/`, `src/`) or public RFC/documentation URLs.
3. **Optional PKB Projection**:
   - When an agent operates in a privileged environment with active PKB connectivity, it may project an index node into the PKB graph using canonical node type `reference` (with tag `adr`, `source: <repo-relative-path>`, and attributes `repo`, `adr_id`, `title`, `status`).
   - The PKB node acts as a catalog pointer for cross-project search across the user's portfolio; the project-local repository remains the canonical authoritative text.

### 4. Decision Lifecycle & Evolution

Architectural decision records transition through defined lifecycle states:

1. **Inception & Proposal**: When an architectural fork with multiple viable alternatives arises, a draft ADR is initialized (`status: proposed`).
2. **Alternative Evaluation**: Candidate options are evaluated against explicit decision drivers, documenting distinct trade-offs, advantages, and drawbacks for each option.
3. **Adoption & Review**: Upon review approval, the chosen option is documented with its deciding justification and the ADR status transitions to `accepted`.
4. **Superseding**: When subsequent empirical evidence, scale shifts, or evolving requirements warrant replacing an existing architecture, a new ADR is drafted. Upon acceptance of the successor decision, the predecessor ADR's frontmatter status transitions to `superseded by ADR-NNNN`, preserving an unbroken historical lineage of architectural evolution without overwriting past rationale.

### 5. Synchronization Invariants

To avoid split-brain architectural states and silent index drift:

1. **Atomic Index Synchronization**: Any commit that adds, modifies, deprecates, or supersedes an ADR must update `specs/decisions/INDEX.md` (or `docs/decisions/INDEX.md`) in the same commit, ensuring the compact table remains an exact mirror of the decision directory.
2. **Atomic Spec Synchronization on Supersession**: When a new ADR supersedes an existing decision, any affected subsystem specifications in `specs/` whose target contracts change as a result must be updated in the same PR, preventing discrepancies between active behavioral contracts and recorded architectural rationale.
3. **Specification Frontmatter Traceability**: Subsystem specifications may optionally include a frontmatter `decisions` sequence (e.g. `decisions: [ADR-0001]`) pointing to governing ADRs. Specifications state current contracts without historical narrative.
