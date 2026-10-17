# Report form

The report argument is one fenced block with the info string `argument`, at the end of the report. One statement per line. The recorder reads this block to cross-check the checker's reason, so the line shapes below are exact.

````text
```argument
Asked (<ask id>): <the asker's own words, one question>
Asked (<ask id>): <next question>

(1) <premise>. -- <basis phrase> [a]
(2) <premise quoting the deciding value>. -- <basis phrase> [b]
(3) <missing premise, written in>. -- assumed, not checked here
-- <warrant: a rule that could be false on its own>. Unless: <defeater> -- <ruled out by (n) | not ruled out | not tried>. --
(4) So, <qualifier bought by (3)>, <conclusion>.
(5) <premise of the next step>. -- <basis phrase> [c]
-- <warrant using (4) and (5)>. Unless: <defeater> -- <status>. --
(6) So <conclusion>.

Answers: <ask id> ← (6); <ask id>: none

[a] <path:line, span id, task id, PR>
[b] ...
```
````

## Line shapes

| Line | Shape |
| - | - |
| Ask | `Asked (<id>): <words>`. Id: `tg-<message id>`, or `<task id>/AC<n>`. No spaces in an id. |
| Premise | `(n) <statement>. -- <basis phrase>[ <note>][ [x]...]` |
| Inference | Starts `--`, ends `--`. Warrant first, then `Unless:` and its status. |
| Conclusion | The numbered line directly after an inference line. Starts `So`. Carries no basis. |
| Answers | `Answers:` then `<id> ← (n)` or `<id>: none`, separated by `;`. |
| Endnote | `[x] <pointer>`. Pointers live only here. |

Basis phrases come from [`vocabulary.toml`](vocabulary.toml). A note may follow the phrase after `;` or `:` -- `worker reported, verdict verdict-842af6cb`, `I read it: the policy note says so; not attempted here`.

Numbers run on through a chain: a supervisor quoting a worker's lines keeps their numbers and continues from the next one.

## Short example

```argument
Asked (tg-1990): is the hook enforced?

(1) A hook that only advises cannot block an agent. -- rule
(2) The hook returns "block", not advice. -- I read it [a]
(3) The agent runtime honours a "block" from a hook. -- assumed, not checked here
-- A hook that returns "block" to a runtime that honours it is enforced. Unless: this runtime ignores hook output in the mode it runs in -- not ruled out. --
(4) So, most likely, the hook is enforced.

Answers: tg-1990 ← (4)

[a] plugins/ida/hooks/handlers.py, the function that emits the block.
```
