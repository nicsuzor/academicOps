# Report form

The report argument is one fenced `argdown` block at the end of the report, parser-valid Argdown in standard form. The recorder reads it to cross-check the checker's reason, so the line shapes below are exact. Statement lines carry no `{...}` attributes.

````text
```argdown
===
asks:
  <ask id>: <the asker's own words, one question>
  <ask id>: <next question>
answers:
  <ask id>: <number of the line that answers it>
  <ask id>: none
notes:
  a: <path:line, span id, task id, PR>
  b: ...
===

(1) <premise>. -- <basis phrase> ^a
(2) <premise quoting the deciding value>. -- <basis phrase> ^b
(3) <missing premise, written in>. -- assumed, not checked here
-- <warrant: a rule that could be false on its own>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) So, <qualifier bought by (3)>, <conclusion>.
(5) <premise of the next step>. -- <basis phrase>
-- <warrant using (4) and (5)>. Unless: <defeater>; <status>. --
(6) So <conclusion>.
```
````

## Line shapes

| Part | Shape |
| - | - |
| `asks` | Frontmatter map, ask id to the asker's words. Id: `<channel>-<message id>` (`tg-2008`), or `<task id>/AC<n>`. No spaces. |
| `answers` | Frontmatter map, ask id to the number of the line that answers it, or `none`. |
| `notes` | Frontmatter map, letter to pointer. Pointers live only here. |
| Premise | `(n) <statement>. -- <basis phrase>[ <note>][ ^x...]` |
| Inference | Starts `--`, ends `--`, one line. Warrant, then `Unless:`, the defeater, `;` and its status. No `--` inside the line. |
| Conclusion | The numbered line directly after an inference line. Starts `So`. Carries no basis. |

Basis phrases come from [`vocabulary.toml`](vocabulary.toml). A note may follow the phrase after `;` or `:`, as in `worker reported, verdict verdict-842af6cb` or `I read it: the policy note says so; not attempted here`.

Numbers run on through a chain: a supervisor quoting a worker's lines keeps their numbers and continues from the next one.

Check the block before sending: `npx -y @argdown/cli json --throwExceptions <file>.argdown <outdir>` exits 0 on a valid block.

## Short example

```argdown
===
asks:
  tg-1990: is the hook enforced?
answers:
  tg-1990: 4
notes:
  a: plugins/ida/hooks/handlers.py, the function that emits the block.
===

(1) A hook that only advises cannot block an agent. -- rule
(2) The hook returns "block", not advice. -- I read it ^a
(3) The agent runtime honours a "block" from a hook. -- assumed, not checked here
-- A hook that returns "block" to a runtime that honours it is enforced. Unless: this runtime ignores hook output in the mode it runs in; not ruled out. --
(4) So, most likely, the hook is enforced.
```

## Null form (minimal compliance)

When a message makes no claim (such as automated harness notices, /loop wakeups, or messages making no evidence-backed claims):

```argdown
===
asks: none
===

[no claim]
```

The null form declares minimal compliance and clears the premise-check gate with no agent action.
