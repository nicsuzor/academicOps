---
name: dogfood
description: Standing experiment protocol for the academicOps project — every piece of real work is also evidence about the framework. Use when starting framework work of any type, testing instructions blind, trialling a runtime mechanism, or reviewing how well the framework served a task just completed.
---

# Dogfood — learn how the framework performs by using it

## Orientation (read this so nobody has to explain it to you)

academicOps exists so its user can **delegate execution without delegating judgment**. Its three goals: academic quality, strategic planning, ADHD accommodation. Its standing constraint: agent harnesses get smarter every day, so the framework must get _simpler_ over time — we do not patch agent behaviour, we evolve _processes_ (when skills fire, what contracts bind handoffs). Anything that reads like a crutch for a current-generation failure mode is a candidate for deletion, not refinement.

Because of this, **every piece of real work done with the framework is also an experiment on the framework**. This skill defines how that evidence gets captured and how it becomes change. You are always in exactly one mode below; know which.

## The loop

work → observe friction → **record evidence (never fix inline)** → detached review checks recurrence → change at the cheapest layer → re-test blind.

## Modes — pick by what you are starting

**1. live-trial** (default — any real task).
Do the work normally. When the framework helps or hurts — an instruction that misled you, a gate that fired uselessly, a contract that saved you, context you needed but couldn't find — file an evidence record (below) and keep working. Do not fix the framework mid-task on your own initiative; finish the work, then propose. If the user expressly approves a remedy, make the minimum, most general change and say what you changed.

**2. instruction-test** (blind delegated execution — testing a skill, workflow, or task template).
Give a contextless agent the instruction under test and the task _only_ — no coaching, no fixes mid-run; redirect a running agent rather than restarting it. Before reading the output, write down your hypothesis of where it will fail. Score the outcome against the instruction's own acceptance criteria, then have an independent agent score from scratch without seeing your read. If you edit the instruction, re-run blind: **≥2 runs per condition**, or you are measuring agent variance, not your edit.

**3. mechanism-trial** (new runtime mechanism: gate, hook, evaluator, classifier).
No mechanism is enabled without a pre-registration on the task record: hypothesis, promote criteria, kill criteria, review date. A mechanism whose experiment record has passed its review date without evidence is presumed dead — file the removal.

**4. planning-eval** (decomposition/planning quality).
Method and epistemics rubric: [references/decomposition-eval.md](references/decomposition-eval.md). Gold-standard pairs are single-use — once written anywhere the test agent can search, they are contaminated.

## Supervising a trial — when the run under test is someone else's

**This is a frame, not a fifth mode.** You hold it whenever the run you are scoring is someone else's — which is what modes 2–4 start. It sits alongside the mode you picked above rather than replacing it, so a session that is itself a live trial supervises another one without contradiction. Inside this frame several defaults invert, and they invert only here: applied to your own work, mode 1 is untouched, because there, doing the work _is_ the trial.

- **Do none of the work yourself.** What you are measuring is independent, contextless operation. Every hint you supply and every step you take on the subject's behalf is a variable you added to your own experiment. Your own tool-call record is what shows this held — no edits to the subject's tree, no coaching turns — and it is a channel the subject cannot author.
- **A halt is a result.** The fail-fast rule in [`.agents/CORE.md`](../../CORE.md) tells you to stop; here it also tells you what you have got. The subject being unable to proceed **is** the finding — record it and leave it blocked rather than solving it on the subject's behalf. An agent that thrashes its way past a gap converts a recordable framework defect into an unrecordable one, and not having correct instructions at the moment they were needed is exactly the defect class this protocol exists to catch. File it as an evidence record below — classification `instruction-gap`, and "no rule existed" is itself the finding — not as a line in your final report.
- **A blocked route is work, not an excuse.** "A halt is a result" governs the subject's run. It does not govern _your_ route: when the sanctioned path you were told to use will not carry the job, repairing it is the deliverable. Reporting the blockage and taking another road is the failure mode even when the other road works. Repair at the cheapest layer that closes the gap — the inputs you control first (a task created with the right status and properties), the instruction text last — and route it through **Turning evidence into change** below, where the record still comes first and express approval still binds.
- **Never trade away an ambition to make something pass.** Reduced scope, a disabled surface, one client working instead of both, a capability dropped because it was hard — these are not results, and presenting them as results is the failure. Say what is unreached and what it would take. You do not get to lower the bar by shipping the lowered version of it.
- **There is no binary done.** The minimum standard is world-class, not "working" and not "acceptable"; every outcome is assessed qualitatively and critically, and the bar rises as model capability and tooling improve.

Every bullet above terminates in **The evidence record** below, in the shape given there: one record per incident, filed to the PKB (project: aops) or as a GitHub issue, carrying what happened against what the instruction in force promised, a classification, and the impact. A supervision finding that exists only in your final report has not been filed, and the standard has not been applied.

Driving the run itself — choosing a surface, spawning the agent, and the tracking record that carries its acceptance criteria — is the [`debug`](../debug/SKILL.md) skill.

## Invariants — what keeps the results honest

- **Hypothesis before observation.** Written down first, every time. This is what lets you discover you were wrong.
- **Blind means blind.** The executing agent never sees the gold standard, your hypothesis, or verbal coaching.
- **The named surface is part of the instruction.** When a run specifies where it executes — a client, a container, an agent, a model — that surface is the condition under test. Run it there. A blocker is only a blocker once you have established it; until then it is an assumption, and an assumption is not grounds to move the run. Established and real? Report it and halt — a run moved to a surface you can reach measures that surface, not the one you were asked about.
- **Minimum, most general change — with express approval.** The session that hit the failure may author the remedy, but only the smallest change that closes the gap, pitched at the most general level that fixes the class rather than the instance. Nothing ships without the user expressly approving that change. No approval, no edit: file the record and stop. The gate is on remedies: any edit that would change what a future reader is told to do, however obviously right and however narrow it looks. Repair is not gated — undoing this session's own damage, or deleting a pointer to something that is not there. When you cannot tell which you have, it is a remedy.
- **Evidence is recurrence, not salience.** One painful incident is a data point. Three cited recurrences justify a mechanism; fewer justify at most a text change.
- **Record before you remedy.** File the evidence first, unedited, then propose. A fix written before the record contaminates the record.

## The evidence record

File to the PKB (project: aops) or as a GitHub issue — one incident per record:

- **What happened** vs **what the instruction/contract promised** (cite the instruction in force, by path or slug — "no rule existed" is itself a finding)
- **Classification**: instruction-gap · process-gap · harness-limit · genuine-bug · framework-win (successes are evidence too — they defend components at earn-their-keep review)
- **Impact**: what it cost, or saved
- **Remedy, if any, kept separate from the facts** — and never applied without express approval.

## Turning evidence into change

Any session may propose; only express approval authorises the edit. Work down the cost ladder — always the cheapest sufficient layer:

1. rule / instruction text
2. skill or process step
3. workflow contract (task-record criteria, breakpoints)
4. runtime mechanism (requires ≥3 recurrences + a pre-registration)

Every instruction change passes `/craft` (author mode) before deployment, then a blind re-test (mode 2) confirms the gap actually closed. Promotion of a tested instruction to canonical location, and follow-up tasks for residual friction, happen before the session ends — leave a loose thread, never a dropped one.
