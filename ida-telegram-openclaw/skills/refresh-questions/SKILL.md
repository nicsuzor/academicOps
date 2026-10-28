---
name: refresh-questions
description: Sweep and refresh open questions in the Telegram Mini App by closing questions that are answered elsewhere, superseded, or asking for completed actions, and ensuring active open questions carry recommendations and context. Use when asked to refresh questions, sweep stale questions, or keep the Mini App decision queue current. Exclude for asking new questions or routine chat replies.
---

# Refresh Questions

Keep open questions in the Telegram Mini App current by sweeping pending questions against external state, closing settled inquiries with verified reasons, and verifying that open questions supply actionable recommendations and decision context.

## Workflow

1. **Enumerate Unresolved Questions**:
   - Fetch the active list of pending questions via `list_questions` or `GET /api/app/questions`.
   - If no questions are pending, conclude with an empty sweep summary.

2. **Evaluate External State per Question**:
   - For each pending question, inspect external state across repositories, task graphs, communication channels, and asking sessions:
     - _Completed Actions_: Check git commit logs, PR merge status, issue tracking, and system state for actions the question asked to approve or perform (such as a pull request merge or release deployment).
     - _Answered Elsewhere_: Check recent channel communications, asking session execution traces, and peer agent turns for answers or directives already delivered on other surfaces.
     - _Superseded or Obsolete_: Check whether subsequent questions, re-asks, or user steering instructions have replaced or rendered the decision moot.

3. **Close Settled or Stale Questions**:
   - Close each identified question via `close_question` or `POST /api/app/questions/close` (or `POST /api/app/questions/:id/close`), providing the required `question_id` and a mandatory, explicit `reason`.
   - Support every closure reason with primary citations:
     - Completed action: cite the exact merge commit SHA, PR number, or released tag.
     - Answered elsewhere: cite the channel message, session identifier, or confirmed decision.
     - Superseded: cite the newer question ID or direct user instruction.
     - Obsolete: cite the changed prerequisite or condition that eliminated the question.

4. **Verify Active Questions**:
   - Do not answer questions or select subjective choices on the user's behalf.
   - For any question remaining open, ensure it adheres to decision presentation standards:
     - Provides an explicit recommendation marked first (`(Recommended)`).
     - Supplies concise, self-contained context and rationale necessary to make an informed choice without requiring manual log lookups.

5. **Record Sweep Report**:
   - Summarize the disposition of every evaluated question: question ID, question text, outcome (`closed` or `kept`), stated reason, and primary citation.

## Must Not

- Must not answer questions, choose options, or guess user intent on the user's behalf.
- Must not close a question without an explicit stated reason supported by primary citations.
- Must not leave open decisions without a recommendation and context.
