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
===

(1) <premise with inline citation>.
(2) <premise quoting the deciding value inline>.
(3) <missing premise, written in>.
-- <warrant: a rule that could be false on its own>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) So, <qualifier bought by (3)>, <conclusion>.
(5) <premise of the next step with inline citation>.
-- <warrant using (4) and (5)>. Unless: <defeater>; <status>. --
(6) So <conclusion>.
```
````

## Line shapes

| Part | Shape |
| - | - |
| `asks` | Frontmatter map, ask id to the asker's words. Id: `<channel>-<message id>` (`tg-2008`), or `<task id>/AC<n>`. No spaces. |
| `answers` | Frontmatter map, ask id to the number of the line that answers it, or `none`. |
| Premise | `(n) <statement with inline citations and quoted values>` |
| Inference | Starts `--`, ends `--`, one line. Warrant, then `Unless:`, the defeater, `;` and its status. No `--` inside the line. |
| Conclusion | The numbered line directly after an inference line. Starts `So`. Carries no basis. |

Pointers and citations live directly inline in natural prose:

- File locations: `(plugins/ida/hooks/handlers.py:42)`
- Task or note links: `[[task-id]]` or `task-id`
- Runtime executions: `(run: exit_code = 0)`

Numbers run on through a chain: a supervisor quoting a worker's lines keeps their numbers and continues from the next one.

Optional local syntax check before sending: `npx -y @argdown/cli json --throwExceptions <file>.argdown <outdir>` exits 0 on a valid block (authoring agents follow syntax rules directly without invoking an external CLI per `argdown-toulmin`).

## Short example

```argdown
===
asks:
  tg-1990: is the hook enforced?
answers:
  tg-1990: 4
===

(1) A hook that only advises cannot block an agent (governing rule).
(2) The hook returns "block", not advice (read from plugins/ida/hooks/handlers.py).
(3) The agent runtime honours a "block" from a hook (assumed, not checked here).
-- A hook that returns "block" to a runtime that honours it is enforced. Unless: this runtime ignores hook output in the mode it runs in; not ruled out. --
(4) So, most likely, the hook is enforced.
```

## Null form (minimal compliance)

When a message makes no claim (such as automated harness notices, /loop wakeups, or messages making no evidence-backed claims), see the null form defined in [`SKILL.md`](../SKILL.md#writing-the-argument).
