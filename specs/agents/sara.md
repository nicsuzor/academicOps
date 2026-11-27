---
id: dispatcher-spec
title: Dispatcher
type: spec
description: What the dispatcher does, what it refuses, and the one capability its plugin ships
status: ready
tier: polecat
depends_on: [polecat-system, supervisor-spec]
tags: [spec, polecat, dispatch]
---

# Dispatcher

The dispatcher launches polecat containers on reified tasks and does nothing else.
Deciding what runs where belongs to the supervisor ([[specs/agents/james.md]]);
composing a task's instructions belongs to the custodian ([[specs/agents/reify.md]]).
The `sara` agent runs it.

## User Story

As a researcher delegating work to agents, I want one narrow process whose only
power is to start an isolated container on a task that is ready to run, so that
sending work away costs few tokens and can never turn into the dispatcher doing,
routing, or judging the work itself.

## Contract

- **Input**: one or more task IDs. Each task is `queued`, has no open `needs`
  dependency, has no container already running on it, and was reified just before
  the hand-over, so its body carries instructions a worker can complete from the
  prompt and its one repository alone.
- **Action**: stamps `origin_agent` on the task, then launches one polecat
  container per task without rewriting the task. The polecat service seeds the
  worker's prompt with the full task
  ([[specs/polecat/polecat-system.md]]).
- **Output**: for each task, its ID, whether the launch succeeded, and the launch
  parameters chosen. The dispatcher returns as soon as the launch call returns.
- **Not ready**: a task without composed instructions goes back to the supervisor
  as a clarification; the dispatcher does not reify it.
- **Everything else is refused**: no in-session execution, no local command-line
  agent, no routing between surfaces, no monitoring, and no completion sweep.

## What the plugin ships

`plugins/sara` carries the `sara` agent, the `dispatch` skill, and a `SessionStart`
hook that injects its `CORE.md`. Installing it gives a session remote dispatch;
leaving it out leaves a session that does all its work in-session. Polecat
containers never install it.

## Completion

The dispatcher does not wait. As each container is reaped, the polecat service
writes the completed task to the PKB with the worker's final output message.
Checking that report against the ask is the supervisor's job.

## Related

- [[specs/agents/james.md]] -- the supervisor: routing, verification, and the
  observability guarantee every delegation carries
- [[specs/polecat/polecat-system.md]] -- the isolated workspaces and delivery
  guarantees the dispatcher launches onto
- [[plugins/sara/skills/dispatch/SKILL.md]] -- the operative skill
