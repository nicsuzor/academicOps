## Evidence contract and reporting protocol

Lead with the answer in plain prose. Then end any report that makes a load-bearing claim with a claim ledger in Argdown, so the reader can follow the logic at a glance and check every premise without your transcript:

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

- **Readable at a glance.** Give each statement a short title. The derivation line names the premises and the rule it uses.
- **One claim per statement**, true on its own, with its scope stated ("in `plugins/ida/`", "at commit `abc1234`", "in one run").
- **A pointer is the identifier of the evidence, as specific as you can make it.** A pinpoint is best: `owner/repo@sha:path:line`, a Phoenix span id, a PR comment URL. Next best is the bare identifier: commit `owner/repo@sha`, a PR URL, a task id. Give a command only when its output is the evidence, and quote that output: `cmd` → "verbatim result". Never give a command that merely fetches something that has an identifier (`git show …`). Never cite your own transcript steps, which the reader cannot open. Write pointers verbatim in backticks, unescaped.
- **Tag every premise with its basis**: #observed, #attempted-and-failed (quote the error), #exhaustively-searched (tool, query, scope, count), #not-observed, #inferred, #assumed, #reported-by-another (name the source). Tag a rule #warrant.
- **The conclusion carries no tag**, because it is only as strong as its weakest premise. Word it no wider than its premises reach. Add a warrant whenever a step needs a rule the premises do not state.
- **Negative and capability claims** ("does not exist", "cannot", "failed") rest on #attempted-and-failed or #exhaustively-searched; #not-observed grounds neither. Write each alternative you ruled out as a premise, and each caveat still open as an attack (`->`).
- **A one-fact result** is the outcome plus one tagged statement, with `+> [Outcome]` indented two spaces on the line beneath it.
