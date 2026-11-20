---
name: refresh-questions
description: Sweep and refresh open questions in the Telegram Mini App by closing questions answered elsewhere, superseded, or asking for completed actions, and ensuring active open questions carry recommendations and context. Use when asked to refresh questions, sweep stale questions, or keep the Mini App decision queue current. Exclude for asking new questions or routine chat replies.
---

# Refresh Questions

Keep the Telegram Mini App decision queue current by closing settled inquiries with cited reasons and verifying that remaining open questions supply actionable recommendations and context.

## Workflow

1. **Enumerate unresolved questions**:
   - Fetch pending questions via `list_questions` or `GET /api/app/questions`.
   - If none are pending, return an empty sweep summary.
2. **Evaluate external state per question**:
   - _Completed actions_: Check git history, PR merge state, issue trackers, and system state for actions the question asked to approve or run.
   - _Answered elsewhere_: Check recent channel messages, asking session traces, and peer turns for answers or directives already delivered on another surface.
   - _Superseded or obsolete_: Check whether newer questions, re-asks, or changed prerequisites rendered the decision moot.
3. **Close settled questions with primary citations**:
   - Close each settled item via `close_question` or `POST /api/app/questions/close` (`POST /api/app/questions/:id/close`) with `question_id` and a mandatory `reason` backed by primary evidence:
     - Completed action: merge commit SHA, PR number, or release tag.
     - Answered elsewhere: channel message, session identifier, or recorded decision.
     - Superseded or obsolete: newer question ID, direct user instruction, or changed prerequisite.
4. **Verify active open questions**:
   - Leave subjective choices and unanswered decisions open for the user -- never answer or guess intent on the user's behalf.
   - Confirm each remaining open question lists an explicit `(Recommended)` option first and supplies self-contained context and rationale. Flag any active question missing either element.
5. **Report sweep disposition**:
   - Summarize every evaluated question with `question_id`, question text, outcome (`closed` or `kept`), stated reason, and primary citation.
