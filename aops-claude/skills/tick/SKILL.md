---
name: tick
type: skill
description: Periodic check to nudge high intent epics along between steps.
---

# /tick: keep our epics moving

We do not yet have a good way of automatically enqueing work without manual dispatch or a long-running supervisor agent. We also have no reliable way to close the loop on tasks: if an agent finishes a task (success or failure), we don't have a way to follow up, even though the pkb does record current state.

This skill exists to make sure things keep moving through. It will be invoked periodically, manually, by nic.

## Instructions

1. Get a list of epics in flight, ordered by focus score descending. In flight here means started in some way or queued.

2. Reconcile before you judge anything stuck -- run `/reconcile` (batch mode) so "in flight" reflects what's actually finished or failed, not a queue status that's gone stale.

3. For each of these, check whether any tasks are currently dispatched and running. If so, skip to next.

4. You are looking for epics that have gotten stuck somehow. Those are the ones I want you to bump. Bump a couple per pass, not the whole list -- this is about clearing what's genuinely stuck, not draining the board in one go.

### Bumping an epic

Epics might be stuck for any number of reasons.

- Maybe they're waiting on a decision; you should figure out if you can resolve it yourself, or whether you need to bring it to nic's attention. Please do try not to bring it to my attention though.
- Maybe they're waiting on a PR approval, or a stuck CI run, or a draft pull request or changes requested on a PR. You know what to do; each epic should have a process that was baked into the task by the decomposition process, so just follow that. If that's not there, figure it out. Again, don't bother me with it if you can at all avoid it.
- If bumping means dispatching the next step and both the epic and one of its already-decomposed children are sitting ready, dispatch the epic, not the child -- I don't want to be pulled back in at every seam once something's been decomposed.
- Things genuinely waiting for me: I need to know. Put it in the daily note for a start, but also make sure that the decision point is assigned to me and shows up on the graph. Don't touch the manual intent lever, but an approval task that is blocking a high focus epic should show up on my dashboard automatically.

Once you have decisions that you need to bring to me, give me a brief summary and a recommendation for each through the AskUserQuestion tool. If I've just invoked this skill, it's likely I have time to talk through some quick decisions and unblock some tasks.

Don't pull a stuck epic's task bodies, transcripts, or PR diffs into your own context to work out what's wrong -- delegate that reading to a subagent and take back a short summary. You're triaging across many epics in one pass; reading deeply into all of them defeats that.

If bumping keeps failing the same way across a couple of passes, that's a systemic problem, not one more stuck epic -- stop bumping, flag it to me once, and wait rather than raising it every time you run. Same if something breaks at the infrastructure level: stop and say so rather than working around it. Nothing stuck is a fine outcome too -- no need to report it.

We'll figure out the rest as we go.
