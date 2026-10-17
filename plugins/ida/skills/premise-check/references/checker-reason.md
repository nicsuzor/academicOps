# Checker's reason

The reason is seven keyed lines. A key may repeat: one line per entry. Write it to a file and pass `--reason-file`.

```text
Judged: <claim id>; asks <ask id>, <ask id>
Valid: (n) holds -- <the rule, and why it yields (n) here>
Valid: (m) fails #missing -- <the condition no premise supplies>
Supported: weakest <basis phrase> -- <which premise, and whether stakes need it supported>
Answered: <ask id> ← (n)
Answered: <ask id> unanswered
Sufficient: (n) <materiality; sufficiency (obvious | authority-backed | low-stakes | sent back); necessity of any objection>
Waived: none
Waived: <format item> -- <what was off, and why the step could still be judged>
Relay: "<sentence you will send up>" ← (n), (m)
Relay: none
```

| Key | Entries |
| - | - |
| `Judged` | Exactly one. The claim id the gate named, then every ask id in the block. |
| `Valid` | One per inference line, keyed by the conclusion it yields. `holds`, or `fails` and a defect tag. |
| `Supported` | One. The weakest basis phrase among all premises. |
| `Answered` | One per ask id: the line that answers it, or `unanswered`. |
| `Sufficient` | One or more, keyed by conclusion: which proportionality test settled each material step. |
| `Waived` | `none`, or one per waived breach, starting with a format item from [`vocabulary.toml`](vocabulary.toml). |
| `Relay` | `none`, or one per sentence you will send up, naming the lines it restates. |

## What the recorder refuses

For PASS the recorder checks, and refuses on any miss:

- all seven keys are present, with exactly one `Judged` and one `Supported`;
- `Judged` names at least one ask id, and its ask ids equal the `Asked` ids in the block;
- every ask id has an `Answered` line that names a line of the block (`← (n)`) or says `unanswered`;
- `Valid` has one entry per inference line, every inference line is followed by its conclusion, and no entry says `fails`;
- the `Supported` phrase has the lowest rank among the block's premises;
- every `Waived` entry starts with a format item;
- every `Relay` line names lines that exist in the block.

With no `argument` block in the judged text, the block cross-checks cannot run: PASS then needs `Waived: block -- ...` and the remaining checks run against the reason alone.

REVISE and FAIL are recorded with any reason; write the keyed lines you have, because they are what the sender fixes against.

## A message that makes no claim

A harness notice or a status ping carries no argument. Record PASS with one line, `Judged: <claim id>; no claim -- <what the message is>`. The recorder accepts it only when the judged text has no `argument` block, and marks the verdict as no-claim in telemetry.
