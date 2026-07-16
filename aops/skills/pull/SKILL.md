---
name: pull
description: Claim a queued task, execute it, update the record, and hand over.
---

All work must be tracked in the Personal Knowledge Base (PKB).
Each task has been carefully vetted before it is available for dispatch.
You must faithfully execute the task; it forms the extent of your obligations and the limits on your authority.
A task is not finished until its deliverables are met and all progress recorded in an update on the task object itself.
You are working in an isolated, temporary environment. Your changes here will only be saved if you follow the instructions and properly hand over the task to signal completion.
Your work will be LOST and DELETED if you halt execution without formally following the official task claim, update, and handover procedures exactly.

## Official Task Claim, Update, and Handover Procedures

1. Claim the task using the PKB MCP tool `claim_task` with the argument `task_id="TASK_ID"`.
   - "TASK_ID" is the unique identifier of the task to be claimed.
   - If you were not given a task ID, you must search the PKB for the task.
   - If you cannot find the correct task, you must HALT and inform the user.
   - Descend to sub-tasks if the selected task has children.

Claiming a task is critical to mark it as "in_progress" and assign the task to you.

The full requirements of the task will be returned on success.

2. Carefully read the task body and track each step and deliverable.
   - Use your native task list to track your progress.
   - Include ALL specified outstanding sub-tasks on your tracked list.
   - Include a verification step at the end of the list that requires you to check that all deliverables have been met and the acceptance requirements are satisfied.
   - Ensure that the last item on your tracked list is: "Handover (execute `/handover`)"

3. CHECK TASK STATUS=='queued' BEFORE EXECUTING
   - If the task status is not `queued`, you must HALT and inform the user that it is not yet ready for execution.

4. Execute each task step and track your progress.
   - Delegate steps and subtasks to specialist subagents or parralel agent teams as appropriate.
   - Use your judgment to determine efficient sequencing of steps and subtasks, operating in parallel when possible.
   - Always check the output of any delegated work carefully before accepting the result.
   - It is YOUR responsibility to re-dispatch any work that fails to meet the requirements to the highest standard.

5. **VERIFY COMPLETION**: On completion, you must FULLY check your work against EACH and EVERY task requirement.
   - Agents lie. DO NOT accept a claim from any subagent without INDEPENDENT VERIFICATION.
   - Technical compliance is not sufficient. Quality assurance is NOT a checklist exercise. The quality bar is nothing short of excellence.
   - Rectify any shortcomings you identify.
   - Your personal reputation is on the line here; do not certify a task as complete without absolute certainty that it has been delivered, in full, to a world-class standard.

6. **HANDOVER**: You MUST invoke the `/handover` skill to complete.
   - If you halt without formally invoking the skill, your completed work will be automatically DESTROYED.
   - The `/handover` skill will save your work and allow the task to proceed to the next stage.
   - Output the final message as directed by the handover skill.

**HALT ON ALL ERRORS**:

- DO NOT proceed if any check fails.
- DO NOT attempt to work around infrastructure or technical problems.
- Your authority is limited to PRECISELY what is defined in the task.
- If you are unable to complete a task, you MUST invoke the `/handover` skill and follow the instructions for failure.
