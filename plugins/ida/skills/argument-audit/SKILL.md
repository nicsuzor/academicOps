---
name: argument-audit
description: Formally audit and stress-test a scholarly, legal, policy, or qualitative argument using Chained Toulmin Argdown -- identifying logical gaps, hidden assumptions, overclaiming (scope and construct drift), methodological mismatches, and under-explored rival explanations at a controlled granularity floor. Use for "audit this argument", "check if this argument holds up", "find the gaps in this chapter/thesis", "evaluate argument strength", or "what assumptions are missing". Not for reconstruction alone (use argument-extraction), for a readable map page with open issues (use argument-map), or for agent handback reports (use premise-check).
---

# Argument Audit

Evaluate whether a scholarly, qualitative, mixed-methods, or policy argument is formally made out by stress-testing its **Chained Toulmin** structure against five diagnostic checks: **Term & Scope Alignment**, **Method-to-Construct Validity**, **Warrant & Backing Fit**, **The Contrast Test (Rival Explanations)**, and **Macro-Remedy Coherence**.

## When to Use

- Auditing a thesis chapter, journal draft, research design, or existing `.argdown` map for logical gaps and overclaiming
- Testing how research questions, methods, empirical evidence, and theoretical lenses lock together hierarchically
- Surfacing hidden assumptions (`#missing`) and under-explored alternative explanations (`_> #unanswered`) without demanding formal mathematical proof
- Deciding whether a weak step requires **new evidence**, **a bridging citation**, or **narrowing the claim's qualifier**

## Procedure

### 1. Set the Audit Scope and Granularity Floor

Before auditing, lock the abstraction level so the evaluation stays targeted and does not recurse infinitely:

- **`macro` (Whole Thesis / Book Architecture)**: Audit how part-level and chapter-level conclusions pull up into `[Core Thesis]`, and whether policy/reform chapters match diagnostic chapters. Floor: treat chapter-level empirical findings as given unless internally contradictory.
- **`meso` (Chapter / Paper Audit - Default)**: Audit how section claims, methods, primary evidence, and theoretical warrants combine to establish the chapter/paper thesis. Floor: accept peer-reviewed citations (`basis: "theory"`) and raw descriptive statistics (`basis: "observed"`) as leaf nodes unless their scope mismatches the warrant.
- **`micro` (Hinge Inference / Research Design Audit)**: Deep-dive into 1 to 3 load-bearing inferences (for example, RQ -> Method -> Empirical Finding -> Causal Claim). Floor: raw observations and verbatim quotes.

### 2. Reconstruct or Normalise into Chained Toulmin

If the input is prose or a flat tree (such as `+` bullet hierarchies that mix methods, data, and theory as sibling nodes), first normalise the target claims into **Chained Toulmin** blocks:

- Put only **observations, sample bounds, or prior sub-conclusions** in numbered premises `(1)`, `(2)` (max 2 to 3 per inference bar).
- Put the **theoretical principle, methodological rule, or causal mechanism** in the inference bar: `-- Warrant: <rule> {uses: [1, 2], basis: "...", pointer: "..."} --`.
- Separate epistemic layers into stacked inference bars inside the block:
  1. **Observational Step**: Raw Data + Method/Sample Bound -> _Empirical Pattern_
  2. **Explanatory Step**: Empirical Pattern + Theoretical Mechanism Warrant -> _Causal / Interpretive Diagnosis_
  3. **Normative / Policy Step**: Diagnosis + Normative Standard Warrant -> _Evaluative / Reform Claim_

### 3. Run the 5-Point Formal Sufficiency Audit

Apply these five formal checks to every load-bearing inference bar above your granularity floor:

#### Check A: Term and Scope Alignment (Overclaiming & Middle-Term Drift)

Compare the exact nouns, populations, and quantifiers in `(1)-(2)` against the conclusion `(3)`:

- **Quantifier inflation**: Do the premises show `"some"`, a single percentage, or `"can"`, while the conclusion claims `"most"`, `"systematically"`, or `"excludes"`?
- **Concept / Middle-term shift**: Do the premises measure a **proxy** (a price, an absence from a catalogue, a count) while the conclusion claims a **substantive construct** (exclusion, lost value, harm) without a bridge that links the proxy to the construct?
- **Action**: Insert the missing bridge as a numbered premise tagged `#missing #scope-drift` with `{basis: "assumed", reason: "..."}` (tags before metadata), or flag the conclusion for qualifier narrowing.

#### Check B: Method-to-Construct Validity (Observational Equivalence)

When an argument moves from a `method-bounded` empirical finding to a substantive claim, verify that the instrument can logically observe the claimed phenomenon:

- **Circular categorisation**: Are analytical tiers or categories defined independently of the outcome variable before testing?
- **Equilibrium confounding**: Does the method observe a joint outcome of two or more actors while the conclusion attributes it to one actor's mechanism?
- **Action**: Attach an undercut node, with the relation on its own line:
  ```argdown
  [Method Limit: <name>]: <Why the instrument cannot isolate the claimed mechanism>. #method-gap
    _> <Target Argument>
  ```

#### Check C: Warrant and Backing Fit

Inspect the `-- Warrant --` line and its cited `basis: "theory"` backing:

- Does the cited literature actually establish the rule used in the `-- Warrant --`, or was it developed for a different domain, population, or sector?
- **Action**: If the domain differs, attach an undercut node `[Backing Domain Mismatch: <name>]: <the difference>. #missing` with `_> <Target Argument>` on its own line below it.

#### Check D: The Contrast Test (Under-Explored Rival Explanations)

For every causal or interpretive warrant, ask: **"What is the nearest plausible alternative explanation or world state in which the cited evidence `(1)-(2)` would look weak or identical?"**

- Classic rival families: _a change in demand vs. a change in cost_, _substitution vs. exclusion_, _a gap in the instrument vs. a real absence_.
- If the argument does not exclude or bound that rival explanation, add an explicit undercut node:
  ```argdown
  [Rival Explanation: <name>]: <State the rival mechanism that produces the same data (1)-(2)>. #unanswered {basis: "assumed", reason: "Unexcluded by current evidence"}
    _> <Target Argument>
  ```
- Then specify the **Rebuttal-Defeater**: what specific sub-analysis, control variable, or qualitative check would defeat `- [Rival Explanation]`.

#### Check E: Macro-Coherence and Diagnosis-to-Remedy Fit

At the chapter or thesis level, compare the **diagnosed bottleneck** against the **proposed conclusion or policy reform**:

- If Chapter A diagnoses the bottleneck as _actor X refusing to buy_, does Chapter B's reform target _actor Y refusing to sell_?
- **Action**: Flag cross-branch contradictions with `><` (`#conflict`).

### 4. Emit the Audited Argdown and Actionable Triage Table

Deliver two outputs:

1. **Annotated Chained Toulmin Argdown**: Containing the reconstructed argument with `#missing`, `#scope-drift`, `#method-gap`, `#unanswered`, and `#conflict` nodes placed at the exact inference bars where they occur.
2. **Triage & Remediation Table**: For every identified gap, recommend the lowest-friction scholarly fix across three options:
   - **Option 1 - Re-scope / Qualify (Zero new data)**: Narrow the claim or qualifier so it matches what the existing method and data already prove.
   - **Option 2 - Bridge via Theory / Literature (Citation fix)**: Supply the unstated warrant or behavioural bridge from existing scholarship.
   - **Option 3 - Empirical / Methodological Check (Data fix)**: Run a specific cross-tab, hold a confounder constant, or audit a subsample to defeat an `_> #unanswered` rival explanation.
