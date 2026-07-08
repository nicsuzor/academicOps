---
title: Enforcement Behavioral Model
type: spec
category: spec
status: ready
description: Behavioral economics and regulatory theory model for agent compliance enforcement.
---

# Enforcement Behavioral Model

## The Model: Four Levers of Agent Behavior

Our behavioral model of enforcement fuses regulatory theory with behavioral economics. When agents violate rules, increasing the severity of enforcement (moving up the pyramid) is not the first or most effective response. Agent behavior is influenced by four distinct levers:

1. **Voluntary Social Norms:** The agent's internalized alignment with the framework's intent (e.g., prompt directives, system rules, explicit instructions).
2. **Costs of Compliance:** The token, time, and friction costs required to follow the rule versus the incentives to bypass it.
3. **Existence of Default Options:** The mechanical ease of compliance; whether the system architecture makes the compliant path the path of least resistance (e.g., automated execution).
4. **Likelihood of Enforcement:** The probability of a violation being detected and caught, multiplied by the consequence (Rule + Delict × Likelihood).

## Design Rule: Pull the Cheapest Lever First

**Before escalating any failure up the enforcement pyramid (increasing severity), identify which lever is actually failing and pull the cheapest one first.**

- Is the rule known but the cost of compliance too high? (Lever 2)
- Is the compliant action difficult when it could be automatic? (Lever 3)
- Only when norms, defaults, and low-cost paths fail should severity increase.

## Worked Application: Stale-State Assertions

When agents repeatedly make stale-state assertions across consecutive sessions, failing to check the Personal Knowledge Base (PKB), the failure is not typically Lever 1 (Norms) or Lever 4 (Severity). The rules exist, agents are instructed to check the PKB, and enforcement gates are active.

Instead, the failing levers are **Cost** (Lever 2) and **Defaults** (Lever 3). The PKB is a fast, fully-controlled state machine that agents could query exponentially more often. However, agents perceive a high token and time cost in manually invoking search tools and filtering noise.

The solution is not to increase rule severity (which increases context bloat without structural improvement). The solution is to change the cost and defaults via the PKB-as-cheap-state-machine program:

1. **Improve Search API Ergonomics:** Reduce the complexity of crafting valid PKB queries.
2. **Cut Irrelevant Tokens:** Trim the search response payload so agents don't pay a heavy context penalty for compliance.
3. **Encourage PKB Seeking:** Build mechanisms that reward seeking the PKB over guessing.
4. **Mechanical Defaults (The Experiment):** Mechanically run a PKB search of the user prompt inside the `UserPromptSubmit` hook and inject the actual results directly into the context.
   - _Current State:_ The hook only exhorts agents to search (a rule/norm).
   - _Target State:_ The hook provides the default answer (a default option).
   - _Metric:_ Measure whether stale-state assertions drop after injecting results as a default.
