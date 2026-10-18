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
- Each material premise carries its basis, and a pointer wherever that basis rests on evidence.
- A premise about the state of something outside the report quotes the observed value of the field that decides it, beside the pointer.
- Each state claim rules out the nearest other state that would change the reader's next action. "Blocked on review" says whether review is awaited or changes were requested.
- The conclusion stays within its premises' scope and answers the original ask.
- The receiver answers with a verdict and a reason: PASS, REVISE or FAIL. A report not in the skill's shape goes back to its sender as REVISE.

### 3. Strength that survives every hop

As the user, I want each claim to reach me as strong as its evidence and no stronger, so that a guess relayed three times still arrives as a guess.

- Every claim keeps its basis at every hop.
- A derived claim takes the weakest basis among its premises.

### 4. Tested limits

As the user, I want every "it does not exist" or "I cannot" to rest on a test, so that a limit is never asserted from absence alone.

- A negative or capability claim cites a failed attempt with its verbatim error, or a bounded search with its query, scope and zero count.
- A claim that blames something outside the writer's own change cites a control run that isolates it, or travels as unestablished.

### 5. Honest endings

As an agent that could not finish, I want failure and partial delivery to be complete answers, so that I report what happened as it happened.

- "I could not do X, because Y" meets the contract.
- A partial report carries evidence for what shipped and discloses the deferred remainder under the partial-work coverage partition (`tested | declared-deferred | illegal-gap`, [partial-work spec](../polecat/spec-partial-work-tight-loop-delivery.md)).
- A deliverable is complete when the writer's own acceptance items are met, whatever follow-up depends on it.

### 6. Directions relayed intact

As the user, I want my directions to reach a worker as I gave them, so that an agent in the chain cannot add to what I asked.

- A relayed direction cites the original ask, and every detail, constraint and method in it can be derived from that ask.

## Terms

- **Load-bearing claim:** a claim the reader would act on, or that a conclusion rests on.
- **Pointer:** an identifier a reader can open: a commit and line, a span id, a PR or task id, a resolving URL. A pinpoint is best. A command counts as evidence only when its output is the evidence, and then the output is quoted.
- **Basis:** how the writer knows the claim. The vocabulary is defined once, in the `argdown-toulmin` skill.
- **Report format:** the report shape and verdict tokens are defined once, in the `premise-check` skill, which writes to the `argdown-toulmin` grammar. A task handback carries its receipts in that shape.
