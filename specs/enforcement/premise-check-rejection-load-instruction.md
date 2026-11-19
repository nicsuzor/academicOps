---
title: Premise-Check Load Instructions in Argument Rejections and Refusals
status: ready
---

# Premise-Check Load Instructions in Argument Rejections and Refusals

Specifies how every rejection or refusal of a report or hand-back concerning its argument explicitly instructs the author or checker to load the `premise-check` skill before authoring the replacement. This covers all three rejection surfaces: the hearsay gate's absent-argument notice, verdict-recorder tool refusals, and checker revision requests returned under the skill.

## User stories

### US-1 Hearsay Gate Absent-Block Notice

As an agent receiving an incoming report or hand-back lacking a required argument, I want the gate's absent-block notice to instruct me to tell the sender to load the `premise-check` skill, so that the sender loads the governing skill before drafting the resubmission.

- **AC-1.1** Given an incoming agent envelope requiring an argument (such as a subagent hand-back, peer message, or task notification with results), when the envelope contains no fenced `argdown` block, then the gate arms and emits a notice directing the receiver to send the message back for revision and instruct the sender to load `ida:premise-check` before resending.
- **AC-1.2** Given an absent-block notice emitted by the gate, when formatted for the receiver, then the notice carries the exact command to record `REVISE` with reason "no argument supplied" and explicit text directing the sender to load the skill.

### US-2 Verdict-Recorder Refusals

As a checker recording a verdict or an author reviewing tool output, I want every recorder refusal to state actionable remediation that tells the relevant agent to load the `premise-check` skill, so that subsequent submissions conform to the skill's dialect rather than unconstrained public priors.

- **AC-2.1** Given a verdict recording attempt of `PASS` on a message where an argument block was expected but absent, when evaluated by the recorder, then the recorder refuses `PASS` with an error instructing the checker to return the message for revision and mandate that the sender load `ida:premise-check`.
- **AC-2.2** Given a verdict recording attempt of `PASS` on an argument block that fails deterministic parser checks, when evaluated by the recorder, then the recorder refuses `PASS` with an error detailing the syntax defect and instructing that the author load `ida:premise-check` before resubmitting.
- **AC-2.3** Given a verdict recording attempt of `PASS` on an argument with zero inference lines, when evaluated by the recorder, then the recorder refuses `PASS` and instructs that bare assertions cannot pass and require revision under `ida:premise-check`.
- **AC-2.4** Given a verdict recording attempt where the checker's reason omits required keyed lines or violates the reason schema, when evaluated by the recorder, then the recorder refuses the verdict and instructs the checker to load `ida:premise-check` to format the seven-line reason correctly.
- **AC-2.5** Given a verdict recording attempt of `REVISE` or `FAIL` where all `Valid:` entries hold and no ask is marked unanswered, when evaluated by the recorder, then the recorder refuses the verdict with remediation guidance instructing the checker on the schema required by `ida:premise-check`.

### US-3 Checker Revision Requests

As an author whose report is returned for revision, I want the checker's return message to explicitly instruct me to load the `premise-check` skill before rewriting, so that I load the correct schema before drafting the resubmission.

- **AC-3.1** Given a report returned by a checker as `REVISE` due to an absent argument block, when delivered to the author, then the return message states that no argument was supplied and instructs the author to load `ida:premise-check` before resending.
- **AC-3.2** Given a report returned by a checker as `REVISE` due to zero inference lines or substantive inference defects, when delivered to the author, then the return message names the failing line, defect tag, required remedy, and instructs the author to load `ida:premise-check` before drafting the revision.
- **AC-3.3** Given an incoming direction returned by a receiving worker as `REVISE` due to unverified caller method or template prescriptions, when returned to the caller, then the notice instructs the caller to load `ida:premise-check` before reformulating the direction.

### US-4 Proportional Placement

As a framework architect, I want enforcement of load instructions to remain strictly at the instruction and message level within existing surfaces, so that no new mechanical reminder hooks or runtime layers are introduced.

- **AC-4.1** Given the enforcement options hierarchy, when placing the rejection load instruction, then the mechanism is placed exclusively at Level 1 (Instructions in skills) and Level 2 (JIT injection in hook message templates and structural tool refusal text).
- **AC-4.2** Given the framework enforcement map, when registering the control, then the placement aligns with the Evidence Contract entry without introducing new mechanical hooks.

## Design

### Surface 1: The Hearsay Gate Absent-Block Notice

When an incoming message requiring an argument arrives without a fenced `argdown` block, the hearsay gate arms in absent-block mode. The template message loaded by the gate (`hearsay_absent.md`) directs the receiving agent to send the message back for revision and explicitly specifies the instruction to pass to the sender:

```text
Premise-check gate armed by {claim_id}: no argument block supplied; send the message back for revision per the `premise-check` skill (an absent block cannot pass). Instruct the sender to load the skill (`ida:premise-check`) before resending.
{command}
```

The user-facing companion message (`hearsay_absent.user.md`) succinctly records:

```text
Premise-check gate armed by {claim_id} (no argument block supplied; send back for revision with instruction to load ida:premise-check).
```

### Surface 2: Verdict-Recorder Refusals

The verdict recorder (`premise_check_verdict.py` and `report_argument.py`) validates both the report argument and the checker's seven-line reason. When refusing an invalid submission, the recorder emits actionable remediation text to stderr that points directly to loading `ida:premise-check`:

1. **Absent Block on PASS Attempt**:
   When `PASS` is submitted for a peer or task message lacking an argument block, the recorder raises:
   ````text
   PASS refused -- no argument block in judged text: an absent block cannot pass; send the message back for revision
   Defect: The judged text does not contain a fenced ```argdown block.
   Required remediation: Return the message for revision and instruct the sender:
     Load the premise-check skill (`ida:premise-check`) before writing your report; its Argdown dialect is a restricted subset of Argdown, so do not write the block from memory.
     Command: verdict.py --claim <id> --verdict REVISE --reason-file <path>
   ````

2. **Parser Failure on PASS Attempt**:
   When `PASS` is submitted for an unparsable block, the recorder raises:
   ```text
   PASS verdict refused for {claim_id}: could not parse argdown block:
   {parser_output}
   Required remediation: The argdown block failed syntax validation. Return the message for revision and instruct the sender to load `ida:premise-check` before resending, or waive under `Waived: block -- <reason>` if format-only.
   ```

3. **Zero Inference Lines on PASS Attempt**:
   When `PASS` is submitted for a block with zero inference lines, the recorder remediation specifies:
   ```text
   Required remediation format: Bare assertions cannot pass and require at least one inference bar followed by a conclusion. Return for revision and instruct the author to load `ida:premise-check` before rewriting:
     -- <warrant rule>. Unless: <defeater>; <status>. --
     (n) So, <conclusion>
   ```

4. **Missing Keyed Lines in Checker Reason**:
   When a checker reason omits required keys or misformats fields, the recorder remediation specifies:
   ```text
   Required remediation format: Reason must include all 7 keyed lines per `ida:premise-check`. Load the skill (`ida:premise-check`) to inspect the required format before resubmitting.
   ```

5. **Inconsistent REVISE or FAIL Attempt**:
   When `REVISE` or `FAIL` is submitted with all `Valid:` entries holding and no unanswered ask, the remediation format directs the checker to the specification in `ida:premise-check`.

### Surface 3: Checker Revision Requests in Skills

The `premise-check` skill instructions (`SKILL.md`) specify the contract for returning work for revision. Under § "Recording the Verdict", the requirement for `REVISE` mandates including the load instruction in the return payload:

- When returning an absent block (`REVISE "no argument supplied"`), the return message sent to the sender states:
  > No argument block supplied. Load the `premise-check` skill (`ida:premise-check`) before writing your report; its Argdown dialect is a restricted subset of Argdown, so do not write the block from memory.
- When returning for substantive defects or zero inference lines, the return message names the failing line, defect tag (`#missing`, `#scope-drift`, `#conflict`, `#unanswered`, `#undercut`, `#construct-drift`, `#method-gap`), required remedy, and includes:
  > Load the `premise-check` skill (`ida:premise-check`) before writing your revised report.

### Enforcement Architecture and Proportional Placement

Placement of this control adheres to the enforcement pyramid in `specs/enforcement/enforcement.md`:

- **Mechanism Rung:** Stays strictly at Level 1 (`instructions`, `imperative`) in skill documentation and Level 2 (`JIT injection`, `warning` / `structural`, `block`) in message templates and tool stderr refusals.
- **Proportionality Justification:** The burden of proof required to introduce new mechanical reminder hooks is not met. A pattern of agents drafting blocks from unconstrained memory after receiving rejections is resolved by making existing rejection and refusal paths informative and explicit. Adding a separate mechanical reminder hook would impose unnecessary execution friction and violate the principle of least mechanism.
- **Enforcement Map Alignment:**

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Rule: The Evidence Contract](evidence-contract.md) | instructions, JIT injection, structural, process, post-hoc | imperative, warning, block, required gate, observability | `specs/enforcement/evidence-contract.md`, `specs/enforcement/evidence-contract-enforcement.md`, `specs/enforcement/premise-check-rejection-load-instruction.md`, `plugins/ida/skills/premise-check/SKILL.md`, `plugins/ida/hooks/messages/hearsay_absent.md`, `plugins/ida/hooks/premise_check_verdict.py` |
