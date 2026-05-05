# AcademicOps Observability Strategy

This document outlines strategies for evaluating the efficiency and return on investment (ROI) of safeguards within the AcademicOps framework.

## 1. Guardrail ROI (Cost vs. Efficacy)

**Concept:** Evaluate the token cost of specific context injection points and gates (`PreToolUse`, `enforcer`, `custodiet`) against the session `outcome` (success/partial/failure) stored in insights logs.

**Metric:** `Tokens per Success`. If a safeguard (e.g., a heavy `context_map` injection) consistently inflates the input tokens but the task still results in a "partial" or "failure" outcome, it has a low ROI.

## 2. Human Attention Cost Proxy (Intervention Rate & Review Burden)

**Concept:** Since human attention is the limiting factor, we must measure how much human attention a task demands.

- **Interactive Sessions:** Measure the _Intervention Rate_. By parsing interactive transcripts, we can count the number of user turns vs. assistant turns. A high ratio indicates the agent needed constant steering.
- **Async PRs (GitHub):** Map `task_id` to PR metadata. We can calculate `Review Burden` = `(Number of PR review comments + Number of commit iterations after open) / Lines of Code changed`.

**Actionable Insight:** Tasks with high token usage but a high Review Burden are severely underperforming.

## 3. Friction Point & Friction Tool Heatmap

**Concept:** Extract `friction_points` and `root_cause` from transcript reflections.

**Implementation Idea:** Aggregate all `friction_points` across session insights and cluster them. Cross-reference this with `usage_stats.by_tool` to pinpoint which tool defaults or outputs are causing the most confusion (e.g., if `grep` consistently triggers a friction point, we can optimize its output format).

## 4. The "Epic" Aggregation (Task Cohort Analysis)

**Concept:** Group tasks by epic/PR instead of looking at them individually.

**Metric:** Visualize the "Token-to-Merged-Line Ratio" by summing the total tokens across all session logs in the epic and comparing it against the final PR size. This identifies epics with massive thrashing.
