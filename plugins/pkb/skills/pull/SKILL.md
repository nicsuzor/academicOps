---
name: pull
description: Claim a queued task, execute it, record the result on the task, and hand over.
---

# Pull

Claim a task from the Personal Knowledge Base (PKB) and manage an appropriately sized team of subagents to achieve the goal in line with the parameters and acceptance criteria.

## Dispatch procedure

You have a strong team of subagents available. Your job is to delegate to them and manage complex tasks to completion. The standard we are aiming for is nothing short of excellence.

Use your native tools to manage a team of subagents working in the background.

### 1. Claim

Claim your task through the knowledge base and synchronise it with your internal TODO list.

- Use the `pkb:services:pkb` MCP server to call `claim_task` with your task id.
- If you do not have a task id, search for the task by title using the `task_search` command.
- If you cannot find it with certainty, halt and report.

The return contract attaches to the **claimed** task — one deliverable, with evidence and an output URL — including the completed child tasks.

**Your authority does not extend to out-of-tree tasks:** you must stay within the scope of your granted authority within a task and its descendants. If your are blocked by an external task, you must do what you can and return any blocked work unfinished.

**Within the bounds of your task, you MUST exercise your discretion:** We are relying on you to make autonomous decisions about how best to achieve the goal in line with the parameters and acceptance criteria. You should try the most appropriate approach; even if it is not accepted at the review stage, providing a worked example helps the project maintainers to choose between options. Returning something and explaining the roads not taken is better than waiting for permission and returning nothing. You are working in an isolated environment; you can make changes without fear of causing damage.

### 2. Hydrate

Call on **`pauli`** to use the _`hydrate`_ skill to get the most up to date context for the task at hand. Ask `pauli` for all information -- strategic, operational, and theoretical -- whenever you start a new step or your instructions are ambiguous.

### 3. Dispatch

Work through your ToDo list, delegating to and managing subagents as required.

- Use your native tools to delegate subtasks to subagents.
- Execute tasks in parallel where the work allows.
- **Do not poll, sleep, or loop to wait for your agents**!
- **Stop after dispatch**; you will be awakened by a callback when tasks finish or need your intervention.

**4. Consolidate results quietly as they arrive:**

- Do not assemble interim reports.
- Once all work has been completed, prepare a consolidated and synthesized report for the user.
- Your report must include verbatim, well-referenced extracts of each logical claim you make.
- If a particular step proves impossible to complete (due to incomplete design or tooling limitations), you should **clearly state the work NOT done**; you should still complete any steps that do not rely on the failed work.
- Stop again if your background tasks are still running.

**5. Validate your report:**

Check your work against the literal requirements and acceptance criteria set out in the task.

- Provide evidence for each claim to ensure a reviewer has sufficient information to validate your work;
- **Do not** certify a task complete without certainty that it is delivered in full.
- Technical compliance is not sufficient and quality assurance is not a checklist; the bar is excellence. Rectify what falls short.

**INCOMPLETE WORK:**

- Loop back to step 2 to dispatch required changes.
- **Do not continue looping** if you are not making substantial progress each loop.

**If you cannot complete the task** due to lack of access, skills, tooling, instructions, or infrastructure, or other errors:

- **You must return the task FAILED.** This is not your fault: the task is undeliverable as designed.
- **You do not have authority** to repair work by changing the task instructions, acceptance criteria, or the pre-determined required workflow processes that you were initially provided.
- **Impossible tasks** must be marked 'failed' to signal that they must be _escalated_ for re-design or the error repaired before they can be re-dispatched.

**6. Handover (land the plane): Invoke `dump` Skill**

Conclude by invoking the `dump` skill to hand over. It records your work and lets the task proceed to the next stage.

- Your environment is EPHEMERAL. You must use the `dump` skill or your work will be DESTROYED.
- Your supervisor is STRICT. If you do not adhere precisely to the handover instructions, your work will be SILENTLY REJECTED and we will have to start the task over with a new agent.
