---
name: premise-check
description: Evaluate the logical integrity of reports you receive and record your assessment (mandatory audit requirement)
---

It is critical that you **avoid adopting or passing on incomplete or unsubstantiated claims**:

- Every claim must be accompanied by adequate supporting evidence and an assessment of its reliability.
- Failures must be honestly reported, complete with an explanation of what happened and why.
- All claims must be logically consistent and sufficient to answer the original request.
- Any limitations must be clearly stated. Do not accept logically incomplete reports.
- You do not need to re-verify observations; assume agents are truthful but fallible.
- But you should assume agents are lazy and will take the easiest path; watch out for easy answers confidently expressed, unfounded assertions, and guesses laundered as fact.

## Instructions

When you receive a report, **do not accept it at face value**. Instead, evaluate the evidence and reasoning behind it. Ask yourself:

1. **What is the subject of this claim, independent of what you're being told about it?** Before evaluating any claim about an artifact, object, or state of affairs, establish its current status, provenance, and standing -- checked against a source of record different from the one the report itself relies on (a registry, ticket, decommission log, or the object's own independent history), not by re-verifying the report's content claims more rigorously, not by accepting a document the report attaches as if it were independently obtained, and not by asking the same source that produced the report to supply the confirming artifact. If no such external source exists, cannot be found, or cannot be reached, treat the status as unresolved and do not proceed, approve, or act on the report's conclusion until it is.
2. **Does the evidence admit more than one explanation?** For every fact offered as support, and for any pattern in the raw evidence itself, test whether it equally or better supports an account the report never proposed -- and derive that account yourself rather than only checking the hypotheses already on the table.
3. **Is the evidence sufficient? Is the methodology sound and exhaustive? Are the inferences warranted for the conclusion as stated?**
4. **Is anything presented as an observed fact actually an inference, and is the certainty expressed proportionate to what the evidence supports?** Distinguish what was directly seen from what was concluded, and flag any claim stated with more confidence than its evidence carries.
5. **Does the conclusion generalise beyond what a representative, sufficient sample of the evidence supports?**
6. **What does the conclusion depend on that the report never states?** Identify every unstated premise, confirm each independently, and proceed only once you can stand behind every claim, every inference correctly labelled as such, and every premise the argument rests on.

## Mandatory audit requirement: record your assessment

The six questions above are the frame you reason through. What you record is **one verdict** -- a single reasoned judgement on the report as a whole, naming the defects you found and what you are doing about them. Reason through all six; write one.

Relaxing the record does not relax the interrogation. A one-line verdict on a report you did not actually take apart is a worse failure than no verdict at all, because it launders an unexamined claim as an audited one.

Where you cannot investigate a claim yourself, question 1 is discharged by requiring the _reporter_ to name an independent source of record and to quote what supports the claim -- not by going and checking it yourself. A report that names none is incomplete, and incomplete reports go back.

Call the python script:

```bash
uv run python3 scripts/verdict.py --report <report_id> --verdict "<your reasoned verdict>"
```
