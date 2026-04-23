---
name: dogfood
type: skill
category: meta
description: Delegated instruction testing — write instructions, commission contextless execution, observe friction, iterate, review quality, codify.
triggers:
  - "dogfood"
  - "test these instructions"
  - "instruction testing"
  - "delegated execution test"
modifies_files: true
needs_task: true
mode: execution
domain:
  - meta
  - framework
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, Skill
model: opus
version: 0.1.0
permalink: skills-dogfood
---

# /dogfood — Delegated Instruction Testing

## Purpose

Test whether a set of instructions produces good outcomes when executed by a contextless agent. The dogfooder does NOT do the work — they write instructions, delegate execution, observe what happens, and improve the instructions.

This skill is the **outer loop** that wraps any task category. The inner loop (execute/reflect/codify per step) is documented in `specs/future/dogfood.md` and applies within each phase below.

## When to Use

- Building or improving a skill, workflow, or command
- Testing whether instructions are sufficient for delegation
- Evaluating framework capabilities on real work
- Any situation where "can a contextless agent do this well?" is the question

## Workflow

### Phase 0: Know What You're Eating

**Goal**: Understand the system being dogfooded well enough that your instructions won't send the subagent down a dead end.

This phase exists because of a specific, observed failure: a dogfooding supervisor concluded a task was impossible because "the data doesn't exist" — when the data was in the session transcripts and hook logs, documented in the framework's own forensics workflow. The supervisor had the right files in their research but didn't connect the dots.

**Before writing any instructions:**

1. **Read the relevant framework workflows.** Check the `/framework` skill's workflow router. If the task touches hooks/gates, read `09-session-hook-forensics.md`. If it touches skills, read the relevant SKILL.md. If it touches transcripts, read `transcript.py` and understand the data pipeline.

2. **Verify data sources by sampling.** Do not ASSUME what a data file contains. READ one. If you're writing instructions that say "audit files contain X," open an audit file and confirm X is there. If it isn't, find where X actually lives.

3. **Map the full data landscape.** For any framework component, there are typically multiple data sources at different levels of detail:
   - **Pre-rendered markdown transcripts** (`~/.aops/sessions/transcripts/`) — abridged and full forms, ~10K+ files. This is the most accessible source for any session-level analysis.
   - **Raw session logs** (JSONL/JSON in `~/.aops/sessions/client-logs/`)
   - **Hook event logs** (JSONL in `~/.aops/sessions/hooks/`) — contains SubagentStart/SubagentStop events with verdicts
   - **Subagent transcripts** (referenced by `agent_transcript_path` in SubagentStop events)
   - **Session metadata** (JSON in `~/.aops/sessions/polecats/`)
   - **Audit files** (input documents sent to review agents — INPUT, not output)

   The audit file for a component is its INPUT, not its OUTPUT. The output lives in the subagent transcript and the hook event log. The full session transcript (markdown or JSONL) contains the complete conversation including what happened before and after any component fired.

   **When a command like `ls *.md` returns nothing on a large directory, try `ls <dir>/ | head` instead.** Glob expansion failures on 10K+ files are silent.

4. **Understand the difference between "not in this file" and "doesn't exist."** If a data point isn't in the file you're looking at, ask where else it might be before concluding it's unavailable.

5. **Trace the full data flow for multi-component systems.** If evaluating a system with multiple components (e.g., gate + subagent + main agent), map how data moves between them. A conclusion about "does X work?" requires knowing which channel delivers the result and whether the recipient sees it. Don't assume the obvious channel is the only one.

### Phase 1: Research and Draft Instructions

**Goal**: Produce a self-contained instruction document that a contextless agent could follow.

1. **Understand the domain.** Read existing skills, specs, and infrastructure related to the task category. Don't draft from imagination — draft from evidence of what exists.

2. **Identify the data.** Where does the input come from? What format is it in? What's the expected output? A contextless agent can't ask you — the instructions must answer these questions. **Verify by reading sample files** — don't describe data you haven't inspected.

3. **Write the instructions.** Work directly in the target skill file if the instructions are mature enough to belong there. Only use `specs/drafts/` for scaffolding that doesn't yet fit anywhere — and **delete it when the session ends**. The document must be self-contained:
   - What to do and why
   - Where to find the data (exact paths, not variables the agent won't have)
   - How to sample if the data is large
   - What to assess and how to structure the output
   - Where to save the output
   - Ground rules (evidence standards, uncertainty handling)

   Learnings that belong in a skill go into the skill immediately. Learnings too narrow for the skill go into PKB. Don't leave stray markdown files in the repo.

4. **Reflect before delegating.** Read the instructions as if you knew nothing about this codebase. What's ambiguous? What requires knowledge the agent won't have?

### Phase 2: Commission Contextless Execution

**Goal**: Test the instructions by delegating to an agent with NO prior context.

1. **Scope the first iteration small.** Start with N=2 representative tasks. Verify the pipeline accepts tasks, workers spawn, and output is observable before scaling. Only increase batch size when the first N=2 run completes cleanly. Finding 2 failures from 2 tasks is as informative as 2 failures from 10 — at a fraction of the cost.

2. **Launch a subagent** with ONLY the instruction file as context. Do not brief it verbally — if the instructions need verbal supplementation, they're incomplete.

   ```
   Agent(
     prompt="You are a contextless reviewer. Your ONLY instructions are in: <path>. Read that file, then follow its instructions exactly. Note any friction.",
     run_in_background=true
   )
   ```

3. **Do not interfere.** Let the agent succeed or fail on the instructions alone. The friction IS the data.

   **Exception — redirect, don't kill.** If new guidance arrives while the agent is running and making progress, use `SendMessage` to redirect scope rather than `TaskStop` + restart. Only use `TaskStop` if the agent is actively causing harm (wrong files, dangerous scope expansion). A scope-narrowing correction (e.g. "do 2 tasks not 10") does not justify a kill-and-restart — send the update and let the agent self-correct. Killing a productive agent discards accumulated work and pays full cold-start cost on the replacement.

4. **Record what happens.** When the agent completes, **read the full output** — not just a summary. Note:
   - Did it find the data? If not, what was missing from the instructions?
   - Did it understand the task? Where did it misinterpret?
   - Where did it get stuck? Was that because the instructions were wrong, ambiguous, or assumed knowledge the agent didn't have?
   - Was the output well-structured?
   - Was the output useful (not just complete, but actually insightful)?
   - **Did it discover something you didn't expect?** The subagent may find real issues with the system being evaluated, not just issues with the instructions. Both matter.

### Phase 3: Friction Analysis and Iteration

**Goal**: Update the instructions based on observed difficulties.

1. **Read the subagent's output.** Evaluate against the original objectives — not "did it follow the steps" but "did it produce something valuable?"

2. **Categorize friction:**

   | Friction type                                | Fix                                  |
   | -------------------------------------------- | ------------------------------------ |
   | Missing path or data source                  | Add to instructions                  |
   | Ambiguous assessment criteria                | Sharpen the question                 |
   | Agent couldn't find something                | Add discovery commands               |
   | Agent misunderstood the goal                 | Rewrite the objective section        |
   | Agent produced shallow analysis              | Add examples of good vs bad analysis |
   | Agent went off track                         | Add guardrails or constraints        |
   | Instructions too long/complex                | Simplify, split into phases          |
   | Data format wasn't what instructions assumed | Update data source description       |

3. **Update the instructions.** Edit them in-place (skill file, or wherever they now live). Be careful not to over-fit to this specific execution — the instructions should work for the category of task, not just this instance.

4. **Optionally re-run.** If friction was severe (agent couldn't complete the task), commission a second contextless execution with the updated instructions. If friction was minor (agent completed but output could be better), one iteration may suffice.

### Phase 4: Independent Quality Review

**Goal**: Assess HOW WELL the delegated work was carried out, not just whether it was done.

This is the hardest phase. Commission a separate reviewer agent — ideally a different model or agent type — to evaluate the subagent's output against the original objectives.

1. **Commission the review.** Use the critic agent or James (orchestrator):

   ```
   Agent(
     subagent_type="aops-core:critic",
     prompt="Review the following report against these objectives: <objectives>. The report is at: <path>. Assess depth, accuracy, specificity, and actionability. Be brutal — adequate is not good enough."
   )
   ```

2. **Evaluate the review.** The reviewer's assessment tells you about BOTH the instructions and the execution:
   - If the execution was poor but instructions were clear → the task may be too hard for this agent tier
   - If the execution was shallow because instructions didn't specify depth → fix the instructions
   - If the execution was good but missed important angles → add those angles to instructions
   - If the reviewer identifies structural framing errors (e.g., burying the primary finding as one recommendation among many) → add explicit structural requirements to the instructions
   - If the reviewer finds the subagent violated framework principles in its own analysis (e.g., keyword-matching recommendations that violate P#49) → add guardrails against those specific anti-patterns

### Phase 5: Codify

**Goal**: Produce reusable skill components from what you learned.

1. **Promote instructions to a skill or command.** If the instructions work well enough for delegation, they belong in `aops-core/skills/` or `aops-core/commands/`, not in `specs/drafts/`.

2. **Generalize.** Review the instructions for over-specificity to this one execution. Would they work for:
   - A different time period?
   - A different aspect of the same system?
   - A different reviewer agent?
   - A slightly different question in the same category?

3. **File follow-ups.** If the dogfooding revealed issues beyond the instructions themselves (framework bugs, missing data, broken tools), file tasks for those separately. **Always file follow-up tasks for friction items, promotion work, and unfinished phases.**

4. **Assess category coverage.** Does this one example adequately test the skill, or is the category broad enough that another example from a different part of the space would reveal new issues? Common reasons to run another example:
   - The first example was narrow (e.g., only one platform, one time period, one data source)
   - The quality review revealed structural issues that the updated instructions haven't been tested against
   - The subagent's output was good enough that iteration was minor — you haven't stressed the instructions enough to find their limits

## Key Principles

1. **You are testing the instructions, not doing the work.** If you find yourself doing the analysis, you've left the dogfooding lane.

2. **Friction is data, not failure.** A subagent that gets stuck reveals an instruction gap. That's the point.

3. **Don't over-fit.** Instructions should work for the category, not just this specific instance. If you add "look in ~/.aops/sessions/hooks/" that's fine (it's where the data lives). If you add "look for session hash b9555bcd" that's over-fitting.

4. **Quality review is not optional.** Without independent assessment, you can't distinguish "the agent did what I said" from "the agent produced something valuable." These are different.

5. **One iteration minimum, two maximum.** If the first subagent run was a disaster, iterate once and re-run. If it was decent, iterate once and move to review. Don't loop forever.

## Scope Note

When dogfooding, the agent has scope over both the task being executed AND the instructions being tested. Inline fixes to the instruction artifact are not scope expansion — they are the task. Custodiet should not flag this.

## Common Failure Modes

These were observed during dogfooding runs and should be watched for:

| Failure mode                                                                            | What happened                                                                                                                                                                                         | Prevention                                                                                                                                                         |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Concluded task was impossible when data existed elsewhere**                           | Supervisor accepted "verdicts not in audit files" as "verdicts don't exist" — when session transcripts and hook JSONL contained everything needed                                                     | **Phase 0**: Read framework workflows, verify data by sampling, map the FULL data landscape before writing instructions                                            |
| **Didn't read the relevant framework workflow**                                         | The forensics workflow documents exactly how to find RBG verdicts in hook logs. Supervisor never read it.                                                                                             | Phase 0: Check the /framework skill's workflow router. If the task touches hooks/gates, read the forensics workflow FIRST.                                         |
| Wrong assumption about data format                                                      | Instructions said "audit files contain RBG verdicts" — they contain input to RBG, not output                                                                                                          | Verify data sources by reading samples BEFORE writing instructions                                                                                                 |
| Accepted subagent's "impossible" finding without verification                           | Subagent reported data gap → supervisor iterated on acknowledging the gap rather than questioning the premise                                                                                         | When a subagent reports a task is impossible or data is missing, VERIFY before accepting. P#26 applies to your subagent's claims too.                              |
| Silent glob failure hid 10K+ files                                                      | `ls ~/.aops/sessions/transcripts/*.md` returned empty because shell glob expansion failed on 10K+ files — supervisor concluded no transcripts existed                                                 | Use `ls <dir>/ \| head` instead of `ls <dir>/*.ext` for large directories. When a command returns nothing, question WHY before concluding the data isn't there.    |
| Fragile shell commands                                                                  | `sed` commands broke when file naming convention changed                                                                                                                                              | Describe what to extract, not specific commands. Let the agent figure out the parsing.                                                                             |
| Quality reviewer finds structural framing errors                                        | Report buries the primary finding as one recommendation among many                                                                                                                                    | Add explicit structural requirements (e.g., "executive summary must state data limitations first")                                                                 |
| Quality reviewer finds framework principle violations in the subagent's recommendations | Keyword-matching recommendations violated P#49                                                                                                                                                        | Add guardrails against specific anti-patterns in the ground rules                                                                                                  |
| Writing draft artifacts before review completes                                         | Skill files written before quality feedback received                                                                                                                                                  | Draft early (that's fine), but mark them as drafts and plan to revise after review                                                                                 |
| Unreproducible quantitative claims                                                      | Subagent counted "68 events" for a session that had 15 — used keyword grep that included unrelated event types                                                                                        | Instructions must require documented counting methodology. Quantitative claims need the exact command that produced them, so reviewers can spot-check.             |
| Keyword classification of free-text verdicts                                            | Subagent classified RBG verdicts by keyword presence in analytical reasoning, inflating false positive count                                                                                          | If classification requires judgment (OK vs WARN in free text), document rules and acknowledge margin of error. Don't present rough counts as precise.              |
| Mischaracterized enforcement architecture                                               | Iteration 2 concluded "zero enforcement" because it examined only the gate system message (always "Compliance verified"), missing that the agent receives verdicts directly via the Agent tool result | Verify the actual delivery mechanism before making claims about enforcement channels. Trace the full data flow: who sends what to whom, and through which channel. |
| Useless early samples wasted deep-review time                                           | Instruction to sample from "earliest week" led to March sessions with empty narratives and free-text verdicts — infrastructure failures, not compliance test cases                                    | Qualify sampling guidance by data quality: note which periods have usable structured data vs. which are infrastructure-failure era                                 |
| Subagent found real findings but misframed aggregate conclusion                         | Iteration 2's session-level analysis was correct (RBG accuracy, false positives, etc.) but the aggregate conclusion ("zero enforcement") was wrong because it examined the wrong enforcement channel  | When aggregating, verify that the aggregate conclusion follows from the individual findings. A correct finding + wrong causal chain = wrong conclusion.            |
| Full batch dispatched on first iteration                                                | Agent dispatched N=10 tasks on iteration 1; user had to intervene. Two failures from 2 tasks is as informative as 2 from 10 at a fraction of the cost.                                                | **First iteration scope**: cap at N=2. Verify pipeline health before scaling.                                                                                      |
| Killed productive agent on scope correction                                             | Scope narrowing arrived mid-run; agent used `TaskStop` + restart instead of `SendMessage`. Discarded real findings, paid full cold-start cost on replacement.                                         | Use `SendMessage` to redirect a running agent. Only `TaskStop` for active harm (wrong files, dangerous expansion).                                                 |
| Created draft spec file instead of editing skill                                        | Agent wrote `specs/drafts/dogfood-instructions.md` as working artifact rather than editing the skill directly. File persisted after session, cluttering the repo.                                     | Work directly in the skill file. Use `specs/drafts/` only for scaffolding; delete it when the session ends.                                                        |
| **Concluded task without filing follow-up**                                             | Agent finished work but didn't leave a loose thread in the PKB                                                                                                                                        | **Always leave a loose thread.** Before exiting, file a task for what comes next.                                                                                  |

## Handover

**Always leave a loose thread.** Before exiting, file a follow-up task for any friction items, instruction promotions, or unfinished phases. A summary in chat is not enough; the next step must exist in the PKB as a discrete task.

## Related

- `specs/future/dogfood.md` — the inner-loop spec (per-step reflection)
- `.agents/skills/framework/workflows/10-reflective-execution.md` — the workflow version
- `aops-core/commands/retro.md` — single-transcript review (a task this skill might dogfood)
- `aops-core/commands/trend-review.md` — multi-session trend analysis (a task this skill might dogfood)
- `aops-core/skills/qa/SKILL.md` — quality assessment (used in Phase 4)
