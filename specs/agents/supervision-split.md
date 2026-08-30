---
id: supervision-split-spec
title: Supervision Doctrine — Where Rex's Charter Lives
type: spec
status: ready
tier: core
depends_on: [agent-authority-spec, supervisor-spec]
tags: [spec, agents, supervision, dogfood, rex, ida, framework]
created: 2026-08-07
---

# Supervision Doctrine — Where Rex's Charter Lives

`rex` is a project-local persona that ships in no plugin. For as long as its
supervision doctrine lived only in `.agents/agents/rex.md`, no other identity
could hold that standard — including `ida`, the only agent that talks to the
user. This spec records where each half of that charter now lives, and why.

## The split

| Material                                                                                                                                                                     | Home                                                      | Why there                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| The standard held while scoring someone else's run — do none of the work yourself, a halt is a result, a blocked route is work, never trade away an ambition, no binary done | `.agents/skills/dogfood/SKILL.md` § "Supervising a trial" | It is judgment about evidence, which is what the dogfood protocol governs. As a skill it is invocable by any identity, which is the point. |
| Driving a run — surface choice, background spawning, dispatch preconditions, and the tracking record carrying acceptance criteria                                            | `.agents/skills/debug/SKILL.md`                           | Project-local, like the material itself.                                                                                                   |
| Identity, the user-facing proxy role, and the two required workflows                                                                                                         | `.agents/agents/rex.md`                                   | Uniquely rex. Everything else is now a pointer.                                                                                            |
| The standard, referenced so `ida` holds it                                                                                                                                   | `plugins/aops/agents/ida.md` § "Dogfood duty"             | A pointer only. `ida` is shipped, so it names the skill rather than a project-local path.                                                  |

## Why the execution material lives in `debug` and not on the shipped launcher

The user delegated this call ("wherever it fits best"). Three things decided it.

1. **Shipped versus project-local.** The launcher, `plugins/orchestrate/agents/pc.md`, is
   shipped and project-agnostic. Rex's execution material names
   `make docker-build`, the gitignored `dist/`, aops PKB task statuses and
   `agy --agent james` — academicOps specifics that must not ship inside a
   project-agnostic surface. `.agents/skills/debug/` is project-local, as is
   `rex.md` itself.
2. **The launcher is scoped narrowly.** It does one thing: spawn a polecat,
   locally or over ssh, and halt on anything else. Rex's material is broader:
   choosing among headless `claude`/`agy`, a container, and fire-and-forget
   dispatch, then verifying which surface actually executed.
3. **Genre.** `debug` already carries the doctrine that a capability is scored on
   the instrumented tool-call record and never on what an agent says. Rex's
   execution material is the same genre of instruction.

## Deleted rather than moved

The no-duplication constraint made four components deletions, not migrations.
Each was already stated at an equal or higher authority:

- Rex's "never write a defect into an instruction" — `.agents/CORE.md`,
  "A defect is never a rule".
- Rex's "a reply is not a result" probe caution — `.agents/CORE.md`, "Proof comes
  from a channel the subject cannot author", and `.agents/skills/debug/SKILL.md`'s
  "Never score a capability on what the agent says".
- Rex's minimal-brief routing rule — `.agents/CORE.md`, "Outcome-oriented
  delegation".
- Rex's "academicOps framework objectives" paragraph — PKB node `aops-f770fe8a`,
  of which it was a near-verbatim copy. The excellence bar attached to it was
  genuinely absent elsewhere and did move, into `dogfood`.

Rex's manual connectivity probe was likewise dropped in favour of `debug`'s
scripted probes, which test the same thing and score it from the tool-call record.

Three further drops, recorded because a deletion missing from this section is
attrition rather than a decision:

- **`learn` running asynchronously in the background.** The obligation to turn a
  significant failure or unexpected success into a lesson survives in `debug`;
  the instruction to run it in the background did not. Reason: `.agents/CORE.md`'s
  "Outcome-oriented delegation" — specify what needs doing and the constraints,
  not the execution path.
- **The "search blindly or work around errors and you have already failed"
  block.** Covered twice over: `.agents/CORE.md`'s "Fail fast" carries
  stop-and-report, and `dogfood`'s "A halt is a result" carries the harder half —
  that not having correct instructions at the moment they were needed is the
  defect class the protocol exists to catch.
- **The explicit-request gate on driving a session interactively.** Rex's charter
  admitted interactive observation only on the user's explicit request, and
  nothing in the merged text reinstates that gate. **No reason is recorded for
  this one.** It was lost in condensation rather than decided, and it is named
  here so the next reader can decide it deliberately rather than inherit it.

## Two tensions this resolves, and one it does not

**Resolved — halt versus repair.** Rex's charter told the reader both to halt on
all errors without searching for a solution, and that a blocked route is work
rather than an excuse. In `dogfood` these are separated by whose run is blocked:
a halt in the _subject_ under test is the finding and is left blocked; a
sanctioned path that will not carry _your own_ job is a repair you owe.

This separates the two rules; it does not lower the halt. Halt-and-report remains
rex's default on hitting an error, stated in its own charter, and the repair
doctrine is the narrow exception to it — a route that will not carry the job at
all — never a licence to debug every failure encountered.

**Resolved — supervision versus mode 1.** "Do none of the work yourself" would
break `dogfood` mode 1, where doing the work is the trial. The supervision
material is therefore a delimited section scoped to modes 2–4, not an addition to
the skill's general invariants.

**Not resolved — ida cannot drive a run.** Rex's role as written includes direct
PKB writes and spawning named agents. `ida.md` reserves both: james is ida's only
subagent, surface selection is james's, and ida is not a writer to the PKB. The
authoritative wired map corroborates this at the architecture level. So ida now
_holds_ the supervision standard and _delegates_ the run; it does not select a
surface or open a tracking record itself. Which further capabilities should move
to ida, and what trust checkpoints gate each, is designed in
[Migrating Supervision Capability into Ida](ida-supervision-migration.md).
