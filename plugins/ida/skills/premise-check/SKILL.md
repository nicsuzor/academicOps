---
name: premise-check
description: Author or verify an agent handback report argument in standardised Chained Toulmin Argdown -- enforcing basis vocabulary, the ask as main conclusion, non-flat inference chains, contrast testing, granularity stopping rules, and verdict recording. Use when receiving a subagent report, passing verified claims up the chain, or authoring handback receipts.
---

# Premise Check

Author or verify report arguments using the standardised **Chained Toulmin Argdown** contract so every handback receipt links observed facts to `[Outcome]` through explicit warrants, bounded scopes, and dynamic stopping rules.

## When to Use

- Ending an evidence-backed subagent or task report with a verifiable handback argument concluding `[Outcome]`
- Auditing an incoming report from a subagent or workflow step before accepting its claim or passing it upstream
- Recording a formal `PASS`, `REVISE`, or `FAIL` verdict on a report claim

## Standardised Chained Toulmin Shape

End every evidence-backed report with a parser-valid Argdown block concluding `[Outcome]` (the direct answer to the incoming ask):

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

## Authoring Rules

- **No flat premise lists (2-to-3 Premise Cap)**: Never dump 4 or more premises above a single `-- Warrant --` line. Group co-dependent facts (at most 2 to 3 premises) above the specific `-- Warrant --` that licenses their intermediate conclusion, then chain `(3) [Intermediate State]` into the next `-- Warrant --` bar to reach `[Outcome]`.
- **Metadata schema (`{basis, pointer, source?}`)**:
  - `basis`: `"observed"`, `"exhaustively-searched"`, `"attempted-and-failed"`, `"method-bounded"`, `"reported-by"`, `"theory"`, `"stated"`, or `"assumed"`.
  - `pointer`: Verbatim locator (`owner/repo@sha:path:line`, span/node ID, URL, citation, or exact shell query).
  - Diagnostic tags when flagging issues: `#format`, `#missing`, `#scope-drift`, `#conflict`, `#unanswered`.
- **Observed-value rule**: Premises with `basis: "observed"` or `"reported-by"` must quote the deciding field's observed value or verbatim text (`status: MERGED`, `p = 0.004`, `66% unavailable`) inline or in `source` alongside the `pointer`. A bare pointer proves existence only, not content.
- **Warrants live in the `--` inference bar**: Always write the licensing rule, mechanism, or policy inside `-- Warrant name {uses: [1, 2], basis: "...", pointer: "..."} --`, never as a numbered `#warrant` premise.
- **Match basis to claim type**:
  - _Rankings / comparisons_ require explicit comparison premises covering the alternatives.
  - _Negatives / absences / capabilities_ require `basis: "exhaustively-searched"`, `"attempted-and-failed"`, or `"method-bounded"` stating the exact search boundary or instrument limit.
  - _Causal / universal claims_ require an explicit mechanism in the `-- Warrant --` bar and a conclusion scope no wider than the premises' scope.

## Formal Check and Granularity Stopping Rules

When verifying an incoming report, accept `observed` and `exhaustively-searched` leaf premises with valid pointers and observed values as given (do not re-open files or re-run searches):

1. **Format Kickback (`REVISE` `#format`)**: If a report lacks a parser-valid Chained Toulmin block concluding `[Outcome]`, or dumps 4+ unchained premises into a flat list without connecting warrants, return `REVISE` (`#format`) immediately before checking substance.
2. **Scope and Middle-Term Check (`REVISE` `#scope-drift`)**: Check that every noun, population, and quantifier in `(3) [Outcome]` is licensed by `(1)-(2)` and the `-- Warrant --`. If the premises prove a local or sample fact (`"in module A"`) but the conclusion states a global claim (`"across the repo"`), return `REVISE` (`#scope-drift`).
3. **The Contrast Test (`REVISE` `#missing` or `#unanswered`)**: For each load-bearing inference bar, name the nearest plausible world state or rival explanation that would change the conclusion or next action. If the cited evidence in `(1)-(2)` would look identical in that rival state, return `REVISE` (`#missing`), naming the exact step and the unexcluded rival state.
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

Use `--reason-file <path>` (or `-`) for multiline reasons.
