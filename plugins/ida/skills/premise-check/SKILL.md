---
name: premise-check
description: Judge a report's logic or author a report argument -- parser-valid Argdown with basis vocabulary, the ask as main conclusion, stopping rules, and verdict recording. Use when receiving a report, passing claims up the chain, or authoring handback receipts. Not a fact check or requirement review.
allowed-tools: Read, Write, Edit
---

# Premise Check

Author or check report arguments (syntax and validation: `ida:argument-extraction`; reconstruction: `ida:argument-map`).

## Authoring and Shape

End every evidence-backed report with a parser-valid Argdown argument concluding `[Ask]` / `[Outcome]`:

```argdown
===
title: Incoming ask
author: agent-name
date: 2026-10-12
abstract: Outcome in plain prose.
model:
  mode: strict
===

[Outcome]: The answer to the ask.

<Check>: Verification

(1) [Pinpoint fact]: Stated finding (`status: MERGED`). {basis: "observed", pointer: "owner/repo@sha:path:line"}
(2) [Exhaustive search]: Bounded search finding. {basis: "exhaustively-searched", pointer: "query in path -> 0 hits"}
-- Rule name {uses: [1, 2], basis: "reported-by", pointer: "node-id"} --
(3) [Outcome]
```

- **Metadata**: `{basis, pointer, source?}` with verbatim locators (`owner/repo@sha:path:line`, span IDs, URLs, node IDs).
- **Basis vocabulary**: `observed`, `exhaustively-searched` / `attempted-and-failed` (search boundary or failed command), `reported-by`, `assumed`, `stated`; tags `#format`, `#missing`, `#conflict`, `#unanswered`.
- **Observed-value rule**: State premises (`observed` or `reported-by`) quote the deciding field's observed value (`status: MERGED`, `conclusion: FAILURE`) beside the pointer; a bare pointer proves existence only.
- **Warrants & conclusions**: Put warrants in the `--` line (`uses: [n, ...]`, `basis: "reported-by"` or `"assumed"`), never as `#warrant`. Rankings need comparison premises; negatives/capabilities need `exhaustively-searched` or `attempted-and-failed`; causal/universals need a mechanism; scope stays within premise scopes.

## Formal Check and Stopping Rules

Accept observed premises with pointers as given; never open pointers or re-determine facts:

- **Kickback (`REVISE` `#format`)**: A report without an argument in this shape gets `REVISE` (`#format`); the sender rewrites it before substance is checked.
- **Contrast test**: For each load-bearing premise, name the nearest world state that changes the next action. If the cited evidence looks the same in that state, record `REVISE` (`#missing`).
- **Truth boundary**: A `REVISE` (`#missing`) names the step and the unexcluded state or missing premise for the author to supply with a pointer.
- **Relayed directions**: For `'direction...' (derived from: ask summary [source:id])`, verify derivation from the cited ask and flag unsupported detail.
- **Proportionality & stopping**: Check only material steps; accept obvious, authority-backed, or low-stakes warrants whole; reject only when an objection changes the conclusion. No criterion addresses style, granularity, or splitting. Dispatch/return until `[Ask]` / `[Outcome]` has no material `#missing`. Synthesise accepted Outcomes upward as `{basis: "reported-by", pointer: "<verdict id>"}`, keeping material fact pointers.

## Recording the Verdict

- **PASS**: No material `#missing`, undercut (`_>`), `#conflict` (`><`), or `#unanswered`.
- **REVISE**: Step + `#format`, `#missing`, `#conflict`, `#unanswered`, `_>`, or narrowing; return to sender (never pass unchecked/hedged claims to the user).
- **FAIL**: Conclusion does not answer the ask.
- **Harness notices**: Record `PASS` (`"harness notice"`) on automated notices; proceed on `/loop` wakeups.

```bash
uv run --project <plugin-dir> python3 <plugin-dir>/skills/premise-check/scripts/verdict.py --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason "<why>" [--title "<short_title>"]
```

Use `--reason-file <path>` (or `-`) for multiline text.
