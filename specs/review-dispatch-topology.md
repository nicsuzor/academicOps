---
title: Review dispatch topology — how a James panel is launched
status: ready
---

# Review dispatch topology — how a James panel is launched

> Canonical reference for **where** a multi-perspective review (James + rbg + pauli + marsha)
> is dispatched from, and **why** dispatching James as a leaf subagent silently collapses a
> four-perspective review into a one-agent one. Consumed by `aops-core:review-pr` and the
> `james` persona; the orchestrator (`junior`/`james`) reads this before commissioning a panel.

## TL;DR

- A James panel review wants **four independent perspectives** — James synthesis, rbg compliance,
  pauli strategy, marsha QA — each in its own context window.
- **Never dispatch James as a leaf subagent for a panel review.** A subagent generally cannot
  spawn further subagents, so a James-as-subagent does all four roles himself and the degradation
  is silent — the output still reads like a review.
- The fix is a **capability ladder** (Tier A → B → C) the dispatching agent walks down to the
  highest tier its harness supports. The portable default (Tier B) works on any harness that can
  spawn one level of sub-agents; the floor (Tier C) works everywhere, including Gemini CLI and GHA.
- The instructions describe the **shape** (four perspectives) and the ladder — not a Claude-only
  primitive. Agent teams are the top rung, never a hard dependency.

## The agent-teams mechanism (what it is)

"Agent teams" is a Claude Code capability (experimental, **disabled by default**, requires
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and Claude Code ≥ v2.1.32). It lets one session — the
**team lead** — spawn **teammates** that are each a _full, independent Claude Code session_ with
its own context window. Unlike subagents, teammates:

- **message each other directly** through a shared **Mailbox** (`SendMessage` tool), not only the lead;
- **share a task list** they self-claim work from (file-locked to avoid races);
- can be defined from an existing **subagent definition** — `Agent(subagent_type=…)` personas like
  `rbg`/`pauli`/`marsha` can be spawned _as teammates_, honouring their `tools` allowlist and `model`,
  with the persona body appended to the teammate's system prompt.

The relevant architecture line: a team = **team lead + teammates + shared task list + mailbox**.
(Source: Claude Code docs, [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
and [Manage multiple agents with agent view](https://code.claude.com/docs/en/agent-view).)

## The precise cause of the James-as-leaf collapse

Two facts from the same docs combine to produce the silent collapse:

1. **Subagents are one level deep.** Subagents "run within a single session and can only report
   back to the main agent" — they do not message peers and, as leaf workers, cannot fan out to
   their own subagents.
2. **Teammates cannot nest either.** Agent teams' own limitations are explicit: _"No nested teams:
   teammates cannot spawn their own teams or teammates. Only the lead can manage the team."_

So whichever primitive is in play, **fan-out is a privilege of the top-level/lead session, not of a
spawned worker.** When an outer agent dispatches `Agent(subagent_type="james", …)`, James is a leaf
subagent. James's instructions tell him to commission rbg/pauli/marsha via `Agent(…)` — but a leaf
cannot spawn subagents, so those calls no-op or are unavailable. James then quietly performs all four
roles in his single context. A four-perspective review degrades to a one-agent review **with no error
surfaced** — the output is still shaped like a panel verdict, which is exactly what makes it dangerous.

The portable kernel of this fact (true on Claude _and_ Gemini-class harnesses): **a delegated worker
cannot re-delegate; only a top-level session or a team lead can fan out.**

## The fix: a capability ladder (walk to the highest tier the harness supports)

The dispatching agent — the **outer agent the user invoked**, not a worker it spawned — picks the
highest available tier:

### Tier A — Peer team (best fidelity; Claude Code with agent-teams enabled)

The outer agent launches a **four-member team**: `james` as lead, `rbg`/`pauli`/`marsha` as teammates
spawned from their subagent definitions. All four are peers with independent context; James (lead)
synthesises via the mailbox. Available iff the agent-teams primitive is present and enabled
(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, lead session in an interactive/`--bg` host that can manage a
team). This is the shape the parent task asked for.

### Tier B — Top-level orchestration (portable default)

The outer agent runs `review-pr` **in its own main session** — the main session _becomes_ James — and
commissions `rbg`/`pauli`/`marsha` as **one level of subagents** (`Agent(subagent_type=…)` on Claude;
`delegate_to_agent` on Gemini). The three reviewers run in their own contexts and report back; James
synthesises. This is the **default** and works on every harness that supports one-level sub-delegation.

The load-bearing rule that makes Tier B work: **invoke `review-pr` at the top level. Never nest James
one level down as a subagent.** If James is already a subagent, he is a leaf and Tier B is impossible
for him — see the guard below.

### Tier C — Single-session multi-pass (floor; any harness, incl. GHA and sub-delegation-less Gemini)

One session runs the four lenses **sequentially as self-roles** and **must disclose the degraded mode
explicitly** in its output ("single-session review — perspectives not independent"). No silent collapse.
The existing GHA `pr-reviewer.agent.md` is an instance of this floor: a portable single-agent reviewer
that applies the axiom/quality/strategy lenses itself because GHA runners have no plugin, no peers, and
no sub-delegation.

## The leaf-subagent guard (load-bearing)

Because the collapse is silent, the guard is mandatory, not advisory. **If James detects he is a leaf
subagent** — i.e. he cannot spawn the reviewer agents (the `Agent`/delegation tool is absent or its calls
do not produce independent workers) — he must **not** silently proceed as a one-agent panel. He must
either:

- **Escalate to the caller**: "I was dispatched as a subagent and cannot fan out to a peer panel.
  Re-dispatch `review-pr` at the top level (Tier B) or as a team lead (Tier A)." — preferred; or
- **Degrade with disclosure** (Tier C): run the four lenses himself and label the verdict as a
  single-session, non-independent review.

What James must never do: present a single-context, self-played four-role review as though four
independent perspectives were obtained.

## Vendor neutrality — the approach, stated explicitly

This design deliberately does **not** hard-depend on the Claude-only agent-teams primitive. Neutrality
is achieved by **describing the desired shape (four independent perspectives) plus a capability ladder**,
rather than a single mechanism:

- **Tier B is the portable default.** It needs only one-level sub-delegation, which every supported
  harness has (Claude `Agent`, Gemini CLI `delegate_to_agent`). A Gemini-CLI-class harness with no
  agent-teams primitive runs Tier B unchanged.
- **Tier A is an optional enhancement**, selected only by capability detection where the primitive
  exists and is enabled. Its absence costs nothing — the agent simply falls through to Tier B.
- **Tier C is the floor** for harnesses that lack even one-level sub-delegation (GHA runners; any
  client where delegation is unavailable). It always produces a review, with honest disclosure.

Why a ladder rather than "always sequential, let Claude parallelise": a flat sequential instruction
gives the orchestrator no signal that independent perspectives are the _point_, and no place to express
the leaf-collapse guard — which is the actual bug. The ladder makes "four independent perspectives" the
stated goal, names the highest-fidelity mechanism without depending on it, and gives every harness a
defined, non-silent rung.

## See also

- `aops-core/commands/review-pr.md` — the James orchestrator skill (consumes this doc at dispatch time)
- `aops-core/agents/james.md` — the James persona (carries the leaf-subagent guard)
- `.github/agents/pr-reviewer.agent.md` — the Tier C floor instance for GHA
- `specs/SURFACES.md` — which surfaces can dispatch onto what (agent teams need an interactive/`--bg` Claude host)
- Claude Code docs: [agent-teams](https://code.claude.com/docs/en/agent-teams), [agent-view](https://code.claude.com/docs/en/agent-view), [sub-agents](https://code.claude.com/docs/en/sub-agents)
