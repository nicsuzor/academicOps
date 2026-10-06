---
name: claim-ledger
description: Write the claim ledger that ends any report, handback, or verdict resting on evidence -- Argdown layout, basis tags, and what counts as a pointer. Use before writing receipts, a handover, or a final report whose conclusion depends on observed facts. Not for checking someone else's report (use premise-check).
---

# Claim Ledger

Lead the report with the answer in plain prose. Then end it with a ledger, so the reader can follow the logic at a glance and check every premise without your transcript.

## Shape

```argdown
[Outcome]: The result in one plain sentence, with its scope.

<Why>: What this argument establishes.

(1) [Short title]: One atomic claim, scope named. #observed `owner/repo@abc1234:path/file.py:42`
(2) [Short title]: One atomic claim. #exhaustively-searched `rg -n "pattern" lib/` → 0 matches
(3) [Rule]: The rule that turns (1) and (2) into the outcome. #warrant
-- from (1) and (2) by (3) --
(4) [Outcome]

[Open limit]: Something that still weakens the outcome. #observed `Phoenix span 04c6cb12533977a5`
  -> [Outcome]
```

A result resting on one fact needs no argument: the outcome, then one tagged statement with `+> [Outcome]` indented two spaces beneath it.

## Rules

- **Readable at a glance.** Give each statement a short title. The derivation line names the premises and the rule it uses. Only the claims the outcome rests on go in the ledger; context stays in the prose above.
- **One claim per statement**, true on its own, with its scope stated ("in `plugins/ida/`", "at commit `abc1234`", "in one run").
- **Pointers.** A pointer is the identifier of the evidence, as specific as you can make it:
  1. A pinpoint is best: `owner/repo@sha:path:line`, a Phoenix span id, a PR comment URL, a PKB node id and section.
  2. Next best is the bare identifier: commit `owner/repo@sha`, a PR URL, a task id.
  3. Give a command only when its output is the evidence, and quote the output: `cmd` → "verbatim result". A command that fetches something with an identifier (`git show …`) is not a pointer, so give the identifier instead.
  4. Never cite your own transcript steps, "tree inspection", or "test output" without the output, because the reader cannot open them.

  Write pointers verbatim in backticks, unescaped, even though the Argdown parser rejects underscores in them.
- **Basis tags.** Tag every premise: #observed, #attempted-and-failed (quote the error), #exhaustively-searched (tool, query, scope, count), #not-observed, #inferred, #assumed, #reported-by-another (name the source). Tag a rule #warrant.
- **The conclusion carries no tag**, because it is only as strong as its weakest premise. Word it no wider than its premises reach. Add a warrant whenever a step needs a rule the premises do not state.
- **Negative and capability claims** ("does not exist", "cannot", "failed") rest on #attempted-and-failed or #exhaustively-searched; #not-observed grounds neither.
- **Alternatives and caveats.** Write each alternative you ruled out as a premise. Write each caveat still open as an attack (`->`).
- **No horizontal rules.** Use the named derivation line (`-- from … --`), never a bare `----`. Use no `---` separators anywhere in the report: headings and blank lines carry the structure.
- **Fences.** Put a ledger in an `argdown` fenced block, never in inline code. To nest one inside another fenced block, make the outer fence longer (`` ````markdown ``).
