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
- An identifier for the session: a session id, a session slug, a trace id, or enough to
  find one (a task id, an agent and a time window).

## Steps

1. **Resolve the session.** Turn the identifier into the owning session id. A task id or
   a time window resolves through the trace store's spans for that task or window.
2. **Assemble and persist the transcripts.** Run the `session-trace` skill's transcript
   script (`phoenix_transcript.py`) on the session. It fetches the session's spans in one
   paged sequence and generates two primary files: `<slug>.transcript.md` (full record with
   durations, tokens, and folded payloads) and `<slug>.outline.md` (condensed outline of prompts,
   model calls, and tool actions). Save both files to a durable destination (such as the PKB via
   `pkb_create` or committed to the repository/PR branch) rather than leaving them solely in an
   ephemeral container filesystem. When saving to the PKB, pass `--sanitize-paths` (or sanitize
   literal host filesystem paths) to satisfy PKB host-path guards.
3. **Read narrowly.** Read the summary and the outline, then open only the folded
   payloads of the steps that bear on the question, by anchor.
4. **Answer.** Say how the decision was made, citing the turn and step anchors in the
   transcript where it happened, and the duration and cost of the work that led to it
   where the question touches on them.

## Output contract

- The primary deliverables: the two generated transcript files (`<slug>.transcript.md` full
  and `<slug>.outline.md` condensed), saved to a durable location (PKB note/document or
  committed repository path; sanitized for PKB persistence).
- The answer, citing turn and step anchors into the transcript.
