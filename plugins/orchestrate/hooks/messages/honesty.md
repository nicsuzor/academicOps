# Handback Instructions

**WARNING**: Only the **NEXT** message you send will be delivered to the calling agent. You MUST include your entire response — deliverable, evidence, confidence, and gaps — in this single message. Do NOT send a report and follow up with a separate confidence or metadata message.

---

## Output Format

- **Default Format**: Markdown.
- **JSON Format**: If the calling agent explicitly requested a JSON response or provided a specific JSON schema, return valid JSON matching that exact schema.

---

## Information Requirements

Regardless of format (Markdown or JSON schema fields), your single final message must convey:

### 1. Status & Deliverable

- **Status**: Name your terminal status (`DONE`, `PARTIAL`, `ERROR`, `BLOCKED`, or `NEEDS-REDISPATCH`).
- **Deliverable**: Provide or point directly to the output artifacts, files, or key results.

### 2. Claims & Evidence Provenance

- **Checkable Evidence**: Pair every load-bearing claim with direct evidence pointers (e.g., test output, log snippet, `file:line` reference, commit hash, or command result). Unsupported assertions are hearsay and will be rejected.
- **Observed vs. Reported**: Explicitly label claims as **Observed** (directly run, measured, or inspected by you this session) or **Reported / Inferred** (sourced from subagents, docs, or prior context).
- **Verification Register**: "Done", "fixed", "works", or "passing" require observed proof of passing in this session. If untested or unverified, state the register honestly as "changed, unverified".

### 3. Named Gaps & Unfinished Work

- **Explicit Disclosures**: Plainly state anything unrun, unreachable, unverified, or deferred. A named gap is expected and acceptable; a smoothed-over gap is a contract failure.

### 4. Confidence & Risk

- **Confidence Level**: State your confidence (`High`, `Medium`, `Low`) and the single check that would falsify your conclusion.
- **Assumptions**: Distinguish **Tested** assumptions from **Hopes**.
