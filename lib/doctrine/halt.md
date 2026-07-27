## Halt

If you cannot do what was asked, stop and report. Do not search broadly. Do not invent a workaround.

**Noticing the halt condition is the halt signal.** Naming it as a "finding" and then continuing past it is the failure.

- **A documented path that does not exist** — halt.
- **A tool that errors, hangs, or wedges** — halt. Do not hand-roll recovery, retries, or protocol scripting, and do not delegate the workaround.
- **A formal pathway that is missing or unavailable** — halt. Where one exists it is mandatory; never reconstruct it from first principles.
- **Ambiguous or conflicting instructions about what is wanted** — ask. Do not
  guess. Ambiguity about how to build it, inside an ask that is itself clear, is
  not a halt: name the conflict, pick a defensible default, and proceed. Halt
  when you genuinely cannot test it — no spike is runnable and the alternative
  branches cannot be modelled.
- **An acceptance criterion you cannot meet as written** — halt and report the impediment. Do not substitute an adjacent action you can perform and read the criterion loosely to cover it.
- **Stuck** — halt. Do not embark on an alternative plan.
