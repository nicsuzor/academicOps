# Proposal: Clear Division between Workflows and Skills

## The Principle

To improve framework clarity and reduce redundancy, we propose a strict division between **Workflows** and **Skills**.

### Workflows (The "Map")
A workflow defines the **procedural requirements AROUND a task**. It describes the lifecycle, gates, approvals, and handover.

- **Focus**: Process, stages, sequencing, compliance.
- **Content**:
    - **Routing Signals**: When to use this workflow.
    - **Phases**: The high-level stages of the task (e.g., Analysis -> Design -> Implementation -> Validation).
    - **Gates**: Mandatory checkpoints (e.g., "Critic must review before implementation").
    - **Composition**: Which base patterns are included (e.g., `base-task-tracking`, `base-handover`).
- **Analogy**: A flight plan. It tells you where you are going, what checkpoints you must pass, and what rules you must follow.

### Skills (The "Toolkit")
A skill provides the **instructions for DOING the task**. It contains the actual work content, expertise, and tool usage.

- **Focus**: Execution, "how-to", expertise, quality rubrics.
- **Content**:
    - **Step-by-step instructions**: Detailed "how-to" for specific actions.
    - **Qualitative Rubrics**: How to judge the quality of the work (e.g., Qualitative Assessment rubrics).
    - **Specialized Tools**: Instructions for using specific scripts or MCP tools.
    - **Examples & Anti-patterns**: "Do this, not that."
    - **Subagent Prompts**: Specific prompts for specialized sub-tasks.
- **Analogy**: The pilot's manual and flight controls. It tells you how to actually fly the plane and use the instruments.

---

## Identification of Misclassifications

Current issues identified in the review of `aops-core/workflows/` and `aops-core/skills/`:

### 1. Bloated Workflows (Expertise misfiled as Process)
Workflows currently contain deep "how-to" expertise that should be modularized into skills:

- **`qa.md`**: Contains 150+ lines of detailed qualitative assessment rubrics, persona immersion techniques, and specific evaluation scenarios. This is expert judgment ("doing") and should live in the `qa` skill.
- **`email-triage.md`**: Defines semantic classification rules (FYI, Task, Skip) and priority inference logic. These are instructions for doing the triage, not just the process around it.
- **`decompose.md`**: Contains "Uncertainty Patterns", "Sequential Discovery Patterns", and "Knowledge Flow" logic. These are strategic planning techniques ("doing").
- **`external-batch-submission.md`**: Contains technical steps for documenting commands and verifying configurations.

### 2. Workflows as Skills (Misfiles)
Several files in the `workflows/` directory are actually skills/commands:

- **`strategy.md`**: Labeled as a command/skill in its own content. It contains facilitation techniques and questioning frameworks. It has no lifecycle stages or gates—it's a tool for thinking.
- **`audit.md`**: Effectively a wrapper for the `audit` skill. It duplicates the 11 phases of audit execution found in `skills/audit/SKILL.md`.
- **`reflect.md`**: A procedural guide for reflection that should be part of the `handover` or `governance` skill.

### 3. Inconsistent Lifecycle Placement
- **The "Full Task Lifecycle"**: Currently defined inside `skills/framework/SKILL.md`. This is the most important workflow in the framework, but it's buried in a skill rather than being a top-level workflow.
- **Bases vs. Workflows**: Some "Bases" (like `base-handover.md`) contain more procedural logic than the workflows that use them.

### 4. Overlap and Redundancy
- **`email-capture.md` vs `email-triage.md` vs `email-reply.md`**: Significant overlap in logic and intent. These should be consolidated into a single `operations/email` workflow that delegates to specific skills.
- **`feature-dev.md` vs `tdd-cycle` (in WORKFLOWS.md)**: Overlapping development flows.

---

## Proposed Structural Changes

### 1. Thinning the Workflows
Workflows will be refactored to remove "how-to" content, delegating instead to the appropriate skill.

| Workflow | Content to Move to Skill | Target Skill |
| :--- | :--- | :--- |
| `qa.md` | Qualitative Assessment Rubrics, System Design, Integration Validation | `skills/qa/` |
| `audit.md` | 11 Phases of audit execution | `skills/audit/` |
| `email-triage.md` | Classification logic (FYI/Task/Skip) | `skills/email-triage/` |
| `decompose.md` | Uncertainty patterns, knowledge flow, spike patterns | `skills/planning/` |
| `strategy.md` | Facilitation techniques, questioning framework | `skills/strategy/` |

### 2. Consolidating into Core Workflows
To simplify routing and reduce cognitive load, we propose consolidating the current set of 18 non-base workflows (excluding the 10 base workflows) into **5 Core Workflows**. These workflows act as high-level procedural containers that delegate specific "doing" logic to thick, specialized skills.

| Workflow | Scope | Composes Skills | Replaces |
| :--- | :--- | :--- | :--- |
| **`task-lifecycle`** | The default master workflow for all tracked work. | `framework`, `handover`, `tasks` | *New (consolidates fragmented lifecycle logic)* |
| **`discovery`** | For uncertain goals and strategic planning. | `planning`, `strategy`, `analyst` | `decompose`, `strategy`, `collaborate` |
| **`development`** | For technical implementation, debugging, and fixing. | `python-dev`, `design`, `tdd` | `feature-dev`, `debugging`, `tdd-cycle` |
| **`verification`** | For quality assurance, peer review, and criticism. | `qa`, `critic`, `peer-review` | `qa`, `critic`, `peer-review`, `constraint-check` |
| **`operations`** | For repetitive administrative and batch tasks. | `email`, `batch`, `admin` | `email-capture`, `email-triage`, `email-reply`, `batch-processing`, `reference-letter` |

*Note: `simple-question` remains as a lightweight routing fast-track for pure information requests.*

### 3. Thickening the Skills
Skills will become the primary repository of expertise and execution detail. They will be structured with:
- `SKILL.md`: High-level "what", "how", and triggers.
- `references/`: Detailed rubrics, technical standards (e.g., `python-dev` standards), and expert manuals (e.g., `qa` qualitative rubrics).
- `instructions/`: Specific step-by-step guides and subagent prompt templates.

---

## Implementation Plan

1. **Step 1: Relocation**: Move misfiled skills (e.g., `strategy.md`) from `workflows/` to `skills/`.
2. **Step 2: Modularization**: Extract detailed rubrics and "how-to" logic from workflows (e.g., `qa.md`) into specialized skill reference files.
3. **Step 3: Refactoring**: Rewrite workflows as thin procedural guides using the 5 core workflow structure.
4. **Step 4: Routing & Reference Migration**: Update existing routing logic in `WORKFLOWS.md` (and any other routing configuration) to map old workflow entries to the 5 core workflows, and systematically update all code and documentation references to use the new workflow names (adding temporary aliases/redirects from old to new names where needed).
5. **Step 5: Update Indices**: Regenerate `WORKFLOWS.md` and `SKILLS.md` to reflect the new architecture and verified routing.

---

## Conclusion
By adopting this division, the framework becomes more modular and robust. Workflows stay high-level and focused on compliance and process integrity ("The Map"), while skills capture the rich, evolving expertise of the system ("The Toolkit"). This separation ensures that agents follow rigorous processes while having access to the specialized knowledge required to execute them effectively.
