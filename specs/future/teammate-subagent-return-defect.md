---
status: draft
tier: 2
type: spec
title: Naming a subagent converts it to a teammate and discards its report
tags: [agents, dispatch, subagent, defect, evidence]
created: 2026-08-15
---

# Evidence — naming a subagent silently converts it into a "teammate", and its report is discarded

Observed 2026-08-15, session `polecat/session-e6cc0451`, Claude Code / Opus 5.

## Symptom

Four subagents spawned. Three emitted `idle_notification` with
`idleReason: "available"` and delivered **no report at all** — no findings, no
partial result, no stated failure reason. The fourth (`review-marsha`) never
returned within the session either.

`ListAgents` returned **"No reachable agents"** throughout — including
immediately after a successful spawn and immediately after a _successful_
`SendMessage` to the same agent. So the listing surface and the messaging surface
disagreed: messages delivered fine to agents the lister claimed did not exist.

## Diagnosis (Nic's, confirmed against the tool contract)

This is an **instructions/prompting bug, not a harness failure.**

Passing `name:` to the `Agent` tool creates a **team member**, not a plain
background subagent. The `SendMessage` contract states it outright:

> Your plain text output is NOT visible to other agents — to communicate, you
> MUST call this tool.

And the `Agent` tool's own `name` parameter:

> Name for the spawned agent. Makes it addressable via `SendMessage({to: name})`
> while running.

The three agents behaved as ordinary isolated background subagents: they wrote
their final report to their equivalent of stdout and exited. Under teammate
semantics that output goes nowhere. Nothing errored, so nothing surfaced — the
report was simply discarded, and the agent then idled as "available".

**Neither the spawning agent nor the spawned agent was told that naming changes
the return contract.** The agent bodies (`pauli.md`, `rbg.md`, `marsha.md`) all
instruct their occupant to _return a report_; none instructs it to return that
report via `SendMessage`.

## Exact invocations

All four used the `Agent` tool. The load-bearing argument is `name:` — present on
every one.

### 1. `pauli-advice`

```json
{
  "name": "pauli-advice",
  "subagent_type": "pkb:pauli",
  "description": "PKB advice on james/polecat topology",
  "prompt": "Hydrate and advise on a topology change Nic is about to make to the aops agent fleet. I need what the PKB already knows that would constrain, contradict, or duplicate it — not a summary of what I'm telling you. […full brief: 9 numbered end-state points, then 5 requested outputs — prior decisions that bind, contradictions, open/queued tasks, known failure modes, strategic read. Closed with: \"Be concrete and cite node ids. If the PKB has nothing on a point, say so plainly rather than reasoning it out from first principles — I need to know where the gaps are.\"]"
}
```

Result: `idle_notification`, `available`, **no report**. Pinged twice via
`SendMessage` with an explicit "send them now, in your reply" and a numbered
minimum list. Went idle again after each. Never delivered anything.

### 2. `review-rbg`

```json
{
  "name": "review-rbg",
  "subagent_type": "rbg:rbg",
  "description": "Rule-compliance review of plan",
  "prompt": "Judge this plan for rule compliance before it is dispatched for implementation. Artifact: /tmp/.../plan-james-split.md […standards to assemble in order: lib/axioms/, .agents/CORE.md, .agents/rules/RULES.md, specs/ARCHITECTURE.md + specs/agents/agent-authority.md; then 6 specific rulings requested — lib/ dispatch script vs duplication, cross-plugin MCP declaration, context7 vs no-defaults, commented allowedTools vs instructions-are-operative, referential integrity after the split, --agent none as magic value…] Return a verdict per finding with the rule cited and the specific plan item it lands on. Cite file:line for every rule you invoke."
}
```

Result: `idle_notification`, `available`, **no report**. Pinged once with the five
rulings restated. Nothing.

### 3. `review-pauli`

```json
{
  "name": "review-pauli",
  "subagent_type": "pkb:pauli",
  "description": "Strategic critique of plan",
  "prompt": "Strategic critique of a plan about to be dispatched for implementation. Run the premise test first, then architectural fit. […premise sentence; \"does this already run?\"; \"was this already decided?\" naming aops_e39b6b9d; then 3–4 lenses; then press hardest on the ida lockdown, the agy/claude seam, one-pass feasibility, and what it missed…] Return concrete findings with severity, each citing evidence (file:line, PKB node id, or a command and its output). Where the PKB has nothing on a point, say \"nothing recorded\" rather than reasoning it out."
}
```

Result: `idle_notification`, `available`, **no report**. Pinged once. Nothing.

### 4. `review-marsha`

```json
{
  "name": "review-marsha",
  "subagent_type": "orchestrate:marsha",
  "description": "Runtime/quality review of plan",
  "prompt": "Assess this plan for runtime correctness and content quality. Assume every claim in it is wrong until you have checked it yourself. […verify all 16 evidence rows F1–F16 against the actual file/line/command cited, reporting each CONFIRMED / WRONG / OVERSTATED; then judge as an instruction artifact; then check what it missed…] Render a verdict — PASS, FAIL, or REVISE — backed by concrete evidence with file:line or command output for every claim."
}
```

Plus a follow-up `SendMessage` adding the highest-priority empirical probe
(whether `agy --agent` still strips MCP tools).

Result: no report within the session.

### Contrast — the one channel that DID work

Direct MCP calls from the main session returned immediately and completely:

```
mcp__plugin_pkb_services__pkb__get_task   { id: "aops_e39b6b9d", max_bytes: 4000 }
mcp__plugin_pkb_services__pkb__search     { query: "agy --agent flag strips MCP tools,
                                            default agent in polecat container",
                                            detail: "snippet", limit: 8 }
```

Every PKB finding in the plan came from these, not from `pauli`.

## Why this is good news

Teammate semantics are a _stronger_ channel than plain subagent return, not a
weaker one: a live addressable agent that can be interrogated mid-run, and that
can push findings back as they land, is what the hooks were originally written
against. If teammates can be driven reliably, the hook-based handback contract
becomes usable again instead of being routed around.

## The fix, and what to test

Two candidate repairs. They are not exclusive.

1. **Tell the spawned agent the return contract.** If `name:` is passed, the
   prompt must instruct the agent to deliver its report via
   `SendMessage({to: "main", …})`, because its plain final output is discarded.
   Cheapest fix; testable immediately.
2. **Tell the spawning agent what `name:` costs.** Naming is currently a
   convenience for addressability with a silent, unadvertised change to the
   return contract. Either the agent bodies carry the obligation, or the
   dispatching surface stops naming agents it only intends to read a report from.

## Control test — SETTLED, the diagnosis is confirmed

The open question ("does an agent spawned _without_ `name:` return normally?") was
run and is answered: **yes.**

```json
{
  "subagent_type": "general-purpose",
  "description": "Control test: unnamed subagent return",
  "prompt": "This is a control test of the subagent return channel. Do exactly this and nothing more.\n1. Run: `git -C /workspace log --oneline -1`\n2. Return the exact output of that command as your final message, prefixed with `CONTROL_OK: `.\nDo not use SendMessage. Do not do any other work. Your final text output is the deliverable."
}
```

**No `name:` parameter.** Everything else identical — same session, same harness,
same permission mode, minutes after the four failures.

Returned in **6.0 s, 1 tool use, 21,788 tokens**:

```
CONTROL_OK: 250921f8d fix(build/agy): restore full tool vocabulary fallback for agents omitting tools:
```

The result arrived in the completion notification's `<result>` field — the exact
channel that was empty for all four named agents.

**Conclusion:** the single variable is `name:`. Passing it converts the spawn to
teammate semantics, under which the agent's final text output is discarded rather
than returned, and the agent then idles as "available". Nothing warns the spawner
or the spawned agent. Both fixes above are cheap, and fix (1) — instruct a named
agent to deliver via `SendMessage({to: "main"})` — is sufficient on its own.

## Failure-mode class

This belongs with the silent-failure family already recorded on this framework
(`aops_267a459a`, F13, F16): **nothing errored.** Exit was clean, the agents
reported themselves "available", and the absence of a report looked
indistinguishable from an agent that had not finished yet. A supervisor that did
not notice the missing reports would have proceeded believing a review had
happened.
