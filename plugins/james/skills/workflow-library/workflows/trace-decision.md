---
description: Answer "how did this decision get made" about a past agent session -- assemble the session outline from the trace store via Phoenix MCP, with step durations, tokens and costs, and answer the question from it, citing the steps where the decision was made.
id: trace-decision
tags:
  - wf-template
  - observability
title: trace-decision
type: template
---

## What this step does

Answers a question about how or why an agent reached a decision, from the trace store's
record of the session that made it rather than from any agent's account of itself.

## Input contract

- The question, in the asker's words.
- An identifier for the session: a session ID / conversation ID, a session slug, a trace id, or enough to
  find one (a task id, an agent and a time window).

## Steps

1. **Resolve the session.** Resolve the owning `session.id` (UUID, slug, trace ID, task ID, or time window)
   via Phoenix MCP.
2. **Assemble and persist the outline.** Run the `phoenix` skill (`plugins/james/skills/phoenix/SKILL.md`)
   to assemble `<slug>.outline.md` (single condensed outline with built-in token/cost totals, step
   durations, prompts, model prose, and tool actions) via Phoenix MCP. Save the file to a durable
   destination (such as PKB note `out-<slug>` with literal local `~/...` host paths sanitized, or
   committed to the repository/PR branch) rather than leaving it in ephemeral scratch storage.
3. **Read narrowly.** Read `<slug>.outline.md` narrowly; when a step's bounded excerpt is insufficient
   to answer the question, fetch full payload fields via Phoenix MCP only for the targeted `span_id` values.
4. **Answer.** Say how the decision was made, citing `#t<turn>` and `#t<turn>-<step>` anchors where it
   happened, and the duration and cost of the work that led to it where relevant.

## Output contract

- The deliverable: the single persisted `<slug>.outline.md` artifact, saved to a durable location (PKB
  note `out-<slug>` with sanitized paths, or committed to the repository/PR branch).
- The answer, citing `#t<turn>` and `#t<turn>-<step>` anchors into the outline.
