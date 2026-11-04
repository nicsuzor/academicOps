# Report form

The report argument is one fenced `argdown` block at the end of the report, parser-valid Argdown in standard form. Frontmatter between `===` lines carries document metadata (`title`, `granularity`, `model: mode: strict` per `argdown-toulmin`), `asks`, and `answers`. Statement lines carry inline citations or `{...}` attributes per `argdown-toulmin`. Readers ignore meaning-free whitespace across the block (common leading indents across frontmatter or body, trailing whitespace on lines, CRLF endings, and added or removed blank lines); whitespace carrying syntactic meaning (relative nesting within frontmatter, and single-line inference bars) remains significant. Transport envelopes (such as XML `<task-notification><result>...</result>`) entity-escape `<`, `>`, and `&`; recorders and readers decode HTML entities (`&lt;`, `&gt;`, `&amp;`) before parsing, so blocks parse identically whether received raw or entity-escaped.

````text
```argdown
===
title: <title>
granularity:
  level: <micro | meso | macro>
  floor: "<floor description>"
model:
  mode: strict
asks:
  <ask id>: <the asker's own words, one question>
  <ask id>: <next question>
answers:
  <ask id>: <number of the line that answers it, or statement title>
  <ask id>: none
===

(1) [Label]: <premise with inline citation or attributes>. {basis: "observed", pointer: "...", source: "..."}
(2) <premise quoting the deciding value inline>.
(3) <missing premise, written in>.
-- <warrant: a rule that could be false on its own>. Unless: <defeater>; <ruled out by (n) | not ruled out | not tried>. --
(4) [Conclusion]: So, <qualifier bought by (3)>, <conclusion>.
(5) <premise of the next step with inline citation>.
-- <warrant using (4) and (5)>. Unless: <defeater>; <status>. --
(6) So <conclusion>.
```
````

## Line shapes

| Part | Shape |
| - | - |
| `asks` | Frontmatter map (ask ID to asker's words) or list of records (`- id: <ask id>`, `text: <words>`). Id: `<channel>-<message id>` (`tg-2008`), or `<task id>/AC<n>`. No spaces. |
| `answers` | Frontmatter map, ask id to the number of the line that answers it, statement label/title (e.g. `Next` or `[Next]`), or `none`. |
| Premise | `(n) <statement with inline citations and quoted values>` |
| Inference | Starts `--`, ends `--`, one line. Warrant, then `Unless:`, the defeater, `;` and its status. No `--` inside the line. |
| Conclusion | The numbered line directly after an inference line. Starts `So`. Carries no basis. |

Pointers and citations live directly inline in natural prose:

- File locations: `(plugins/ida/hooks/handlers.py:42)`
- Task or note links: `[[task-id]]` or `task-id`
- Runtime executions: `(run: exit_code = 0)`

Numbers run on through a chain: a supervisor quoting a worker's lines keeps their numbers and continues from the next one.

Optional local syntax check before sending: `npx -y @argdown/cli json --throwExceptions <file>.argdown <outdir>` exits 0 on a valid block (authoring agents follow syntax rules directly without invoking an external CLI per `argdown-toulmin`).

## Method fidelity and departures

When an ask specifies a method, form, design, or value, the report carries a pairing line before the argument block setting each specified feature beside what was done, naming each departure with its reason, else `departures: none`.

- **Shape**: `Departures: none` or `Departures: <specified feature> -> <what was done> (<reason>); ...`
- **Default rule**: A detail in a method specification is load-bearing regardless of typography (quoted, backticked, or plain) unless the ask's purpose shows it free.
- **Rewording**: Rewording that preserves the construct is not a departure; no verbatim requirement is added outside specified methods, forms, designs, or values.

## Short example

Departures: none

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
