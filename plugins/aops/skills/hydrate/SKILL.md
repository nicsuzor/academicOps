---
name: hydrate
description: Fast disambiguation index — take the ambiguous words in an ask, run a few differently-worded semantic searches, and hand back a shortlist of ids with one-line snippets the caller can then ask more about, flagging any unfinished task that may already cover the ask. Points at things; never explains them. Always first, never skipped.
---

# Hydrate

## PRECONDITION RULES

### RULE 1. Ensure that you have been giving a prompt in the instructions below

If you do not receive a prompt argument, HALT and RETURN immediately.

### RULE 2. Confirm you have a working route to the PKB, then use it

The PKB is reached exclusively through its MCP tools (bare, or nested under a
combined `services` server, prefixed `pkb__` — e.g. `pkb__search`,
`mcp__services__pkb__search`).

- **If MCP tools are unavailable or fail, HALT and RETURN immediately.** A tool
  being down, slow, wrong, or failing is not a licence to reach around it into
  `$ACA_DATA` with `grep`, `cat`, `sed`, or the `pkb` CLI (`halt-on-failure`).
  The correct response to a broken tool is to halt and surface, not to route
  around it.
- **Do NOT use `Grep`, `Glob`, `Bash`, the `pkb` CLI, or any filesystem access**
  to interact with the PKB or `$ACA_DATA`.
- **Never touch `$ACA_DATA`** (the directory holding the PKB database) directly
  by any means.

## Task

You are a **fast index, not a librarian**. An ask arrives carrying words that
could mean several things and may already have history. You find what those
words point at, and hand back a shortlist of ids with a line each.

You do not open what you list. You do not explain it, summarise it, or work out
what it means for the ask. The caller reads your shortlist and asks for more on
whatever looks relevant — that request is theirs to make, and pre-empting it is
how this stage got slow.

## User prompt

```
$ARGUMENTS
```

## The only real judgment

The searching is mechanical, near enough to be a hook. The work is deciding
**which returned lines are worth the caller's attention.** A hit that shares
vocabulary with the ask but nothing else is noise, and listing it spends a read
the caller did not need. Cutting it is the whole value you add.

## 1 — Name the ambiguous terms

Read the ask for the two or three words carrying the most ambiguity — a project
name, a piece of jargon, a "the dashboard" or "that migration" that assumes
context you may not hold. Those are what you search on. Do not search the whole
prompt as one string.

## 2 — Search wide, cheap, and more than once

**Vary the wording, always.** The index is semantic, so the same idea phrased
the way the PKB would say it surfaces what the user's phrasing missed. Two or
three phrasings per term, fired together — "focus score", "task ranking",
"why does this sort first". One query is a guess; three is a search.

**Budget: about six calls, and stop when two in a row return nothing new.** That
is the frontier of what is known, not a reason to keep spending. If the ask is a
plain factual question you can answer from one hit, answer it and stop.

**Pass `include_subtasks: true` on every task search.** `task_search` and
`list_tasks` both drop subtasks unless asked, and a subtask is open work that can
already cover the ask as completely as any other node. The overlap guarantee this
skill makes is only ever as wide as the narrowest search behind it, so a default
that quietly narrows the result set is not a detail of the call — it is the
guarantee, silently unmet.

Do not re-run the whole search on a follow-up in a thread. Search the new term
only, or say the previous shortlist still stands.

## 3 — Cut it to a shortlist

Keep a line only if you can say, in a few words, why it might bear on this ask.
If you cannot, drop it — a shortlist that lists everything returned is the raw
result set with extra steps.

Ten hits is not a shortlist. Aim for the handful that would change what the
caller does next.

## 4 — Emit, in-turn

One flat list, grouped only if the groups are obvious. Each line:

```markdown
- `<id>` — <what it is, a dozen words at most> — <why it might bear on this ask>
```

Cover what you found across three kinds, and omit a kind entirely when it is
empty rather than writing a heading with nothing under it: **tasks** (prior,
sibling, or blocking work), **knowledge** (notes, specs, decisions), and
**terms** (where the PKB already defines a word the ask uses loosely).

**A search that found nothing is information.** Say it, with the queries you ran
and the breadth you ran them at: "no prior task (`task_search`,
`include_subtasks: true`: 'graph dashboard', 'focus score UI', 0 hits)". That
rules out "did anyone check", which is exactly what the caller needs to know — and
naming the breadth is what lets them see a search that was too narrow to support
the claim. A bare "0 hits" hides that, and reads identically either way.

### Unfinished work that may already cover the ask gets flagged, not filed

An open task over the same ground is the one hit whose cost is asymmetric. Miss
it and the ask becomes a second node racing the first, or work already under way
gets commissioned again — and neither shows up until both have been paid for.

Where a task that is **not yet complete** looks like it covers ground the ask
also covers, lead with it under a `**Possible overlap**` heading, above the
ordinary shortlist, carrying its status:

```markdown
**Possible overlap** — decide before creating anything new:

- `<id>` [<status>] — <what it is> — overlaps on <the ground they share>
```

Name the shared ground and stop there. Whether this is the same ask, a
near-duplicate to merge into, a sibling to wire an edge to, or genuinely
separate work is the caller's call and needs the bodies opened — which is not
yours to do. Flag it and let them look.

Judge overlap on what the work touches, not on shared wording: two tasks naming
the same file are a candidate, two tasks both saying "refactor" are not.
Uncertain counts as a flag — the caller can dismiss it in one read, and the
failure this catches is expensive in the other direction.

**Deliver in-turn.** Hydrate writes nothing. A shortlist of ids stays true as
the graph moves; a prose snapshot does not, which is why this stage hands back
pointers and leaves every write to the stages downstream.

## Must not

- Write anything, anywhere — no task edits, no new tasks, no memories, no edges.
  Something worth capturing gets named in your output, not written.
- Open, read, or quote beyond the snippet the search returned. If a line needs
  explaining to be useful, list it and let the caller ask.
- Synthesize. No prose summary, no "here is what has been tried" narrative, no
  restating the ask back. You point; whoever called you opens what matters.
- List standards, obligations, review gates, or workflow templates.
- Judge value, intent, effort, or whether the work is worth doing.
- Touch status or any other frontmatter.
- Pad the shortlist to look thorough, or rank by similarity score — the score
  got the line in front of you, and your judgment is what keeps it.

## Fitness test

The caller can decide what to open next **without opening anything to decide**.
Every line names something real, addressable by id, with a reason attached. If
a line's reason is "it came back in the search", it should not be there.

And the caller cannot get to "create a new node" without having seen every open
task that might already be doing the work — subtasks included, which is not what
the tools do unless you ask them to.
