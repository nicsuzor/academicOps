---
title: Decision Queue Boundaries and Conversational Pacing
status: ready
---

# Decision Queue Boundaries and Conversational Pacing

The decision walk-through workflow (`/decide`) presents discrete, pre-filtered operational choices to the user one at a time. This specification defines the boundaries between interactive operational decision triage, informational decision queries, and open-ended design exploration. It ensures that decision cards are drawn exclusively from ready-to-decide items queued for the user, that queries about decisions return scannable lists rather than launching interactive steppers, that complex design and methodology questions remain in collaborative conversational thinking, and that interactive walk-throughs pace themselves to the user rather than forcing rapid-fire progression.

## User stories

### US-1 Bounded Decision Source

As the user, I want the decision walk-through to present only discrete, pre-filtered operational decisions that are queued specifically for me in today's daily briefing, so that I am never forced to make binary choices on unsifted backlog items, general work streams, or arbitrary task breakdowns.

- **AC-1.1** Given the invocation of `/decide` without arguments, when the agent gathers candidate decisions, then candidate items are drawn strictly from the dedicated queue of items awaiting the user in today's daily briefing.
- **AC-1.2** Given tasks in general backlog sections or active work streams, when `/decide` runs, then those tasks are excluded from the walk-through queue.
- **AC-1.3** Given an empty or missing queue in today's daily briefing, when `/decide` runs, then the agent informs the user that no decisions are currently waiting and stops without scanning other backlog sections.

### US-2 Informational Queries Answered as Lists

As the user, I want inquiries asking about pending decisions to be answered with a concise, scannable summary list rather than launching an interactive card stepper, so that I can inspect what is waiting without being trapped in an interactive decision flow.

- **AC-2.1** Given a command or prompt carrying a question or topical filter (such as `/decide what decisions are waiting on research?`), when processed by the agent, then the agent returns a concise, structured markdown list of matching open decisions and stops.
- **AC-2.2** Given a query answered as a list, when the reply is emitted, then the agent does not present interactive button cards, prompt for immediate single-card choices, or enter a step-through sequence unless explicitly directed to walk through them.

### US-3 Preservation of Substantive Design Exploration

As a researcher and system architect, I want complex design choices, research plan reviews, and methodology evaluations to be explored conversationally with arguments in full view, so that I am never steamrolled into quick button choices with vital context hidden behind details.

- **AC-3.1** Given an open task concerning research design, methodology, or architecture review, when the user discusses or reviews the task with the agent, then the agent conducts the discussion in open conversational thinking with all reasoning, trade-offs, and empirical context visible in the main exchange.
- **AC-3.2** Given a multi-faceted design review or plan approval, when interacting with the user, then the agent never decomposes the review into sequential multiple-choice button cards or conceals methodology behind interactive choice buttons.

### US-4 Respectful Conversational Pacing

As the user, I want the agent to pause the decision walk-through whenever I ask a question, express uncertainty, or shift topics, so that I have the cognitive space and information needed to decide without feeling rushed.

- **AC-4.1** Given an active decision card presentation, when the user provides a direct, unambiguous decision choice, then the agent records the decision on the item and presents the subsequent card.
- **AC-4.2** Given an active decision card presentation, when the user asks a clarification question, expresses uncertainty, or raises an objection, then the agent pauses the stepper immediately, addresses the user's inquiry conversationally, and waits for direction before presenting subsequent cards.
- **AC-4.3** Given background subagents recording prior decisions, when a subagent completes, then the agent never repeats or re-prompts an already-pending card unless specifically asked.

## Design

### 1. Empirical Grounding and Incident Analysis

This specification addresses a failure class observed during interactive session execution:

1. **Invocation**: In session `99137d` (telemetry turn span `1937132`, at timestamp 2026-11-04 05:22:08 UTC), the user submitted the message:
   ```text
   /decide ok, research stuff. what were the decisions waiting for me on the research tasks?
   ```
   The prompt was an informational question asking what decisions were waiting across research tasks. Because the message was prefixed with the slash command `/decide`, the platform delivered it as a command event, triggering the decision walk-through skill.

2. **Permissive Instruction Text**:
   - `plugins/ida/skills/decide/SKILL.md`: The frontmatter description (`Use for "decide", "go through my decisions", morning triage, or when open items in the daily note need interactive resolution`) lacked boundary constraints against questions or queries carrying arguments. Furthermore, while Section 1 directed reading the dedicated escalation section, it lacked an explicit prohibition against pulling tasks from general work sections or slicing complex plans into decision cards. In Section 3, the instruction `Immediately output the next card (Decision N+1 of M) with no intermediate chatter` forced a rigid, rapid-fire sequence on every turn.
   - `plugins/ida/agents/ida.md`: Under `Briefing on returned work`, the rule `One decision or question per message` was misapplied outside its briefing context: the agent took a multi-faceted research plan review, carved it into four sequential button-choice cards, posted card 1 via interactive buttons (tool span `c860a8efcdb4f1d0`), and hid the substantive methodology and trade-offs behind expandable details.

3. **Subsequent Telemetry Traces**:
   - Spans `1965561` (turn `ef8090417a39b708`, 08:00:05 UTC) and `1968843` (turn `db6b6c47156f2eed`, 08:01:35 UTC): When the user responded to card 1 on the console, the agent immediately thrust card 2 at the user, and repeated the prompt as soon as the background recording subagent completed.
   - Span `1974869` (turn `6451cfde905d1b91`, 08:09:37 UTC): The user objected to the pace and cognitive deficit:
     > "you're moving too fast for me. i feel like i don't have enough information here to make a choice. what is the workflow that you're following to push through these questions?"
   - Span `1979435` (turn `0caf004eabfa915e`, 08:20:17 UTC): The user inquired about the source:
     > "wait, ARE these questions all queued on the daily note for immediate answer?"
   - Span `1979810` (turn `e426d99154595d1d`, 08:20:40 UTC): The user challenged the improper tool usage:
     > "so what the fuck do you think you were doing using /ida:decide for a completely inappropriate purpose?"

### 2. Proposed Instruction Changes and Target Observations

In accordance with the enforcement pyramid, these behavioural constraints are established at Level 1 (Instructions), which provides the least-invasive intervention fitting the failure class:

#### 2.1 File: `plugins/ida/skills/decide/SKILL.md`

- **Proposed Text Changes**:
  1. _Frontmatter Description_: Update to state the discrete operational scope affirmatively and explicitly exclude informational queries, design discussions, and research methodology:
     ```yaml
     description: Present discrete pending decisions drawn from today's daily note one at a time with recommendations, pointers, and reply options, and record each answer on the item. Use for "decide", "go through my decisions", morning triage, or when discrete open items in the daily note need interactive resolution. Exclude for design discussions, research methodology, task planning, or questions about decisions (use conversational discussion or list summary), routine status reports (use daily note), plain graph truth maintenance (use reconcile), or worker dispatch (use dispatch).
     ```
  2. _Section 1 (Source and Query Routing)_: Clarify the source restriction and establish the list-summary routing for queries:
     ```markdown
     Read strictly the `## With you` section. Never pull from `## Your work`, backlogs, or arbitrary open tasks. Never slice complex plans, research designs, or multi-step tasks into decision cards.

     - **Informational queries are not walk-throughs**: When invoked with a query or filter (e.g. `/decide what decisions are waiting on research?`), answer with a concise list of matching decisions and stop; do not launch the interactive card stepper unless explicitly asked to walk through them.
     - Each entry under `## With you` represents a discrete operational choice that has reached the user under the one-level escalation rule.
     - If the section is empty or missing, report that no decisions are waiting and stop.
     ```
  3. _Section 2 & 3 (Pacing and Conversational Flexibility)_: Replace rigid advancement directives with conversational flexibility:
     ```markdown
     ## 2. Present One Card at a Time

     Hold the ordered list in memory and present exactly one card per turn.

     - **Header**: `Decision N of M: <Short Title>`
     - **Content**: Enough information to decide, proportionate evidence with pointers, the reasoned recommendation, and structured answer options.
     - **Prompt**: Ask for a response (on conversational channels) or present via choice tool (`ask_question` in console) where supported.
     - **Prohibition**: Never output multiple cards in one message or summarize the remaining queue in advance. Never force complex research reviews or open-ended design problems into multiple-choice cards.

     ## 3. Turn-by-Turn Record and Advance

     On each answer from the user:

     1. **Record on the item**: Immediately write the user's decision to the item's record.
     2. **Advance or Converse**: If the user's answer is a clear decision on the card, advance to the next card (`Decision N+1 of M`). If the user asks a question, raises uncertainty, or shifts context, pause the card stepper immediately and address their substance conversationally. Never force the user into rapid-fire progression without allowing conversational pauses.
     3. **Wrap-up**: After the final card (`Decision M of M`), provide a concise one-line receipt summarizing the recorded decisions and updated tasks.
     ```
- **Target Observation Demonstrating Success**:
  Given an inbound prompt `/decide what decisions are waiting on research?`, the agent emits a concise, structured markdown list identifying waiting research decisions and terminates the turn without presenting an interactive card or calling interactive choice tools. When `/decide` is invoked bare, only items from `## With you` are presented, and any mid-stream clarifying question from the user pauses card presentation.

#### 2.2 File: `plugins/ida/agents/ida.md`

- **Proposed Text Changes**:
  In `plugins/ida/agents/ida.md`, under `Conversations with the User -> Thinking with the user`:
  ```markdown
  - **Never reduce design discussions to button choices**: Treat architectural choices, research methodology, and plan reviews as collaborative thinking time. Never slice a multi-faceted design review, research plan, or task decomposition into sequential multiple-choice cards or push button triage on substantive problems. Substantive design exploration requires conversational engagement with the whole argument visible, not quick choices with reasoning tucked behind details.
  ```
- **Target Observation Demonstrating Success**:
  When the user directs attention to a complex research plan or architectural review, the agent engages in reflective prose outlining the core trade-offs, methodological stakes, and options in full view within the conversational thread, refusing to convert the review into sequential multiple-choice button prompts.

### 3. Behavioural Contracts and Invariants

1. **Source Boundary Invariant**: The interactive decision stepper consumes solely pre-filtered, discrete decision items located in the escalation section (`## With you`) of today's daily briefing. Items in general work sections (`## Your work`), open task backlogs, and plan reviews are ineligible for card stepper consumption.
2. **Query vs. Walk-through Contract**: Slash commands and prompts containing question arguments or search filters are informational queries. They return scannable text lists. Only bare walk-through requests or explicit step directives launch the single-card presentation loop.
3. **Conversational Primacy Invariant**: The conversational loop always takes precedence over the card stepper. Any user turn that does not supply a direct answer to the active card pauses the stepper and is handled as conversational thinking.
4. **Non-Reduction of Intellectual Work**: Complex design reviews, research methodology evaluations, and multi-stage task plans are explored conversationally. Agents are prohibited from cutting complex intellectual work into rapid-fire button cards.

### 4. Rejected Choices

- **Mechanical Rate-Limiting or Fixed Delay Timers**: Rejected because cognitive pacing depends on semantic comprehension of user intent and interaction context, which deterministic timers cannot evaluate.
- **Hardcoded Command Argument Interceptors**: Rejected because natural-language understanding easily distinguishes an informational query from a walk-through request without brittle regex parsing.

## Open questions

None. The boundaries, routing criteria, and instruction changes are fully resolved.
