---
title: The Bazaar Model Extension
type: spec
status: proposal
tier: architecture
depends_on: [plugin-architecture, workflow-system-spec]
tags: [modularity, agents, qa, architecture, task-graph]
---

# The Bazaar Model Extension

This specification defines the transition from a monolithic, client-injected framework to a modular architecture centered on the **Task Graph** and the **Personal Knowledge Base (PKB)**. We are moving up a layer of abstraction: instead of trying to control _how_ third-party agents execute tasks turn-by-turn, we define strict requirements and verify them before ratification.

## The Paradigm Shift

**Old Model (Injected Behavior)**: The framework used hooks to inject rules and compliance checks into the immediate context of the agent (e.g., Custodiet checking for scope drift every few turns). This is fragile, client-dependent, and creates constant friction.

**New Model (Requirements & Verification)**: The framework embraces the Task Graph as the ultimate coordinator and Quality Assurance guarantee.

1. **Tell them what standards to meet:** The PKB and Task definitions provide the clear, immutable acceptance criteria and strategic context.
2. **Check that they met those standards:** Strict verification gates (Axioms/QA) run asynchronously _before_ a task can be marked "done" and allowed to move on.

## The Five Layers of academicOps

The framework is divided into five operational layers, but the center of gravity is the Brain.

| Layer                               | Component                                  | Core Philosophy                                                                                                                                                                                                                                    |
| :---------------------------------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Brain (Discovery & Planning)** | **Task Graph, PKB**, Memory, Decomposition | **The Coordinator & QA Guarantee.** The PKB determines strategic alignment. The Task Graph dictates what is allowed to proceed. We do not care _how_ execution happens, only that strict requirements are met before a node transitions to 'done'. |
| **2. Engine (Execution)**           | Swarms, Batches, Supervisors               | **The Horsepower.** Executes the tasks defined by the Brain. It is completely decoupled from intent or quality assessment.                                                                                                                         |
| **3. Filter (Verification Gates)**  | Axioms, QA Agent, Custodiet                | **The Ratifiers.** Checked at the boundaries. Axioms evaluate everything (including decomposition) _before_ it is ratified in the graph.                                                                                                           |
| **4. Utilities (Commodity)**        | PDF, Flowchart, Python                     | Swappable AI tools; nothing special about these, could be replaced by any market plugin.                                                                                                                                                           |
| **5. Expertise (Specialized)**      | Analyst (dbt/streamlit), HDR               | Battle-hardened workflows providing specific instructional guidance for complex research tasks.                                                                                                                                                    |

## The Role of the Hydrator: Ephemeral Decomposition

In this new architecture, **Hydration is Decomposition**.

When a user provides a prompt, the Hydrator decomposes that intent into an execution plan. The difference between Hydration and formal Task Decomposition is merely persistence:

- **Task Decomposition** creates durable artifact nodes (Epics/Tasks) in the Task Graph.
- **Hydration** creates an _ephemeral_ workplan for a limited session.

The Hydrator's role is to ensure the ephemeral session plan inherits the strategic alignment and requirements from the PKB, ensuring the agent knows exactly what standards it must meet before the session ends.

## From Mechanical Hooks to Agentic Workflow Steps

We are abandoning mechanical "wiring" (hardcoded python checks in `router.py`) in favor of asynchronous agentic review:

- **Decomposition Review (Start)**: Before a complex task begins, an agent (e.g., Strategist) ensures the proposed plan aligns with the PKB.
- **Final Review (End)**: Before marking a task complete, a specialized agent (Editor, Reproducibility Expert, or QA) verifies the output against the strict acceptance criteria defined in the Task Graph. If it fails, the task does not transition.
