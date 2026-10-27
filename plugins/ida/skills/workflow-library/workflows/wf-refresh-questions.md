---
title: Refresh Mini App questions
type: template
description: Keeps open questions in the Telegram Mini App current by closing questions answered elsewhere, superseded, or asking for completed actions, and ensuring open questions carry recommendations and context.
tags:
  - wf-template
  - questions
  - mini-app
  - telegram
---

## What this step does

Sweeps all unresolved questions in the Telegram channel and Mini App question broker. For each pending question, it evaluates external state across repositories, task graphs, communication channels, and asking sessions. It closes stale, resolved, completed, or superseded questions with substantiated reasons, and validates that active open questions supply a concrete recommendation and sufficient context for the user to decide.

## Input contract

- Channel plugin question broker interface or endpoints (`list_questions` / `close_question` MCP tools, or `GET /api/app/questions` and `POST /api/app/questions/close`).
- Access to repository git status, commit logs, PR merge history, and active session traces.

## Obligations

1. **Enumerate Unresolved Questions**:
   - Fetch the active list of pending questions via `list_questions` or `GET /api/app/questions`.
   - If no questions are pending, conclude with an empty sweep summary.

2. **Evaluate External State per Question**:
   - For each pending question, evaluate whether the underlying inquiry has already reached resolution:
     - _Completed Actions_: Inspect repository commit history, pull request status, issue tracking, and system state for actions the question asked to approve or perform (such as a pull request merge or release deployment).
     - _Answered Elsewhere_: Inspect recent channel communications, asking session execution traces, and peer agent turns for answers or directives already delivered on other surfaces.
     - _Superseded or Obsolete_: Check whether subsequent questions, re-asks, or user steering instructions have replaced or rendered the decision moot.

3. **Close Settled or Stale Questions**:
   - Close each identified question via `close_question` or `POST /api/app/questions/close` (or `POST /api/app/questions/:id/close`), passing the required `question_id` and a mandatory, explicit `reason`.
   - The closure reason must cite primary evidence:
     - Completed action: cite the exact merge commit SHA, PR number, or released tag.
     - Answered elsewhere: cite the channel message, session identifier, or confirmed decision.
     - Superseded: cite the newer question ID or direct user instruction.
     - Obsolete: cite the changed prerequisite or condition that eliminated the question.

4. **Preserve and Qualify Active Questions**:
   - Do not answer questions or select subjective choices on the user's behalf.
   - For any question remaining open, verify that it adheres to decision presentation standards:
     - Provides an explicit, defensible recommendation marked first (`(Recommended)`).
     - Supplies concise, self-contained context and rationale necessary to make an informed choice without requiring manual log lookups.

5. **Record Sweep Report**:
   - Summarize the disposition of every evaluated question: question ID, question text, outcome (`closed` or `kept`), stated reason, and primary citation.

## Output contract

- Channel broker state updated: settled questions transitioned to closed status with reasons recorded on their cards.
- A scannable sweep summary listing each evaluated question, its outcome, and primary evidence.

## Must not

- Must not answer questions, choose options, or guess user intent on the user's behalf.
- Must not close a question without an explicit stated reason supported by primary citations.
- Must not leave open decisions without a recommendation and context.
