---
name: tick
type: skill
description: Periodic check to nudge high priority epics along between steps.
---

# /tick: keep our epics moving

We do not yet have a good way of automatically enqueing work without manual dispatch or a long-running supervisor agent. We also have no reliable way to close the loop on tasks: if an agent finishes a task (success or failure), we don't have a way to follow up, even though the pkb does record current state.

This skill exists to make sure things keep moving through. It will be invoked periodically, manually, by nic.

## Instructions

1. Get a list of epics in flight, ordered by focus score descending. In flight here means started in some way or queued.

2. For each of these, check whether any tasks are currently dispatched and running. If so, skip to next.

3. You are looking for epics that have gotten stuck somehow. Those are the ones I want you to bump.

### Bumping an epic

Epics might be stuck for any number of reasons.

- Maybe they're waiting on a decision; you should figure out if you can resolve it yourself, or whether you need to bring it to nic's attention. Please do try not to bring it to my attention though.
- Maybe they're waiting on a PR approval, or a stuck CI run, or a draft pull request or changes requested on a PR. You know what to do; each epic should have a process that was baked into the task by the decomposition process, so just follow that. If that's not there, figure it out. Again, don't bother me with it if you can at all avoid it.
- Things genuinely waiting for me: I need to know. Put it in the daily note for a start, but also make sure that the decision point is assigned to me and shows up on the graph. Don't touch the manual priority lever, but an approval task that is blocking a high focus epic should show up on my dashboard automatically.

Once you have decisions that you need to bring to me, give me a brief summary and a recommendation for each through the AskUserQuestion tool. If I've just invoked this skill, it's likely I have time to talk through some quick decisions and unblock some tasks.

We'll figure out the rest as we go.
