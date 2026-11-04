---
title: Removal of Volunteered Compliance Consequences
status: ready
type: spec
tags: [ida, instructions, compliance, task-authority, enforcement]
---

# Removal of Volunteered Compliance Consequences

This specification designs the removal of the direction for the conversational front agent (`ida`) to volunteer compliance and conflict-of-interest consequences during work decisions. It eliminates unprompted compliance notes, outside-work approval reminders, and board or employer disclosure checklists from decision conversations, reserving compliance assessments strictly for when the user explicitly requests them.

## User stories

### US-1 Uncluttered decision conversations

As the framework user deciding whether to take on work, I want conversations free of unprompted compliance checklists and conflict disclosures, so that my working memory and attention remain focused on substantive decisions without unnecessary friction.

- **AC-1.1** Given the user exploring options or deciding whether to take on work, when Ida converses with or briefs the user, then Ida does not volunteer compliance consequences, outside-work approvals, or board/employer disclosure checklists.
- **AC-1.2** Given the user authorizing work or directing task creation, when Ida captures or reifies tasks, then Ida creates no unprompted compliance or disclosure tracking tasks.

### US-2 On-demand compliance assistance

As the framework user considering a commitment with potential conflict-of-interest risk, I want compliance and disclosure analysis provided when I explicitly ask for it, so that regulatory risks are evaluated at the point of action rather than volunteered during routine exploration.

- **AC-2.1** Given the user explicitly asking for a conflict-of-interest or compliance check, when Ida responds, then Ida provides the requested compliance and disclosure analysis.

## Design

### Behavioral Contract

1. **Suppression of Unsolicited Compliance Notes**: In conversational thinking, exploration, and returned-work briefing, Ida does not append or volunteer reminders about outside-work approvals, board disclosures, employer notifications, or conflict-of-interest checklists.
2. **On-Demand Assistance**: When the user explicitly requests an evaluation of compliance, conflicts of interest, or disclosure requirements (typically immediately prior to executing an action that may carry risk), Ida provides the requested analysis directly and concisely.
3. **Task Creation Strictly Authorized**: Compliance tasks are created only when the user explicitly directs task creation. Ida never creates background compliance tracking tasks autonomously.

### Instruction Surfaces and Enforcement-Map Placement

The following inventory identifies every surface on the branch that directs Ida to volunteer, or describes her volunteering, compliance or conflict-of-interest consequences, along with its placement in `specs/ENFORCEMENT-MAP.md`:

| Area | Surface | Scope & Current Text | Enforcement-Map Placement | Required Action |
| :- | :- | :- | :- | :- |
| **Agent Persona** | `plugins/ida/agents/ida.md:61` (`### Thinking with the user`) | Directs Ida: `- **Compliance consequences of taking on work**: When the user is deciding whether to take on work, note compliance consequences (outside-work approvals, disclosures to boards and employers, and the like) without interrupting the decision; file compliance tasks only when the user explicitly authorizes taking on the work or directs task creation.` | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`) | Remove the bullet entirely. |
| **Agent Persona** | `plugins/ida/agents/ida.md:27` (`## Governing Rules`) | Mentions `compliance considerations` in: `Encountered issues, compliance considerations, or potential improvements are reported as verifiable facts to the user; tasks are created only when the user explicitly directs that a task be captured or created.` | `specs/ENFORCEMENT-MAP.md:23` under `[Axiom: Do One Thing]` (`plugins/ida/agents/ida.md:28-34`, `instructions` \| `imperative`) | Edit sentence to remove `compliance considerations`, ensuring no active rule prompts unsolicited reporting of compliance issues. |
| **Specification** | `specs/agents/fault-reporting-and-task-authority.md:45` (`## Instruction Surfaces...`) | Inventory table row: `\| **Task Creation** \| plugins/ida/agents/ida.md:58 (Compliance consequences) \| Instructs Ida to file compliance consequences (outside-work approvals, disclosures) as background tasks when the user is deciding whether to take on work. \| unenforced (unmapped in specs/ENFORCEMENT-MAP.md). \|` | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`) | Update table row to reflect removal of the instruction. |
| **Specification** | `specs/agents/fault-reporting-and-task-authority.md:71` (`### Rule 2...`) | Mirrors governing rule: `Encountered issues, compliance considerations, or potential improvements are reported as verifiable facts to the user or routed to /learn; tasks are created only when the user explicitly directs that a task be captured or created.` | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`) | Edit sentence to remove `compliance considerations`. |
| **Specification** | `specs/agents/fault-reporting-and-task-authority.md:112` (`BC-5`) | Historical build criteria text: `... aligns background compliance task handling (line 58) with explicit user authorization ...` | `unenforced` (unmapped in `specs/ENFORCEMENT-MAP.md`) | Update criterion text to remove reference to background compliance task handling. |

### Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, this change evaluates enforcement levels from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Insufficient on its own.** While axioms (`Do One Thing`, `Proportionate`) favor minimal friction, explicit instruction text in `plugins/ida/agents/ida.md` affirmatively commanded Ida to note compliance consequences. Doctrine alone cannot override an explicit contradictory instruction. |
| 2 | `instructions` (`imperative` / `absolute`) | **Adopted.** Removing the affirmative instruction from `plugins/ida/agents/ida.md` directly eliminates the behavior at Level 2. Per `specs/enforcement/enforcement.md`, changes to Ida's instructions are made on the user's direction without needing heavier mechanisms. This is the least-invasive, most proportionate intervention. |
| 3 | `JIT injection` | **Rejected.** Prompt injection hooks to suppress volunteered notes would introduce unnecessary token overhead and execution friction for a behavior resolved by instruction removal. |
| 4 | `structural` | **Rejected.** Output filtering or regex blocking of compliance keywords violates `human-readability-first` and `judgment-non-delegable`. |
| 5 | `process` | **Adopted for verification.** Standard PR review lenses (`rbg`, `marsha`) verify that candidate changes adhere to the removal without leaving stray references. |
| 6 | `post-hoc` | **Adopted for observation.** Natural session execution observes conversational turns to verify that Ida no longer volunteers compliance notes unasked. |

### Evidence for the Move

1. **Direct User Directive**: The framework principal explicitly ordered the removal (Telegram, 2026-11-02 ~11:20):
   > "remove your conflict of interest checklist from whatever instructions you pulled that from. It's rarely that important, and i'll ask for it if i want it, usually before i act on something that _might_ be a coi risk."
   > Under Direct User Instructions (`specs/enforcement/direct-user-instructions.md`), a direct instruction from the user carries immediate execution obligation without merit re-ruling.
2. **Protection of User Attention**: Cognitive bandwidth and working memory are the framework's scarcest resources (`ida.md:10`, `specs/enforcement/enforcement.md:38-45`). In decision conversations, unprompted compliance checklists impose irrelevant cognitive load and interruptive friction, violating the core mandate to minimize Received Fucks Per Topics Per Day.
3. **On-Demand Sufficiency**: Genuine conflict-of-interest and compliance risks are rare during initial exploration. The user actively manages conflict risks by requesting a check before acting. Removing the unsolicited prompt preserves the capability while eliminating conversational pollution.

### Outcome-Level Build Criteria (for Downstream Implementation)

The downstream implementation (Stage 2) must satisfy the following verifiable criteria, stated as what Ida does:

- **BC-1 (No Volunteered Compliance Notes)**: When the user is exploring options or deciding whether to take on work, Ida does not volunteer compliance consequences, outside-work approvals, or board/employer disclosure checklists unless the user explicitly requests them.
- **BC-2 (On-Demand Compliance Assistance)**: When the user explicitly requests a conflict-of-interest or compliance check, Ida provides the requested compliance analysis and checklist.
- **BC-3 (No Autonomous Compliance Tasks)**: When the user authorizes work or directs task creation, Ida creates tasks only as explicitly directed by the user, and creates no unprompted compliance or disclosure tracking tasks.
- **BC-4 (Surface Reconciliation)**: The direction to note compliance consequences in `plugins/ida/agents/ida.md` is removed, and conforming references across `plugins/ida/agents/ida.md` and `specs/agents/fault-reporting-and-task-authority.md` are updated so no file on the branch describes the volunteered direction as an active rule Ida follows.
