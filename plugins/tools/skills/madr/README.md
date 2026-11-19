# MADR Skill

Markdown Architectural Decision Records (MADR) authoring skill for capturing architectural decisions, evaluated options, and downstream consequences.

## Overview

Architectural Decision Records capture point-in-time design deliberations, evaluated alternatives, and trade-offs. The `madr` skill provides instructions and a minimal template for structuring decisions according to the MADR standard.

## Attribution

This skill implements the Markdown Architectural Decision Records (MADR) format created by Oliver Kopp and contributors:

- Repository: [https://github.com/adr/madr](https://github.com/adr/madr)
- Specification: [https://adr.github.io/madr/](https://adr.github.io/madr/)

## Usage

Use `/madr` or invoke the `tools:madr` skill when:

- Designing a new subsystem or major component.
- Choosing between competing architectural patterns or technologies.
- Preserving the rationale for why an approach was adopted and why alternatives were rejected.

The skill provides the structural grammar and drafting instructions. Repository-specific conventions (such as storage directories, numbering schemes, and review processes) are defined by each repository's local project rules.

## Template

A minimal starting template is provided at [`template.md`](template.md).
