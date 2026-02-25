# Iterative Quality Review for Academic Analysis

## When to Use This

Use this process whenever you are reviewing analytical output — whether produced by a worker agent you delegated to, or by yourself in a previous pass. Academic analysis requires multiple review rounds. Treat every first draft as draft zero.

## Core Principle

Agent-produced academic analysis is consistently strong at mechanics (data loading, chart generation, computation) and consistently weak at judgment (plausibility, audience calibration, theoretical connection, editorial selectivity). The review process targets the judgment gaps systematically.

**Plan for 3-5 review rounds.** Each targets a different quality layer. Do not try to catch everything at once.

---

## The Review Loop

### Round 1: Factual and Structural Integrity

Is the output **correct** at the most basic level?

- **Plausibility**: Do the numbers make sense? If a model shows 100% refusal or 0% error, that is almost certainly a data bug, not a finding. Apply domain knowledge: could this result actually happen?
- **Institutional accuracy**: Are organizations, people, and technical terms named correctly? Agents confidently use wrong names. Check every proper noun.
- **Data completeness**: Are records missing? Demand a mechanistic explanation consistent with the system architecture, not a plausible-sounding guess.
- **Code verification**: Was the code actually run and verified? Require evidence (output logs, test results), not just claims of completion.

**Exit criterion**: Every number verified, every name correct, data pipeline confirmed working, no implausible results.

### Round 2: Analytical Depth and Methodological Rigor

Does the output demonstrate **sound reasoning**?

- **Mechanistic explanations**: Can the agent explain *why* each pattern occurs, not just describe *what* the data shows?
- **Methodological defensibility**: Could each analytical method withstand peer review? If a method conflates two phenomena, cut it.
- **Uncertainty quantification**: Where are the error bars? Classifications need expected error rates. Samples need margins.
- **Evidentiary grounding**: Are claims sourced to appropriate authorities (Freedom House, specific scholars), not general knowledge?
- **Verify surprising results**: Unexpected findings should be verified *before* being reported. If correct, demand additional context: show examples, explain why.

**Exit criterion**: Every finding has a defensible method, mechanistic explanation, quantified uncertainty, and evidentiary grounding.

### Round 3: Audience, Framing, and Editorial Judgment

Does the output **serve its purpose**?

- **Audience calibration**: Internal working document needs detailed methodology but not narrative polish. External paper needs careful framing. Correct the register explicitly -- agents default to generic academic tone.
- **Analytical selectivity**: Not everything that *can* be reported *should* be. If a section is not confident or not interesting, cut it. Removing weak analysis strengthens the whole.
- **Theoretical connection**: Connect findings to the scholarly conversation. This often requires escalation to the human -- flag the gap and ask for direction rather than inventing connections. *[This is typically the human's contribution; the agent's job is to identify where connections are needed and ask.]*
- **Contextual completeness**: Ensure readers have enough context to interpret results (model descriptions, classification criteria). But don't over-explain -- a sentence often suffices where an appendix would be excessive.
- **Qualitative grounding**: Quantitative claims need illustrative examples. Show what compliance and refusal actually look like.

**Exit criterion**: Calibrated for audience, only confident and interesting analysis included, sufficient examples and context for independent reader evaluation.

### When to Escalate to the Human

Some quality dimensions require domain expertise that agents cannot provide:

- Connections to specific scholarly literature and theoretical framing
- Final editorial judgment about what belongs in the output
- Whether analysis is "good enough" for the intended audience
- Verification of results that will be presented to others

Flag these explicitly: *"I've verified the data is correct but this finding about Taiwan refusal rates probably needs theoretical framing -- do you want me to search for relevant literature, or do you have a specific reference in mind?"*

---

## Effective Feedback Patterns

How you correct worker output determines whether the next iteration actually improves.

### Ask Questions That Expose Flaws

Don't state the answer. Ask a question that forces investigation.

> **Weak**: "The missing records aren't from API timeouts."
> **Strong**: "Why would we be missing all predictions for entire records? The batch ran separately from the live API -- how could a per-request timeout cause uniform drops?"

### Reframe Observations as Action Items

When a worker treats a problem as a curiosity, reframe it as a bug.

> **Worker says**: "33 records are missing. Likely API timeouts."
> **Correction**: "That's a bug. File it. Then create a config to backfill."

### Cut Rather Than Iterate on Weak Analysis

When analysis is fundamentally flawed, don't try to fix it -- remove it and replace with something stronger.

> "Drop the severity progression entirely -- the questions aren't linearly ordered. Instead, add a heatmap of refusals by country and model."

### Demonstrate Scholarly Connections

When you want theoretical framing, demonstrate the connection rather than saying "be more analytical":

> "This parallels King, Pan, and Roberts on Chinese censorship -- criticism is tolerated but collective action is suppressed. Frame the flyer vs. satire comparison in that context."

### Give Compound Directives with Priority Ordering

Structure feedback as a prioritized list. Signal what's working alongside what needs fixing:

> "Good, but: (1) check if the Opus flyer refusal rate is correct; (2) if so, show examples; (3) cut the country classification appendix; (4) add model descriptions. Otherwise, looks great."

---

## Quality Gates

### Accept When

- Every number verified or verifiable from the described method
- Analytical methods defensible to a peer reviewer
- Surprising results double-checked and contextualized with examples
- Output calibrated for its specific audience
- Uncertainty quantified where applicable
- Claims cite appropriate authorities
- Weak analysis cut, not hedged
- Reader has enough context to evaluate independently

### Push Back When

- Any result seems implausible given domain knowledge
- Explanations are plausible-sounding but not mechanistically grounded
- The output reads like it was written for a generic audience
- Quantitative findings lack qualitative illustration
- Completion is claimed without evidence of testing
- The analysis includes everything that *could* be said rather than what *should* be said

---

## Delegation Principles

### Trust Workers With (Low Supervision)

- Mechanical coding tasks (data loading, chart generation, notebook editing)
- File organization and formatting
- Running well-defined computations
- Git operations and documentation updates

### Supervise Closely

- Analytical judgment (what's interesting, what to include/exclude)
- Data quality assessment (plausibility checking, bugs vs. findings)
- Methodological choices (which test, which visualization, which construct)
- Audience-facing writing (framing, register, theoretical connections)
- Any interpretation of results
