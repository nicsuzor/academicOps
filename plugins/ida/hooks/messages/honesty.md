## Evidence contract and reporting protocol

End any report that makes a load-bearing claim with a claim ledger in Argdown, so the reader can check every step without your transcript:

```argdown
[Outcome]: STATUS: DONE

<Basis>: Why the outcome holds.

(1) [C1]: One atomic claim, scope named (basis: observed, pointer: file:line)
(2) [C2]: One atomic claim (basis: exhaustively-searched, pointer: rg -n "x" lib/ -> 0 matches)
(3) [D1]: The alternative you ruled out does not apply (basis: attempted-and-failed, pointer: cmd -> "verbatim error")
(4) [W1]: The rule that turns the premises into the outcome
----
(5) [Outcome]
```

- **The outcome rests on its spine**: the premises above the line. Only the spine goes in the ledger; context stays in prose above it.
- **One claim per statement**, readable on its own, with its scope stated ("in `plugins/ida/`", "at commit `abc123`", "in one run").
- **Every premise carries a basis and a pointer the reader can open**: `observed`, `attempted-and-failed` (verbatim error), `exhaustively-searched` (tool, query, scope), `not-observed`, `inferred`, `assumed`, `reported-by-another` (name the source). Cite the file, command, or record, not your own transcript steps, which the reader cannot open.
- **The conclusion carries no basis of its own**, because it is only as strong as its weakest premise. State it no more broadly than its premises reach. Write a warrant when a step needs a rule the premises do not state.
- **Negative and capability claims** ("does not exist", "cannot", "failed") rest on `attempted-and-failed` or `exhaustively-searched`; `not-observed` grounds neither. For a blocked or failed outcome, add a premise for each alternative you ruled out.
- **A one-fact result needs one statement**: `[C1]: … (basis: observed, pointer: …)` then `+> [Outcome]` on the next line, indented two spaces.
- Separate statements with blank lines outside an argument, and escape underscores in names (`test\_hooks.py`).
