## Evidence contract and reporting protocol

End any report that makes a load-bearing claim with a claim ledger, so the reader can check every step without your transcript:

```text
STATUS: <outcome> (from C4)
C1. <one atomic claim, scope named>. [observed: <file:line | command → output | URL>]
C2. <one atomic claim>. [exhaustively-searched: <tool, query, scope> → 0 matches]
W1. WARRANT: <the rule that turns C1 and C2 into the conclusion>
D1. UNLESS: <the alternative you checked>. [<basis>: <pointer>]
C4. THEREFORE (C1, C2 via W1 - D1): <conclusion, no broader than its premises>
```

- **The status line names its spine**: the claim it rests on. Only that claim and what it uses go in ledger form; context stays in prose above.
- **One claim per line**, readable on its own, with its scope stated ("in `plugins/ida/`", "at commit `abc123`", "in one run").
- **Every leaf carries a basis tag and a pointer the reader can open**: `observed`, `attempted-and-failed` (verbatim error), `exhaustively-searched` (tool, query, scope), `not-observed`, `inferred`, `assumed`, `reported-by-another` (name the source). Cite the file, command, or record, not your own transcript steps, which the reader cannot open.
- **Derived lines name what they use** and carry no tag of their own, because a conclusion is only as strong as its weakest leaf. Write a warrant when a step needs a rule the premises do not state.
- **Negative and capability claims** ("does not exist", "cannot", "failed") rest on `attempted-and-failed` or `exhaustively-searched`; `not-observed` grounds neither. For a blocked or failed outcome, add an `UNLESS` line for each alternative you ruled out.
- **A one-fact result needs one line**: `STATUS: DONE (from C1)` and C1.
