# Right-Sizing — Decision Tree & Worked Examples

Hydration is never skipped, only right-sized. The question isn't "do I hydrate?" — it's "how much
bundle does this input earn?"

## Decision tree

```
Inbound ask
    |
    +-- Pure information request, answerable from search alone?
    |       ("what is X", "where do we stand on Y", "how does Z work")
    |       -> MICRO-BUNDLE: ## Intent + a direct answer. Stop. No task touched.
    |
    +-- Continuation of an already-active task in this session/thread?
    |       ("also do this", "actually make it X instead", replying to your own question)
    |       -> BIND: append only the new delta to the existing task's Context. Don't
    |          re-run the full search or re-emit Standards/Dependencies (they haven't
    |          changed) unless the follow-up plausibly shifts them.
    |
    +-- New substantial ask, no existing task, would justify its own line on the graph?
            -> FULL BUNDLE: all four sections, handed to situate.
```

## Worked examples

**Micro-bundle.** Ask: "What's the retry bound for re-dispatch in the two-layer doctrine?"
→ One `search` call finds `two-layer-decomposition.md`. Output:

```markdown
## Intent

User wants the retry-before-escalation bound for re-dispatch.

Per [[two-layer-decomposition]] ("Known-thin"): bounded retries, starting ~3, before escalation —
explicitly tunable, not a fixed constant.
```

No Context/Standards/Dependencies headings — the answer _is_ the context, inline.

**Bind (follow-up).** Active task `aops_1234` already carries a bundle from ten minutes ago; user
says "also check whether this affects the mobile client." → `get_task` confirms it's the same
thread. Append only:

```markdown
## Context (update)

- User has also asked whether this affects the mobile client — no prior investigation found
  (searched `task_search("mobile client")`, no hits).
```

Do not regenerate Intent/Standards/Dependencies — cite that they're unchanged if a downstream
reader might otherwise assume they were skipped.

**Full bundle.** Ask: "We should build a dashboard for the task graph." No existing task, clearly
multi-step, graph-worthy. Run the full Step 2 gather, emit all four sections, hand forward to
`situate` (see `SKILL.md` Step 3 for the exact format).

## Anti-patterns to avoid

- Writing a full four-section bundle for a one-line factual question — it buries the answer and
  burns budget the fitness test doesn't need.
- Treating "simple question" as license to skip the search entirely — you must still check; you're
  just not obligated to write up an empty Context/Standards/Dependencies scaffold afterward.
- Re-running the full gather on every follow-up in a thread — bind and delta instead.
