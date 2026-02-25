# Output Quality Checklist for Academic Analysis

## When to Use This

Run this checklist **before reporting analytical output as complete** — whether you are a worker agent reporting to an orchestrator, or the main agent about to present results to the human. Your output will be reviewed. Catching these issues yourself saves a review round.

## Expect Review

Your first-pass output is draft zero. It will go through 3-5 rounds of review before it is acceptable. This is normal for academic work. Do not aim for perfection on the first pass — aim for **correctness and honesty** so the review rounds can focus on depth and framing rather than fixing errors.

---

## Pre-Submission Self-Check

Before reporting output as complete, verify each of these:

### Correctness

- [ ] **Every number is verified.** Did you actually run the code and confirm the output, or did you write it and assume it works? Show evidence.
- [ ] **No implausible results.** Are there any 0% or 100% values? Any result that seems too clean or too extreme? These are almost always data bugs, not findings. Investigate before reporting.
- [ ] **Names and terms are correct.** Check every proper noun — organizations, people, technical terms. Do not rely on memory; verify against source documents.
- [ ] **Data is complete.** Are all expected records present? If records are missing, can you explain the mechanism (not guess)?

### Honesty About Uncertainty

- [ ] **Distinguish findings from hypotheses.** If you are guessing why a pattern exists, say "hypothesis" not "likely." Do not present guesses as conclusions.
- [ ] **Quantify uncertainty.** Classification methods have error rates. Samples have margins. Report them.
- [ ] **Flag surprising results.** If something is unexpected, say so and recommend verification rather than quietly reporting it as a finding.

### Completeness of Reporting

- [ ] **Methods are described.** Someone reading your output should understand how you arrived at each result.
- [ ] **Sources are cited.** Classifications should reference their authority (e.g., Freedom House). Claims should cite evidence, not rely on general knowledge.
- [ ] **Examples accompany quantitative claims.** Show what the data actually looks like, not just summary statistics.

---

## Anti-Patterns to Avoid

These are the most common ways analytical output fails review. Avoiding them proactively saves everyone time.

### 1. False Confidence

Do not present guesses as conclusions. "Likely API timeouts" sounds authoritative but may be wrong. If you haven't traced the mechanism, say "I haven't investigated the cause yet" rather than offering a plausible-sounding explanation.

### 2. Data Bugs Reported as Findings

If a model shows 100% refusal or 0% compliance, your first hypothesis should be a parser error, missing data, or format incompatibility — not an actual behavioral finding. Investigate data quality before interpreting results.

### 3. Not Testing Your Own Code

If you wrote a download cell, did the download actually produce a non-empty file? If you wrote a parser, does it handle all input formats? Run your code and verify the output before reporting success.

### 4. Producing Complete Output Without Checkpoints

Do not write a 400-line report, commit it, and convert it to Word in a single pass. Write a section, show it, get feedback. The first version will need restructuring — doing formatting and conversion work before review wastes effort.

### 5. Adding Unrequested Deliverables

Do not proactively convert to Word, add executive summaries, or create appendices that weren't asked for. Deliver what was requested. Additional outputs can be discussed after the core work is accepted.

### 6. Over-Exploring Before Acting

If you've been asked to update notebooks 03 and 04, you do not need to read every file in the project first. Match your exploration scope to the task scope.

### 7. Exhaustive Over Selective

Not every analysis that can be run should be included. Ask yourself: is this finding interesting? Does it advance the argument? If you are including something because you computed it rather than because it matters, cut it.
