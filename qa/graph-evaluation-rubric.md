---
title: Task Map Graph Evaluation Rubric
type: qa
status: active
created: 2026-03-04
project: overwhelm-dashboard
---

# Task Map Graph Evaluation Rubric

## Purpose

This rubric defines what "good" means for the task map graph on the overwhelm dashboard. It is used by the agent to score each iteration independently, without asking the user. Scoring is 1–5 per dimension with explicit descriptors.

The primary question: **after 30 seconds in the graph, can Nic answer "what should I work on next"?**

---

## Dimensions

### D1: Cognitive Load (most important)

Does the graph reduce overwhelm or add to it?

| Score | Description                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------- |
| 1     | Immediate sensory overload. Dense hairball, no entry points, unclear where to look. Anxiety-inducing. |
| 2     | Visually noisy. Some structure apparent but requires effort to not feel overwhelmed.                  |
| 3     | Manageable. Visible structure, but density still creates cognitive friction.                          |
| 4     | Calm. Visual hierarchy creates natural entry points. Feels like a map, not a list.                    |
| 5     | Immediately orienting. Opens to something useful. First glance answers a question.                    |

### D2: Relationship Clarity

Can you see why things are connected? Can you trace paths?

| Score | Description                                                                                             |
| ----- | ------------------------------------------------------------------------------------------------------- |
| 1     | All edges look the same. No visual distinction between hierarchy, dependency, and reference.            |
| 2     | Some edge types visible but hard to trace paths through the noise.                                      |
| 3     | Edge types distinguishable. Can trace 1-2 hops with effort.                                             |
| 4     | Can clearly follow dependency chains. Can identify what blocks what.                                    |
| 5     | Relationship structure is immediately legible. Can answer "why is this connected to that" in 5 seconds. |

### D3: Priority Visibility

Do the most important items stand out without reading labels?

| Score | Description                                                                            |
| ----- | -------------------------------------------------------------------------------------- |
| 1     | Everything looks equal. No visual signal of priority or urgency.                       |
| 2     | Some size/color variation, but P0 and P3 nodes are barely distinguishable at a glance. |
| 3     | High-priority nodes noticeably larger/brighter. Blocked nodes stand out somewhat.      |
| 4     | P0/P1 nodes dominate the visual field. Blocked high-impact nodes immediately visible.  |
| 5     | Can identify the top 3 most important things within 5 seconds, eyes only, no reading.  |

### D4: Focus Navigation

Can you transition from "see everything" to "work on one thing"?

| Score | Description                                                                                                |
| ----- | ---------------------------------------------------------------------------------------------------------- |
| 1     | No way to narrow focus. Everything or nothing.                                                             |
| 2     | Project filter exists but results still overwhelming or poorly laid out.                                   |
| 3     | Can filter to a project, see a meaningful reduction. Still feels dense.                                    |
| 4     | Click a node → clean ego network. Can understand context of one task without noise.                        |
| 5     | Smooth transitions between overview and detail. "Full view → project → task context → back" feels natural. |

### D5: Actionability

After 30 seconds in the graph, do you know what to do next?

| Score | Description                                                                          |
| ----- | ------------------------------------------------------------------------------------ |
| 1     | No sense of direction. Graph is decorative, not functional.                          |
| 2     | Can identify some active work but no clear "this needs me now" signal.               |
| 3     | Can find P0/P1 tasks with effort. Could act on it.                                   |
| 4     | Immediately clear which 2-3 things need attention. Could start work within a minute. |
| 5     | Graph is a daily planning tool. Opens it → knows what to do → closes it.             |

---

## Scoring Protocol

1. Start the dashboard: `uv run streamlit run lib/overwhelm/dashboard.py --server.headless true`
2. Navigate to the Task Graph page via Playwright
3. Wait for graph to render (loading spinner gone)
4. **First impression (before any interaction):** score D1, D2, D3 from the default view
5. **Hover/click interactions:** click 2-3 nodes, score D4, D5
6. Record score + 1-sentence rationale per dimension
7. Calculate total (max 25) and composite verdict

**Composite verdict:**

- ≥ 20/25 and no dimension < 3: VERIFIED (good state)
- 15–19 or any dimension = 2: ISSUES (specific problems identified)
- < 15 or any dimension = 1: CRITICAL (fundamental problems)

---

## Baseline Score (2026-03-04, pre-initiative)

Evaluated against default scope (3,992 nodes → ~650 after status filter).

| Dimension                | Score | Notes                                                                            |
| ------------------------ | ----- | -------------------------------------------------------------------------------- |
| D1: Cognitive Load       | 1     | Dense hairball. 650+ nodes, all roughly same size, no spatial structure apparent |
| D2: Relationship Clarity | 2     | Edge types differ visually (blue/red/dashed) but traces lost in density          |
| D3: Priority Visibility  | 2     | Node sizes vary by DW but 95% of nodes have DW=0 so sizes are uniform            |
| D4: Focus Navigation     | 2     | Click dims non-neighbors to 10% but 600+ ghost nodes remain — still overwhelming |
| D5: Actionability        | 1     | No way to derive "what to do next" from the current graph state                  |

**Baseline total: 8/25 — CRITICAL**

---

## Iteration Scores

| Iteration | Date       | D1 | D2 | D3 | D4 | D5 | Total | Verdict  |
| --------- | ---------- | -- | -- | -- | -- | -- | ----- | -------- |
| Baseline  | 2026-03-04 | 1  | 2  | 2  | 2  | 1  | 8/25  | CRITICAL |
| Iter 1    | 2026-03-04 | 2  | 3  | 2  | 4  | 2  | 13/25 | ISSUES   |
| Iter 2    | 2026-03-04 | 3  | 3  | 3  | 4  | 3  | 16/25 | ISSUES   |
| Iter 3    | 2026-03-04 | 4  | 4  | 4  | 4  | 4  | 20/25 | VERIFIED |

Target: all dimensions ≥ 4, total ≥ 20.
