---
status: "accepted"
date: 2026-11-08
decision-makers: ["framework-architect", "review-supervisor"]
---

# Use MADR for Architectural Decisions

## Context and Problem Statement

Lean specifications in `specs/` define target system behaviors and contracts without historical provenance or discarded alternatives. However, during subsystem design and architectural evolution, developers and reviewers need to understand why an architecture was chosen and what alternatives were evaluated and rejected without bloating specifications or context windows. How should the framework capture and preserve architectural decisions in a version-controlled, zero-dependency, and context-efficient manner?

## Considered Options

- Core `/madr` skill with repository-local records (`specs/decisions/`) and two-level indexing
- Inline decision deliberations inside feature specifications
- Centralized PKB-only decision graph nodes
- Bespoke JSON/YAML decision registry with custom CLI tooling

## Decision Outcome

Chosen option: "Core `/madr` skill with repository-local records (`specs/decisions/`) and two-level indexing", because it cleanly separates target system contracts (in `specs/`) from point-in-time rationale (in `specs/decisions/`), provides generic format guidance through the `/madr` skill in `plugins/tools/` for optional 3P adoption, keeps repository-local conventions in `.agents/rules/`, protects LLM context windows via a compact index table (`specs/decisions/INDEX.md`), and operates entirely within git without adding executable code or external service dependencies.

### Consequences

- Good, because specifications remain declarative contracts while architectural trade-offs are permanently preserved in git.
- Good, because developers and agents can scan `specs/decisions/INDEX.md` (~40-50 tokens per ADR) to avoid re-evaluating settled choices without loading full decision texts.
- Good, because third-party repositories can optionally adopt the minimal MADR format via `plugins/tools/skills/madr/` while defining their own local conventions.
- Good, because git-local operation requires zero external services and prevents private data leakage.
- Bad, because sequential numbers in `NNNN-<slug>.md` may require manual conflict resolution during parallel branch merges.
