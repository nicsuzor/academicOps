---
id: workflows-template-library
title: Workflow Template Library
type: spec
category: workflow
status: ready
tags: [spec, workflow, templates, library, composition]
related: [[workflows-task-pipeline]]
---

# Workflow Template Library

The shared substrate every pipeline stage composes from. The library is a peer library at `plugins/pkb/workflows/`, consumed by stages like `hydrate` and `brief` alike, rather than living inside any single skill.

## What a template is

A short, clearly-labelled markdown file a smart agent reads and composes **in-context, by comprehension** — never parsed or solved. There are two kinds:

- **Process templates** — how a class of work proceeds (feature-dev, peer-review, email-triage, investigation…). Carry: routing signals, NOT-this signals, unique steps, exit routing.
- **Gate templates** — reusable QA/vetting/approval obligations (verification, qa, outbound-review, commit/handover, human-approval…). These are the units the door-type policy selects among: _two-way vs. one-way door is expressed as which gate templates get composed in_, one vocabulary for proportionate process everywhere.

## Requirements

1. **Peer location, single index.** The library sits outside any one skill. One index file gives name + one-line routing description per template (the metadata layer agents scan). Project-local extension directories override/extend, as today.
2. **Short and composable.** Each template must be small enough that several compose comfortably in a context window (target ≲100 lines). Substance that grows beyond that belongs in a skill the template points to — a template orchestrates, a skill executes (Principle #0 retained).
3. **Minimal dependency vocabulary.** `requires` / `pairs-with` / `conflicts` / soft `recommends` as frontmatter hints the composer reasons over. No solver, no richer ontology.
4. **Declared stakes.** Gate templates state the door-type/conditions they exist for and their skip-conditions, so composition proportionate-to-stakes is legible, not folk knowledge.
5. **Revisable baselines.** Templates are standardised work, not law: versioned, improved from execution feedback (dogfooding, /learn findings), with the index as the single registration point.
6. **Authoring bar.** Template prose follows the authoring discipline (intent + AC, no micro-scripting) and is reviewed by `/craft` before registration.
