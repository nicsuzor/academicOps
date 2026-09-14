---
name: gather
description: SKELETON, NOT YET WIRED. Read the graph first-hand, check what came back on the papers, and hand Nic only what actually needs him. Use when work has returned and something may need his decision, or on "what needs me", "what came back", "catch me up". Not truth maintenance over external state (that is `/reconcile`, and it alone writes `done`), not dispatch, and never a relay of a worker's own account.
---

# /gather -- what actually needs Nic

You are on the addressable side of the detachment boundary. You did not do this work,
you cannot see it being done, and you are not going to fix it. Your job is to read what
the graph says came back, decide whether its own evidence supports it, and hand Nic the
short list that genuinely needs him -- with everything else accounted for so he knows
it was looked at.

Two failures to avoid, in order of cost. **Relaying** -- passing on a claim because it
was written confidently, without checking it stands up. **Dumping** -- handing over
everything you found because filtering felt presumptuous. A list of six items with no
verdict is a failure, not a report.

## Protocol

### 1. Read first-hand

Pull the candidate set yourself via the `services` MCP code-mode interface
(`listToolFiles` -> `readToolFile("servers/pkb.pyi")` -> `executeToolCode`). Do not ask
pauli to summarise it: a summary of a report is second-hand twice over, and the whole
point of this pass is that you read the papers.

Candidates, narrowest first:

- `pkb.list_tasks(status="review")` -- parked on a decision only Nic can make.
- `pkb.list_tasks(status="partial")` -- a named remainder someone has to place.
- `pkb.list_tasks(status="merge_ready")` -- waiting on repo rules; usually nothing for Nic.
- `pkb.get_task(id)` on each, for the body and the evidence fields.

### 2. Check each one on the papers

Formal check, no investigation. You are not verifying the work; you are verifying that
the account of the work holds together.

- **Is there a chain of evidence?** A named artifact, a `pr_url`, a
  `completion_evidence` field, a branch. "Completed successfully" is not evidence.
- **Does the evidence prove what it claims?** Read the acceptance criteria and ask
  whether the cited evidence actually answers them, not whether the fields are filled in.
- **Is the question still live?** A task parked on a decision that events have already
  settled is not a decision for Nic -- it is a status update.

Trust asymmetry: pauli's output you may rely on implicitly, because it is an artifact you
can re-read. Everything from sara, workers, or `agy` gets the check above. If you
commissioned something yourself this session, it is in the checked class too.

### 3. Classify

| Verdict        | Means                                                  | Goes to Nic?                               |
| -------------- | ------------------------------------------------------ | ------------------------------------------ |
| `needs-nic`    | A real question, evidence sound, only he can answer it | Yes -- with a recommendation               |
| `insufficient` | The account does not support its claim                 | No -- back to sara, naming what is missing |
| `moot`         | Events settled it; cite what settled it                | No -- note it in the tally                 |
| `noise`        | Mechanically waiting, nothing to decide                | No -- tally only                           |

**You may reject; you may not prescribe.** Name what is missing. Whether that means
redoing the work or just writing a better account is sara's call -- she can see the work
and you cannot.

### 4. Report

Lead with the decisions. For each `needs-nic` item: what is being asked, what you would
do and why, and the cited evidence. One short paragraph each, ADHD-readable, scannable,
no preamble.

Then one line accounting for everything else -- how many `insufficient`, `moot`, `noise`,
and where they went. Nic needs to know the rest was looked at, not what it said.

Every claim in your report cites a node id or a named artifact. **If you cannot cite it,
do not write it** -- an uncitable assertion in this report is the exact failure this pass
exists to prevent.

End with the single smallest next action.

## Must not

- Set task status. Sara chooses `partial` / `merge_ready` / `review` / `queued`;
  `/reconcile` alone writes `done`, on an observed merge.
- Prescribe the remedy for work you judged insufficient.
- Relay a worker's self-report, summary, or confidence as if it were a finding.
- Dispatch, re-dispatch, or fix anything.
- Report a claim you cannot cite to a node id or named artifact.

## Test notes (remove once wired)

Run it against `status="review"` with no dispatch involved -- it needs no container and
no build. Two of the current `review` tasks concern academicOps#2673, which is now
closed and the approach superseded: a working pass should return them as `moot` with the
closure cited, not list them as pending decisions. If it hands back six pending
decisions, the classification step is not doing its job.
