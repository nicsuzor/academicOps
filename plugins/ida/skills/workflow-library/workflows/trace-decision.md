---
description: Answer "how did this decision get made" about a past agent session -- assemble the session's readable transcript from the trace store, with step durations, tokens and costs, and answer the question from it, citing the steps where the decision was made.
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

1. **Resolve the session.** Turn the identifier into the owning session ID / conversation ID. A task id or
   a time window resolves through the trace store's spans for that task or window.
2. **Assemble the transcript.** Run the `session-trace` skill's transcript script on the
   session. It fetches the session's spans in one paged sequence and writes the full
   transcript (one header per turn and per step, payloads folded, nothing truncated, with
   every step's duration and every model call's tokens and estimated cost) and an outline
   beside it.
3. **Read narrowly.** Read the summary and the outline, then open only the folded
   payloads of the steps that bear on the question, by anchor.
4. **Answer.** Say how the decision was made, citing the turn and step anchors in the
   transcript where it happened, and the duration and cost of the work that led to it
   where the question touches on them.

## Output contract

- The transcript and outline files, at a path the asker can open.
- The answer, with step anchors into the transcript.
