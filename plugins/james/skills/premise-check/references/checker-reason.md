# Checker's reason

The reason is seven keyed lines. A key may repeat: one line per entry. Write it to a file and pass `--reason-file` along with `--judged-file <path>` when recording a verdict via `verdict.py`.

```text
Judged: <claim id>; asks <ask id>, <ask id>
Valid: (n) holds -- <the rule, and why it yields (n) here>
Valid: (m) fails #missing -- <the condition no premise supplies>
Valid: (k) fails #insufficient-for-stakes -- <the stakes, and why the premises cannot bear them>
Valid: (j) fails #conflict -- <the rule the step breaches>
Supported: (<premise n>) <qualitative evaluation of whether evidence sufficiency bears stakes>
Answered: <ask id> ← (n)
Answered: <ask id> unanswered
Sufficient: (n) <materiality; the stakes in words; sufficiency (obvious | authority-backed | cited verdict | low-stakes (only a conclusion bearing no stakes) | sent back); necessity of any objection>
Waived: none
Waived: <format item> -- <what was off, and why the step could still be judged>
Relay: "<sentence you will send up>" ← (n), (m)
Relay: none
```

| Key | Entries |
| - | - |
| `Judged` | Exactly one. The claim id being judged, then every ask id in the block. |
| `Valid` | One per inference line, keyed by the conclusion it yields (or grouped/semicolon clauses accounting for all conclusions, e.g. `(n), (m) holds`). `holds`, or `fails` and a defect tag from [`vocabulary.toml`](vocabulary.toml) (e.g. `#insufficient-for-stakes`, `#method-gap`, `#scope-drift`, `#conflict`). Rejects circular warrants and conclusions wider than observation surface. |
| `Supported` | Exactly one. Qualitative evaluation of evidence sufficiency against the stakes of the step. On live state, names the source category of load-bearing premises (primary observation with deciding value inline vs. verified child verdict relay). Originating agents citing secondary summaries instead of primary materials fail (`Valid: (n) fails #insufficient-for-stakes`); intermediate agents accepting and re-expressing a verified judgment from below (`verdict-...`) are valid. A conclusion wider than the observation surface fails `Valid` (`#method-gap` or `#scope-drift`). |
| `Answered` | One per ask id: the line that answers it, or `unanswered`. A conclusion line `(n)` demonstrating why an unfulfillable brief demand is unreachable by construction satisfies the ask and links under `Answered: <ask_id> ← (n)`. |
| `Sufficient` | One or more, keyed by conclusion: the step's stakes in words, and which proportionality test settled it. `authority-backed` is limited strictly to the user's own words or a governing spec. `low-stakes` never settles a conclusion that answers an ask, is relayed to the user, or authorises a merge, send or approval. |
| `Waived` | `none`, or one per waived breach, starting with a format item from [`vocabulary.toml`](vocabulary.toml) (`block`, `numbering`, `endnotes`, `basis wording`, `ask wording`, `layout`). Rule violations in deliverables are never waivable and can never be recorded under `Waived:`; any report admitting or exhibiting a rule violation in its deliverable must receive `REVISE` with `#conflict` or `FAIL`. |
| `Relay` | `none`, or one per sentence you will send up, naming the lines it restates. |

## What the recorder refuses

For `PASS`, `--judged-file <path>` is required so `verdict.py` validates the report's fenced `argdown` block against `report_argument.py`. The recorder refuses `PASS` on any miss:

- `--judged-file` is missing, or the judged text contains no fenced ` ```argdown ` block at all (an absent block cannot pass);
- all seven keys are present, with exactly one `Judged` and one `Supported`;
- `Judged` names at least one ask id, and its ask ids equal the `asks` ids in the block, and every line the block's `answers` names exists;
- every ask id has an `Answered` line that names a line of the block (`← (n)`) or says `unanswered` (an ask whose demand was unfulfillable by construction is answered by the conclusion establishing its unreachability);
- `Valid` accounts for every inference line by conclusion (individual lines, indented lines, semicolon clauses, or grouped references such as `(n), (m) holds`), every inference line is followed by its conclusion, and no entry says `fails`;
- the `Supported` line is present and non-empty;
- every `Waived` entry starts with a format item (`block`, `numbering`, `endnotes`, `basis wording`, `ask wording`, `layout`); rule violations are strictly non-waivable;
- every `Relay` line names lines that exist in the block;
- no line that the block's `answers`, an `Answered` line or a `Relay` line names is written as a conclusion (opening with the connective `So`, not `So far` or the like) with no inference bar yielding it, whether or not the block is waived. That orphan conclusion has no `Valid` line to judge it; the missing bar is the report writer's `#missing`, sent back with `REVISE` (`Valid: (n) fails #missing -- ...`).

When a fenced `argdown` block is present in the judged file but its frontmatter or syntax fails to parse, the block cross-checks cannot run: `PASS` then needs `Waived: block -- ...` and the remaining checks run against the reason alone (orphan conclusions remain unwaivable).

A parenthesised answering line (`answers: <ask>: (6)`) is a `numbering` slip: `Waived: numbering -- ...` lets `PASS` judge it as the line it names.

## REVISE and FAIL

Write the keyed lines you have, because they are what the sender fixes against. Every reasoning failure goes on a `Valid` line, whichever test found it: premises too weak for the stakes are `Valid: (n) fails #insufficient-for-stakes`, a rule breach is `Valid: (n) fails #conflict`. When `Valid:` lines are present and all say `holds`, the recorder refuses `REVISE` and `FAIL` unless an ask is `unanswered`, or, for `REVISE` only, the reason carries a format slip to fix:

```text
Format: <format item> -- <what is off, and the fix>
```

`Format:` names a format item from [`vocabulary.toml`](vocabulary.toml), one line per slip. It is the send-back for a sound argument; a format slip is never written as `Valid: (n) fails`.

## A message that makes no claim

A harness notice or claim-free message carries the null-form fenced `argdown` block (`asks: none` / `[no claim]`). Record `PASS` with one line, `Judged: <claim id>; no claim -- <what the message is>`, passing `--judged-file <path>`. The recorder accepts it when the judged text carries no substantive `argdown` block (null form only) and marks the verdict as `no_claim` in telemetry.
