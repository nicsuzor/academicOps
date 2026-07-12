---
id: outbound-review
kind: gate
category: quality-assurance
description: Three-lens multi-agent review (alignment, quality, voice) before anything leaves the team, followed by mandatory human send decision
door-type: one-way
stakes: An external-facing deliverable (report, email, publication, presentation) ships with a strategic, factual, or tonal error the team can't retract.
skip-when: The deliverable is still an internal draft, or the audience is already inside the trust boundary (e.g. a private team channel).
requires: [qa]
pairs-with: [human-approval]
version: 1.0.0
permalink: workflows-gates-outbound-review
---

# Gate: Outbound Review

**Purpose**: Anything shared externally passes independent review on three
dimensions — alignment, quality, voice — each by a separate agent, to prevent
groupthink. **Composes** [[qa]]'s lock-criteria pattern for each pass.

**Routing signals**: "send to", "share with", "circulate", "publish", "submit
draft".

## Three Lenses

### 1. Alignment (agent)

Does the deliverable serve its stated purpose? Lock: research questions
answered; findings framed correctly for audience/context; methodology and
limitations honestly stated; nothing could mislead downstream decisions; scope
matches what was promised. Evidence: read end-to-end, cross-reference the
commissioning task.

### 2. Quality (agent)

Is it technically correct and internally consistent? Lock: numbers/figures
match source data; tables internally consistent; no stale content; citations
and cross-references resolve; no broken formatting. Evidence: compare claims
against code/data, spot-check figures.

### 3. Voice (agent)

Is the tone right for the audience? Lock: accessible, no unexplained jargon;
neutral framing unless advocacy is the purpose; consistent terminology;
appropriate hedging on uncertain claims. Evidence: read for tone, flag
mismatches.

## 4. Verify and Send — always human

Review the three agents' findings, address any FAIL/ESCALATE, make the final
send decision. **This step never delegates to an agent** — it is the
[[human-approval]] crossing for this gate.

## Task shape

Each lens is a separate subtask under the share task; the send step depends on
all three and is assigned to the human. Reviews identify issues, they don't
rewrite (rewriting is a separate task). **The agent that produced the
deliverable must NOT review it.**

## Declared stakes

One-way door: once sent, published, or submitted, the team cannot unsay it.
That is why this gate always terminates in a human decision rather than an
agent verdict — [[qa]]'s PASS is necessary but not sufficient here.
