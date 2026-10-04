---
title: Unit of Analysis Reference
type: reference
category: ref
permalink: analyst-ref-unit-of-analysis
description: Choose the unit of analysis for repeated or crossed measurements, specify random effects so variance is not pre-aggregated away, and detect decompositions that have lost their variance.
---

# Unit of Analysis

Repeated measurements are not independent observations, and their aggregates are not data. Collapsing repeated measurements to a mean, mode, or proportion before fitting is a modelling decision: it asserts that within-unit uncertainty does not matter and that no interaction exists beyond the main effects in the model. Neither assertion appears in the output, and either can move a headline result by an order of magnitude.

## When the trap arises

Apply this reference whenever the same unit is measured more than once:

- Repeated runs, predictions, or ratings of the same item (e.g. several LLM runs per record).
- Crossed designs: every record scored by every model under every criterion.
- Variance decomposition, ICC, or "% of variance explained by factor X" claims.
- Any step that reduces runs to one row per item or combination (`GROUP BY` then fit, modal label, mean score, agreement proportion).

## Default specification

Fit on individual observations and handle clustering with random-effects structure. For a crossed repeated-measures design:

1. **One row per observation** (each run, prediction, or rating), not per aggregate.
2. **A random intercept for each crossed factor** (e.g. record, model, criteria).
3. **A random intercept for the full combination grouping** (e.g. record × model × criteria), so interaction variance has somewhere to live instead of being absorbed by a main effect.
4. **The link-function residual reported alongside the estimated components** (π²/3 for logit; 1 for probit). Without it, a "% of total" partition is meaningless.

Treating every prediction as independent (ordinary regression or a plain χ² over pooled runs) is not an alternative default; it understates standard errors for every clustered factor.

## Warning signs

Any one of these is enough to re-fit before reporting:

- One main effect accounts for 90% or more of the reported variance.
- The partition changes substantially when the unit of analysis changes.
- No residual or combination variance appears in the decomposition.
- Percentages sum to exactly 100% with no link residual.

Before reporting any decomposition, ask: would the main effects change if a random intercept for the full combination grouping were added? If yes, report the fuller specification.

## Worked case

A variance decomposition fitted on per-combination **modal** outcomes, with crossed random intercepts for record, model, and criteria only, reported record = 97% of between-factor variance. Re-fitted on individual runs with a random intercept for the record × model × criteria combination, the partition became record ≈ 33%, combination ≈ 51%, model ≈ 0.1%, criteria ≈ 0.1%, Bernoulli residual ≈ 16%. Interactions dominate, not record identity. The 97% was an artefact: modal aggregation discarded within-combination uncertainty, and with no combination intercept the interaction variance had nowhere to go but the record main effect.
