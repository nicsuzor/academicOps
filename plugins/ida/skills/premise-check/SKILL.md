---
name: premise-check
description: Judge a report's logic or author a report argument before sending -- parser-valid Argdown over extraction and map, with world evidence basis vocabulary, the ask as main conclusion, stopping rules, and verdict recording. Use when receiving a report, before passing any claim up the chain, or when authoring receipts for a handback. Not a fact check (never opens pointers), and not a review that adds requirements.
allowed-tools: Read, Write, Edit
---

# Premise Check

Evaluate a report's logic or author a report argument before sending. Core syntax and parser validation come from `ida:argument-extraction`. Charitable reconstruction and delivery checks come from `ida:argument-map` ("Reconstruct" and "Check before delivering"). This skill adds only the world evidence basis vocabulary, the ask as main conclusion with stopping rules, what travels up the chain, and verdict recording.

## Authoring and Shape

Every report resting on evidence ends in a parser-valid Argdown argument. Frontmatter carries the report envelope in reserved keys:

```argdown
===
title: The incoming ask being answered
author: agent-name
date: 2026-10-12
abstract: The outcome in plain prose.
model:
  mode: strict
===

[Outcome]: The answer to the ask.

<Check>: Verification of stated findings

(1) [Pinpoint fact]: Stated finding. {basis: "observed", pointer: "owner/repo@sha:path:line"}
(2) [Exhaustive search]: Bounded search finding. {basis: "exhaustively-searched", pointer: "query in path -> 0 hits"}
-- Rule name {uses: [1, 2], basis: "reported-by", pointer: "node-id"} --
(3) [Outcome]
```

### Conventions and Metadata

- **Metadata envelope**: `{basis, pointer, source?}` in Argdown YAML braces. Quoted strings are unescaped; pointers carry verbatim locators (`owner/repo@sha:path:line`, span id, PR URL, node id).
- **Basis vocabulary**: `observed`, `exhaustively-searched`, `attempted-and-failed`, `reported-by`, `assumed`, `stated`.
- **Warrants are inference rules, not premises**: Write warrants inside the expanded inference `--` line with `uses: [n, ...]` and inference metadata (`basis: "reported-by"` with pointer for authority-backed rules; `basis: "assumed"` for author's own rules). Never use `#warrant` premises.
- **Conclusion forms**:
  - Comparative or ranking claims require a comparison premise over named alternatives.
  - Negative or capability claims require `basis: "exhaustively-searched"` or `basis: "attempted-and-failed"`.
  - Causal claims require a mechanism premise, or soften to "consistent with".
  - Universal claims require a mechanism premise, or narrow.
  - Normative claims require a stated warrant.
  - Conclusion scope must lie within the intersection of premise scopes.

## Truth Boundary

Observed premises (`observed`, `exhaustively-searched`, `attempted-and-failed`, `reported-by`) with a pointer are accepted as given. The checker never opens a pointer and never re-determines an observed fact. Everything else -- warrants, inference steps, scope, and the fit between rule and case -- the checker judges and rules on.

When a ruling turns on an unstated fact, do not fetch it from sources: return REVISE naming the missing premise so the author supplies it with a pointer.

## Proportionality: Three Tests

Evaluate steps in this order and record which test ruled on each warrant:

1. **Materiality**: Examine a step only if changing its conclusion alters what the reader or next agent does. Immaterial steps are not examined.
2. **Sufficiency**: Accept a warrant as stated without further decomposition when any condition holds:
   - (a) **Obvious**: trivial deduction (conjunction, instantiation, arithmetic).
   - (b) **Authority-backed**: `basis: "reported-by"` pointing to an axiom, skill, decision, or PKB node (applicability to premises is checked; the rule itself is not).
   - (c) **Low-stakes**: material claim that is cheap to reverse.
     A warrant that is complex, unbacked, AND high-stakes is sent back for one level of decomposition.
3. **Necessity**: Reject a warrant only when the objection changes the conclusion in this case. Generality, wording, or alternative routes are never grounds for rejection.

## Stopping Rules and Upward Abstraction

- **Stopping rule downward**: Dispatch or send back until the argument answering the ask has no `#missing` on a material step.
- **Stopping rule for detail**: Expand a premise only if it is material and fails sufficiency.
- **Main conclusion**: The ask is the main conclusion of every layer's argument. An outcome narrower than the ask is `#missing` at the top step.
- **Upward abstraction (two moves)**:
  1. A receiver's argument takes each accepted downstream Outcome as one premise `{basis: "reported-by", pointer: "<verdict id>"}` and drops downstream premises the next reader accepts without challenge.
  2. A supervisor synthesises the Outcomes of all its dispatches into one argument whose main conclusion answers its incoming ask.
- **What travels up**: Facts retain their pointers at every layer where they are premises of a material step. Judgments collapse to one premise `{basis: "reported-by", pointer: "<verdict id>"}`.

## Verdict and Vocabulary

Evaluate the charitable reconstruction (referencing `ida:argument-map` "Reconstruct" and "Check before delivering"):

| Token  | Meaning                                                                                                                                                                                                                     |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | Charitable reconstruction needs no `#missing` on a material step, carries no undercut, and leaves no `#conflict` or `#unanswered`.                                                                                          |
| REVISE | Names a step and one of `#missing` (unstated necessary step), `#conflict` (contradiction or `><`), `#unanswered` (unmet objection), an undercut (`_>` rejecting a warrant with reason), or a narrowing (recorded decision). |
| FAIL   | The main conclusion does not answer the ask.                                                                                                                                                                                |

No criterion addresses style, granularity, or splitting.

## Gate and Verdict Recording

An incoming peer report arms the premise-check gate. The gate blocks dispatch, messaging, and task completion until a verdict is recorded:

```bash
python3 <path/to/verdict.py> --claim <claim_id> --verdict PASS --reason "<why>" [--title "<short_title>"]
```

From this repo's root, use `plugins/ida/skills/premise-check/scripts/verdict.py`. Use `--reason-file <path>` (or `-` for stdin) when the reason contains multi-line text or quotes.
