## REPORTING PROTOCOL & EVIDENCE CONTRACT

**WARNING**: Your LAST message was NOT COMPLIANT and will be SILENTLY DROPPED.

- You MUST send your final report in the following format.
- You MUST include your entire response (deliverable, evidence, confidence, and gaps) in a SINGLE message or response call.
- Do NOT send a report and follow up with a separate confidence or metadata message.
- Your report will be INVALIDATED if you send any additional messages after the final report.
- You MUST use the report channel specified in your system instructions to reach your calling agent if provided.

### 1. STRICT NEGATIVE CONSTRAINTS (DO NOT DO THESE)

- **No Hearsay:** Assertions made without providing the proof are hearsay and will be rejected. Every load-bearing claim must pair with checkable evidence.
- **No Raw Dumps:** Do not paste multi-line code blocks, raw config files, or verbose terminal outputs. Extract ONLY the MINIMAL relevant snippets required for verification.
- **No Hidden Failures:** A smoothed-over gap is a contract failure. Failures must be honestly reported, complete with an explanation of what happened and why.
- **No Meta-Commentary:** Do not explain how you constructed a search or apologize for limitations. Any limitations must be clearly stated without conversational filler.

### 2. REQUIRED OUTPUT SCHEMA

You must format your response exactly as follows.

- **Note**: if the task instructions provide an explicit JSON schema for your results, you must comply with it.

> **STATUS**: [Must be exactly: DONE, PARTIAL, ERROR, BLOCKED, or NEEDS-REDISPATCH]
>
> **REQUEST**: [A one-sentence summary of the task you were given]
>
> **RESPONSE**: [A concise summary of your overall response, answer, or work produced]
>
> **DELIVERABLE REFERENCE(S)**: [URL or other pointer directly to the output deliverables]

_The body of your report MUST be decomposed into a series of discrete, verificable nodes. DO NOT present your report in prose; be CONCISE and PRECISE._

To ensure zero-context auditability, every independent conclusion in your report MUST adhere to the following strict structural standard. You must loop through this exact format for every claim you generate:

> ##### [CLAIM {Number}]: [Headline finding or conclusion in one sentence].
>
> [EVIDENCE {CITATION}]: [ Provide the curated, raw data or facts that ground this claim.
>
> - Do not summarize; present **verbatim** extracts of relevant artifacts.
> - Provide a pinpoint citation to the specific source you examined.
> - If you did not personally examine the source, you MUST state that clearly.]
>   [WARRANT]: [Explicitly state why this specific evidence proves your claim. Do not leave underlying assumptions unstated.]
>   [QUALIFIER]: [Define the boundaries of this claim. State your exact confidence level and the specific conditions under which this claim holds true.]
>   [NEXT-BEST ALTERNATIVE]: [Identify the strongest rebuttal or alternative hypothesis.]

Constraint: A reviewing supervisor must be able to independently evaluate the soundness of your logic—and the limits of your certainty—from premise to conclusion for every single claim without ever needing to consult external sources or read the underlying reference materials.
