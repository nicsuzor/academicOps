---
id: enforcement-evidence-contract
title: The Evidence Contract
type: spec
status: draft
tags: [enforcement, verification, evidence-contract, premise-check]
---

# The Evidence Contract

Every report one agent passes to another meets one contract: each load-bearing claim in it carries checkable evidence or a stated failure reason. The contract binds the writer of a report and its receiver. How the framework enforces it is in [evidence-contract-enforcement.md](evidence-contract-enforcement.md).

## User stories

### 1. Claims I can check

As the user, I want every claim that reaches me to carry evidence I could check, or a plain statement of why the work could not be done, so that I act only on claims someone can back.

- Each load-bearing claim carries a pointer with its basis, or a stated failure reason.
- Each pointer opens without the writer's transcript, and says what its claim asserts.
- An acceptance criterion is ticked on direct evidence of that item. An item without such evidence stays unticked, with its limit stated beside it.

### 2. Reports a receiver can judge as they stand

As an agent receiving a report, I want to judge it from the report alone, so that I can pass it on or send it back without redoing the work.

- The report is in the shape the [`premise-check` skill](../../plugins/ida/skills/premise-check/SKILL.md) defines.
- The report opens with the ask in the asker's own words, one question per line, each carried by an immutable id: `tg-<message id>` for a Telegram message, `<task id>/AC<n>` for a task's acceptance criterion. The writer copies the ask it was given and never substitutes its own title for it.
- Each material premise carries its basis, and a pointer wherever that basis rests on evidence.
- A premise about the state of something outside the report quotes the observed value of the field that decides it, beside the pointer.
- Each state claim rules out the nearest other state that would change the reader's next action. "Blocked on review" says whether review is awaited or changes were requested.
- The conclusion stays within its premises' scope and answers each ask by its id, or says the ask has no answer.
- The receiver takes an observed premise with a pointer as given: it never opens a pointer or re-determines an observed fact. It judges everything else: every warrant, step, scope and fit between rule and case. When a ruling turns on a fact the report lacks, the receiver sends the report back naming the missing premise.
- The receiver tests each material step for sufficiency. A warrant stands as stated when it is obvious, backed by a cited rule or verdict, or carries a claim cheap to reverse. A warrant that is complex, unbacked and high-stakes goes back for one level of decomposition.
- The receiver answers with a verdict and a reason: PASS, REVISE or FAIL. A format breach that leaves every step judgeable is waived and listed in the reason; an untested inference never passes.

### 3. Verdicts I can audit

As the user, I want every verdict to carry a reason I can hold against the report it judged, so that a PASS shows what was tested rather than asserting it.

- The reason is a checkable artefact with required content: seven keyed lines (`Judged`, `Valid`, `Supported`, `Answered`, `Sufficient`, `Waived`, `Relay`) in the form the skill's [checker's reason](../../plugins/ida/skills/premise-check/references/checker-reason.md) defines. Its ask ids, inference entries, weakest basis and relay lines can each be held against the judged report.
- A message that makes no claim takes a one-line no-claim reason, and its verdict is marked no-claim.
- Each verdict has a verification id that resolves to the recorded verdict and the text it judged.

### 4. Strength that survives every hop

As the user, I want each claim to reach me as strong as its evidence and no stronger, so that a guess relayed three times still arrives as a guess.

- Every claim keeps its basis at every hop.
- A derived claim takes the weakest basis among its premises.
- A premise resting on another agent's report cites the verdict recorded on that report. A cited verdict resolves to a recorded verification id; a report cited without one is weighed as unchecked.
- Each sentence relayed upward names the line of the checked argument it restates. A sentence with no line is not relayed.

### 5. Tested limits

As the user, I want every "it does not exist" or "I cannot" to rest on a test, so that a limit is never asserted from absence alone.

- A negative or capability claim cites a failed attempt with its verbatim error, or a bounded search with its query, scope and zero count.
- A claim that blames something outside the writer's own change cites a control run that isolates it, or travels as unestablished.

### 6. Honest endings

As an agent that could not finish, I want failure and partial delivery to be complete answers, so that I report what happened as it happened.

- "I could not do X, because Y" meets the contract.
- A partial report carries evidence for what shipped and discloses the deferred remainder under the partial-work coverage partition (`tested | declared-deferred | illegal-gap`, [partial-work spec](../polecat/spec-partial-work-tight-loop-delivery.md)).
- A deliverable is complete when the writer's own acceptance items are met, whatever follow-up depends on it.

### 7. Directions relayed intact

As the user, I want my directions to reach a worker as I gave them, so that an agent in the chain cannot add to what I asked.

- A relayed direction cites the original ask, and every detail, constraint and method in it can be derived from that ask.

## Terms

- **Load-bearing claim:** a claim the reader would act on, or that a conclusion rests on.
- **Pointer:** an identifier a reader can open: a commit and line, a span id, a PR or task id, a resolving URL. A pinpoint is best. A command counts as evidence only when its output is the evidence, and then the output is quoted.
- **Basis:** how the writer knows the claim. The vocabulary is the skill's.
- **Ask id:** the immutable id an ask travels under, from the asker to the final answer: `tg-<message id>` or `<task id>/AC<n>`.
- **Report format:** the report shape, basis vocabulary, verdict tokens and checker's reason are defined once, in the `premise-check` skill.
- **Task-record handback:** a worker's handback written to its task record's `## Report` section. It is a report like any other: the agent that reads it checks it with the task id as claim id, and writes the verdict back to the task record under `## Premise-Check Verdict`.
