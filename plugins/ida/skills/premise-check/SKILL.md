---
name: premise-check
description: Author or verify an agent handback report argument in standardised Chained Toulmin Argdown -- enforcing basis vocabulary, the ask as main conclusion, non-flat inference chains, contrast testing, granularity stopping rules, and verdict recording. Use when receiving a subagent report, passing verified claims up the chain, or authoring handback receipts. Not a fact check or requirement review, and not for extracting a text's argument (use argument-extraction).
---

# Premise Check

Author or verify report arguments so every handback receipt links observed facts to `[Outcome]` through explicit warrants, bounded scopes, and stopping rules. Read `ida:argdown-toulmin` first: it sets the grammar, basis vocabulary, observed-value rule, tags, and parser validation.

## When to Use

- Ending an evidence-backed subagent or task report with a verifiable handback argument concluding `[Outcome]`
- Auditing an incoming report from a subagent or workflow step before accepting its claim or passing it upstream
- Recording a formal `PASS`, `REVISE`, or `FAIL` verdict on a report claim
- Messaging peers: a message carries something the receiver acts on or is not sent; a message that only confirms receipt is not sent

## Report Shape

End every evidence-backed report with a parser-valid Argdown block concluding `[Outcome]`, the direct answer to the incoming ask. Handback receipts follow the syntax rules directly; do not run an external parser CLI or write a test script to validate the block during handback:

```argdown
===
title: Incoming ask summary
author: agent-name
date: 2026-10-14
abstract: One-sentence outcome in plain prose.
granularity:
  level: micro
  floor: "Accept pinpoint observed values and bounded search counts with verbatim pointers as leaf nodes."
model:
  mode: strict
===

[Outcome]: Direct, scope-matched answer to the ask.

<Verification>: How the evidence establishes the outcome.

(1) [Pinpoint Fact]: Stated finding with deciding value (`status: MERGED`). {basis: "observed", pointer: "owner/repo@sha:path:line"}
(2) [Search Bound]: Bounded negative or scope finding (`0 hits`). {basis: "exhaustively-searched", pointer: "rg 'pattern' path/ -> 0 hits"}
-- Warrant: Why (1) and (2) together rule out alternatives and establish (3) {uses: [1, 2], basis: "reported-by", pointer: "doc-or-rule-id"} --
(3) [Outcome]
```

## Matching Basis to Claim Type

- _Rankings / comparisons_ require explicit comparison premises covering the alternatives.
- _Negatives / absences / capabilities_ require `basis: "exhaustively-searched"`, `"attempted-and-failed"`, or `"method-bounded"` stating the exact search boundary or instrument limit.
- _Causal / universal claims_ require an explicit mechanism in the bar and a conclusion scope no wider than the premises' scope.

## Formal Check and Granularity Stopping Rules

When verifying an incoming report, accept `observed` and `exhaustively-searched` leaf premises with valid pointers and observed values as given (do not re-open files or re-run searches):

1. **Format Kickback (`REVISE` `#format`)**: If a report lacks a parser-valid block concluding `[Outcome]`, or breaks the standard's premise cap or warrant placement, return `REVISE` (`#format`) before checking substance.
2. **Scope Check (`REVISE` `#scope-drift`)**: Run Check A (Term and Scope Alignment) as `ida:argument-audit` defines it on `[Outcome]` and each load-bearing bar.
3. **Contrast Test (`REVISE` `#unanswered`)**: Run Check D (The Contrast Test) as `ida:argument-audit` defines it on each load-bearing bar, and name the exact step and the unexcluded rival state.
4. **Relayed Directions Check**: When a premise cites `'direction...' (derived from: ask summary [source:id])`, verify that the direction follows from the cited ask and flag any invented constraints.
5. **Granularity Floor and Proportionality Stopping Rule**: Hold strictly at `granularity.floor`. Do not demand sub-arguments for obvious definitions, authority-backed rules (`basis: "theory"` or `"reported-by"`), or low-stakes warrants where flipping the warrant would not alter `[Outcome]`. Recurse or kick back only when a material `#missing`, `#scope-drift`, `#conflict`, or `_>` undercut changes the conclusion. Synthesise accepted outcomes upward as `{basis: "reported-by", pointer: "<verdict-id>"}`, preserving pinpoint pointers for material facts.

## Recording the Verdict

- **PASS**: `[Outcome]` directly answers the ask with no material `#missing`, `#scope-drift`, undercut (`_>`), `#conflict` (`><`), or `#unanswered`.
- **REVISE**: Specify the exact step (`(n)` or `-- Warrant --`), the tag (`#format`, `#missing`, `#scope-drift`, `#conflict`, `#unanswered`), and the unexcluded world state or scope narrowing needed. Return to sender; never pass hedged or unchecked claims upstream.
- **FAIL**: `[Outcome]` does not answer the incoming ask.
- **Harness notices**: Record `PASS` (`"harness notice"`) on automated system notices; proceed normally on scheduled `/loop` wakeups.

```bash
uv run --project <plugin-dir> python3 <plugin-dir>/skills/premise-check/scripts/verdict.py --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason "<why>" [--title "<short_title>"]
```

Use `--reason-file <path>` (or `-` for stdin) for multiline reasons; only `--reason-file <path>` keeps the reason off the command line.
