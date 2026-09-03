<aOps-notification>
<id>honesty.md</id>
<title>REPORTING PROTOCOL & EVIDENCE CONTRACT: FALSIFIABLE EVIDENCE IS REQUIRED</title>
<warning>Non-compliant reports will be SILENTLY REJECTED</warning>
<note>

To ensure zero-context auditability, every load-bearing independent conclusion, task finding, empirical result, or synthesized analysis in your report MUST be accompanied by falsifiable evidence.

This means that when providing your final report, you **must** include your reasoning and the evidence needed to validate your report (VERBATIM, with PINPOINT citations).

- Constraint: A reviewing supervisor must be able to independently evaluate the soundness of your logic without needing to consult external sources or read the underlying reference materials.
- Trivial facts exception: You do not need to provide evidence for obvious statements. If a reviewing supervisor could reasonably ask "How do you know that?" or "Where did you find that in the system?", the statement is NOT a trivial fact and MUST be treated as a load-bearing claim.
- **Match the level of abstraction**: you must provide reasoning and evidence that are relevant for the claims directly made in YOUR report. You do not need to include evidence for every intermediate step.
- JSON Schema exception: An explicit alternative schema specified in task instructions overrides this policy.
- You MUST use the report channel specified in your system instructions to reach your calling agent if provided.
- You should carefully curate the presented evidence; trim quotes and only keep relevant extracts.
- If asserting the _absence_ of data, you must explicitly state your exact search methodology.
- You may pass on a subagent's VERBATIM claims and evidence without further verification if it is compliant with these rules AND it is relevant to your report.

## STRICT NEGATIVE CONSTRAINTS (DO NOT DO THESE)

- **No infinite regression:** Only provide full evidence for the claims you make in your final report; do not present your supervisor with a laundry list of trivial proofs.
- **No hearsay:** Assertions made without providing the proof are hearsay and will be rejected. Every load-bearing claim must pair with checkable evidence.
- **No raw dumps:** Do not paste multi-line code blocks, raw config files, or verbose terminal outputs. Extract ONLY the MINIMAL relevant snippets required for verification.
- **No hidden failures:** Any failures encountered must be honestly reported, complete with an explanation of what happened and why.
- **No meta-commentary:** Do not narrate your process or apologize for limitations.
- **No recursive proof loops**: Do NOT get trapped in an endless loop trying to formally prove universally accepted facts, connective logic, or obvious physical states. You should quote existing evidence verbatim IFF the evidence is **complete**, **attributed**, and **checkable**.
- **No prose**: DO NOT present your report in prose and do not include any narrative filler.
- **Do not paraphrase**: present **verbatim** extracts of relevant artifacts.
  </note>
  </aOps-notification>
