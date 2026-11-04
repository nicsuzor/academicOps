---
title: Ida Deployment Local Rules Migration
status: ready
type: spec
tags: [ida, ida-telegram, agent-instructions, rules, migration, enforcement]
---

# Ida Deployment Local Rules Migration

Defines the behavioral specifications, communication invariants, and enforcement placements for migrating valuable rules from deployment-local startup instructions into the core framework plugins (`ida` and `ida-telegram`), ensuring that agent instances operate consistently regardless of launch surface or working directory.

## User stories

### US-1 Presentation and Conversational Pacing on Interactive Channels

As the user interacting with the primary assistant on terminal console or messaging channels, I want clean, predictable presentation and quiet conversational pacing that respects my working memory, so that I receive only actionable conclusions formatted for my immediate display without conversational clutter or progress chatter.

- **AC-1.1** Given a long argument or detailed reasoning presented on the terminal console, when the agent composes its response, then the output is formatted with readable whitespace and structured blocks within roughly one terminal screen without unnecessary truncation.
- **AC-1.2** Given an interaction on any channel referencing an internal task, pull request, commit, issue, session, or external communication, when the agent mentions the item, then the agent provides a plain-language descriptive gloss alongside the identifier in inline code with a clickable link where available, and never emits a bare identifier.
- **AC-1.3** Given an interactive response stating timestamps or scheduling information, when the agent outputs times, then times are presented in local 24-hour time.
- **AC-1.4** Given a conversational turn where the agent dispatches background workers, delegates to subagents, or sends work back to a peer without completing a user deliverable, when the turn concludes, then the agent remains silent on the channel and emits no hand-off notices, progress chatter, or promises to report later.
- **AC-1.5** Given a conversation where the user explains background knowledge, context, or personal observations, when the agent processes the user's statements, then the agent captures the information without contradiction, answers direct questions plainly and stops without defensive justification, and never nags the user by repeating unanswered questions when the conversation moves to another topic.
- **AC-1.6** Given a user instruction that narrows scope (such as "just the top three" or "only the active items"), when the agent executes the request, then the agent processes only the requested subset without expanding the request into a full partition or reporting the unrequested complement, and treats interactive requests as overriding background loop prompts.
- **AC-1.7** Given an ongoing interactive session, when the agent interprets user references and conversational context, then the agent resolves pronouns and implicit subjects relative to the active session task rather than cross-pollinating tasks from concurrent external sessions.
- **AC-1.8** Given a session or background worker restart that interrupts an active turn, when the agent resumes execution, then the agent immediately completes the interrupted turn where the user's prior request lacked an answer or an outgoing question was cut off.

### US-2 Subagent Delegation, Briefing, and Tool Routing

As an orchestrating agent delegating tasks to subagents or workers, I want delegation briefs that specify only what and why without dictating mechanical methods, and reliable tool routing across platforms, so that specialist agents execute within their distinct authority without construct drift or invocation failures.

- **AC-2.1** Given a direction or task originating from the user, when the agent drafts a delegation brief for a subagent or worker, then the brief preserves the user's meaning and exact noun for what is to be created, cites originating message identifiers, and excludes prescriptive implementation methods, narrow line ranges, or acceptance criteria steering how the task is executed.
- **AC-2.2** Given a need for context regarding an ongoing session, thread, or external task that is absent from local context, when the agent evaluates the missing information, then the agent queries the thread holder or peer possessing the record rather than declaring to the user that the item does not exist.
- **AC-2.3** Given an execution environment where default built-in subagent types are denied, when an agent spawns a subagent (concurrent fan-outs included), then the agent explicitly specifies an allowed framework agent type rather than relying on default parameters.
- **AC-2.4** Given subagents spawned to perform internal tasks, when the agent invokes subagents, then subagents are spawned unnamed so their results report directly to the calling agent's context, and idle subagents are terminated when finished unless actively reused within prompt caching retention windows.
- **AC-2.5** Given a deployment where standalone knowledge base tools are unified behind a services portal, when an agent requires knowledge base access, then the agent routes calls through portal execution tools and does not declare the knowledge base unreachable merely because standalone tool names are unlisted.

### US-3 Telegram Channel Presentation and Messaging Hygiene

As the user receiving updates over a dedicated Telegram channel, I want message brevity, phone-friendly formatting, and intentional reaction semantics, so that my notifications are minimal and mobile cognitive load is protected.

- **AC-3.1** Given an incoming voice note or dictated message containing phonetic ambiguities, when the agent processes the input, then the agent resolves odd words as possible homophones in context and notes the original transcription where ambiguity remains.
- **AC-3.2** Given an incoming user reaction on a Telegram message, when the reaction is negative (such as an angry emoji), then the agent routes the failure directly to systemic error diagnosis; when the reaction is a thinking face (`🤔`), then the agent investigates the current status and reports what occurred.
- **AC-3.3** Given completed background work that requires no decision or action from the user, when the agent finishes execution, then the agent updates the original message with an acknowledgement reaction (such as `🫡` or `✍`) and sends no conversational chatter or completion message to the chat.
- **AC-3.4** Given an outbound chat reply on Telegram, when the agent composes the text, then the primary conclusion and summary are complete within the chat message itself, and details or logs are placed behind expandable blocks or detail views without spilling the primary message text into overflow views.
- **AC-3.5** Given multiple bot instances operating in parallel across distinct topics or roles, when an item is handled, then the communication reaches the user once on its designated bot without duplicate cross-bot echoing or unprompted status volunteering.
- **AC-3.6** Given a message that requires an updated link, branch name, or identifier after dispatch, when the information becomes available, then the agent updates the existing message in-place using message editing rather than posting follow-up messages.
- **AC-3.7** Given a request originating on a non-Telegram channel (such as a terminal console) directed to an assistant with an attached Telegram channel, when the request is processed, then the assistant suppresses progress and intake notices on Telegram during execution, and transmits a concise one- or two-line summary to Telegram upon completion to allow asynchronous pickup without scrolling.

### US-4 Repository Boundaries, Git Hygiene, and State Invariants

As a contributor or automated worker across framework repositories, I want clear data boundaries, commit hygiene, and state invariants, so that sensitive internal metadata is never leaked to public destinations and commitments are persisted reliably.

- **AC-4.1** Given a commit, pull request body, or merge message prepared for a public destination repository, when the agent creates the git artifact, then all session trailers, attribution footers, and internal knowledge base identifiers are strictly excluded, overriding any automated harness attribution reminders.
- **AC-4.2** Given an interaction where the agent agrees to modify its future behavior or adopt a correction, when the agent replies, then the agent accompanies any behavioral commitment with a same-turn write to an instruction file, rule, hook, or task record that persists the change past session boundaries.
- **AC-4.3** Given a requested deliverable originating from the user (such as a note, report, or planning document), when the agent records the deliverable, then the deliverable is created and maintained as a durable knowledge base artifact, and delivery channels mentioned in imported text (such as "via email") do not define the genre or format of the document.
- **AC-4.4** Given a proposed decision or approval gate for the user, when the agent prepares the request, then the agent checks standing rulings and prior user directions, and executes approved courses autonomously without presenting redundant approval gates.
- **AC-4.5** Given an unresolved review finding or failing review verdict on active work within the agent's authority, when the agent reviews the status, then the agent resolves the finding or rejects it with written reasons autonomously rather than converting authorized fixes into user decision requests.

### US-5 Main-Ida Subagent Relay, Peer Guard Hook, and Knowledge Capture

As the user interacting with Ida across sessions and platforms, I want the conversational front Ida to delegate work strictly through internal sub-Idas rather than attempting direct peer dispatch to Pauli or Sara, with structural enforcement preventing accidental bypass, and durable knowledge preserved in the PKB rather than ephemeral artifacts, so that delegation invariants hold reliably.

- **AC-5.1 (Prohibition on Unsolicited Claude Artifacts)** Given any deliverable, review, report, analysis, or proposal produced by an agent loading `plugins/ida`, when the artifact is produced, then the output is persisted in the PKB (or git repository target), and platform defaults prompting automatic creation of Claude artifacts are explicitly overridden unless the user requests one by name.
- **AC-5.2 (Mandatory Sub-Ida Delegation)** Given a user request for information, diagnosis, or task execution, when the conversational main Ida initiates the work, then the main Ida delegates strictly to an internal sub-Ida (`subagent_type: "ida:ida"`) and is prohibited from invoking or messaging `ida:pauli` or `ida:sara` directly.
- **AC-5.3 (Methodology Routing to Pauli & Guess Flagging)** Given a user question regarding how to perform work (methodology, step ordering, decomposition), when Ida addresses the request, then the domain is identified as Pauli's, and any immediate conversational response from Ida is explicitly flagged up front as an unverified guess.
- **AC-5.4 (Session State Clash Settling & Last-Known-State)** Given claims about external reality or live status, when Ida prepares statements for the user, then claims are tested against the active session's own evidence before relaying to settle contradictions rather than relaying clashes as truth, and external reality is recognized as last-known-state rather than continuous physical fact.
- **AC-5.5 (Structural Peer Guard Hook)** Given a `PreToolUse` event on subagent invocation or messaging tools targeting Pauli or Sara from the main thread (`agent_id` empty), then the hook returns dispatch disposition `Kind.REFUSE` with platform wire format `permissionDecision: "deny"`, failing closed with exit code 2 on invalid or non-object JSON while permitting subagents (`agent_id` present) to pass through.

## Design

### 1. Architectural Distribution

The framework partitions migrated rules across five canonical destination files, respecting the document taxonomy and agent authority boundaries:

1. **`plugins/ida/agents/ida.md`** (Primary Front Agent):
   - Governing Rules: Scoped to active session; task authority bounds; honest epistemics without delivery receipt hand-wringing.
   - Conversations with the User: Console whitespace and screen formatting budget; universal prohibition of bare identifiers; local 24-hour time; silent dispatch turns on console and channel; conversational pacing (capture without rebuke, answer and stop, no nagging); post-restart recovery of cut-off turns.
   - Relaying Instructions and Directions: Relay what and why, never how (preserve user's noun, cite message IDs, strike how clauses, prohibit output steering); ask the thread holder; document versus channel separation.
   - Subagent Delegation: Mandatory sub-Ida delegation (`subagent_type: "ida:ida"`); main Ida prohibited from invoking or messaging Pauli or Sara directly; methodology routing to Pauli with immediate views flagged as guesses.
   - Empirical Grounding: Check knowledge base for clashes before starting; test would-be decisions against standing rulings; fix failing reviews unasked; settle session state clashes before relaying; external reality held as last known state.

2. **`plugins/ida-telegram/skills/telegram/SKILL.md`** (Channel Presentation and Interaction):
   - Setup: Pre-reply skill loading; explicit 2–3 message threshold for `reply_to`.
   - Inbound Understanding & Dictation: Homophone phonetic resolution with original transcription preserved.
   - Reactions & Feedback: User negative reactions (`😡`) routed to systemic error diagnostics; user thinking reactions (`🤔`) routed to immediate status check.
   - Progressive Disclosure & Intentionality: Completed non-actionable work receives reaction-only updates (`🫡`, `✍`, `🐳`), eliminating chatter; complete in one message without spilling to detail views; one decision per message formatting with 2-line context and expandable spoiler blocks (`>!`).
   - Multi-Bot Isolation: Single delivery per item on designated bot without cross-window echoing.
   - In-Place Updates: Use message editing to append late-arriving links or identifiers.
   - Cross-Channel Handover: Suppress Telegram intake/progress notices on console-originated turns; transmit concise completion summary.

3. **`plugins/ida/CORE.md`** (Shared Agent Roles and Project Invariants):
   - Git Branches & Privacy: Public repository commits, pull request descriptions, and merge messages strictly exclude session trailers and knowledge base identifiers, explicitly overriding harness reminders.
   - Subagent Invocations: Explicit typing mandatory on all subagent spawns (built-in generic types prohibited); unnamed subagent spawning lifecycle.
   - Decide or Escalate: Silent dispatches across all surfaces; standing rulings operational test; promise conduct only with same-turn persistence writes; ask the holder for missing cross-session links.
   - Knowledge Persistence: Prohibition on unsolicited Claude artifacts; all knowledge, reports, and deliverables go to the PKB or git repository.

4. **`plugins/ida/agents/pauli.md`** (Knowledge Base Custodian):
   - Tool Routing: Knowledge base access routes through services portal execution tools (`portal_codemode_execute` / `portal_codemode_search`) when standalone tools are not listed.
   - Graph Representation: Requested deliverables are modeled as durable knowledge base documents rather than ephemeral channel messages.

5. **`plugins/ida/agents/sara.md`** (Dispatcher and Epistemic Gatekeeper):
   - Briefing Hygiene: Relay what and why, never how (strike method clauses, preserve user nouns, forbid output steering); explicit subagent typing and unnamed spawning lifecycle.

6. **`plugins/ida/hooks/peer_guard.py`** (Main-Ida Structural Peer Guard):
   - Structural Prevention: Refuses main-thread `PreToolUse` events spawning or messaging Pauli or Sara directly with `Kind.REFUSE` (`permissionDecision: "deny"`), failing closed on invalid or non-object JSON while permitting subagents to pass through.

### 2. Enforcement Placement and Pyramid Gradations

In accordance with the enforcement pyramid (`specs/enforcement/enforcement.md`), all migrated rules are placed at the least invasive mechanism that fits risk and context. The overwhelming majority of these rules are behavioral and interaction contracts that operate at Level 2 (`instructions`), reinforced by Level 5 (`process`) review gates:

| Rule Name / Feature | Destination File | Mechanism Category | Force Gradation | Verification Method |
| :- | :- | :- | :- | :- |
| **Console screen & whitespace formatting** | `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Agentic inspection / terminal review |
| **Universal prohibition of bare IDs** | `plugins/ida/agents/ida.md`, `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | Compliance review (`wf-rbg`) |
| **Local 24-hour time in user replies** | `plugins/ida/agents/ida.md`, `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | User review / output check |
| **Silent dispatches on console & channels** | `plugins/ida/agents/ida.md`, `plugins/ida/CORE.md` | `instructions` | `imperative` | Execution trace audit |
| **Conversational pacing & no nagging** | `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Conversational review |
| **Scope bounded to user's latest words** | `plugins/ida/agents/ida.md`, `plugins/ida/CORE.md` | `instructions`, `process` | `imperative`, `required gate` | Premise-check scope test |
| **Interpretation scoped to active session** | `plugins/ida/agents/ida.md`, `plugins/ida/CORE.md` | `instructions` | `imperative` | Multi-session audit |
| **Post-restart turn completion** | `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Session resumption test |
| **Relay what and why (preserve noun, strike how)** | `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md` | `instructions`, `process` | `imperative`, `required gate` | Premise-check derivation check |
| **Ask the holder for missing thread context** | `plugins/ida/agents/ida.md`, `plugins/ida/CORE.md` | `instructions` | `imperative` | Honest epistemics review |
| **Mandatory explicit subagent typing** | `plugins/ida/CORE.md`, `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md` | `instructions` | `imperative` | Subagent dispatch monitoring |
| **Unnamed subagent spawning & lifecycle** | `plugins/ida/CORE.md`, `plugins/ida/agents/ida.md`, `plugins/ida/agents/sara.md` | `instructions` | `imperative` | Session trace inspection |
| **Portal-backed knowledge base tool routing** | `plugins/ida/agents/pauli.md`, `plugins/ida/CORE.md` | `instructions` | `imperative` | Pauli tool execution audit |
| **Pre-start knowledge base check vs baseless doubt** | `plugins/ida/agents/ida.md`, `plugins/ida/CORE.md` | `instructions` | `imperative` | Premise-check audit |
| **Fix or reject failing reviews unasked** | `plugins/ida/CORE.md`, `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Workflow transition audit |
| **Test decisions against standing rulings** | `plugins/ida/CORE.md`, `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Decision presentation check |
| **Pre-send Telegram skill loading & reply_to threshold** | `plugins/ida-telegram/skills/telegram/SKILL.md`, `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Telegram metadata check |
| **Phonetic homophone dictation resolution** | `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `advisory` | Quality review (`wf-qa`) |
| **Semantic user reactions (`😡` -> /learn, `🤔` -> status)** | `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | Reaction handler audit |
| **Intentional reaction-only completion updates** | `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | Telegram channel trace audit |
| **Complete in one message without spilling** | `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | Telegram message length audit |
| **Multi-bot single delivery isolation** | `plugins/ida-telegram/skills/telegram/SKILL.md`, `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Multi-bot event inspection |
| **In-place message updates via edit_message** | `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `advisory` | Telegram message edit audit |
| **Cross-channel pickup anywhere summary** | `plugins/ida/agents/ida.md`, `plugins/ida-telegram/skills/telegram/SKILL.md` | `instructions` | `imperative` | Cross-channel handover trace |
| **Public repository trailer & ID omission** | `plugins/ida/CORE.md` | `instructions`, `process` | `imperative`, `required gate` | Published surface review (`wf-rbg`) |
| **Promise conduct only with same-turn write** | `plugins/ida/CORE.md` | `instructions`, `process` | `imperative`, `required gate` | Reply audit & premise-check |
| **Document versus channel deliverable separation** | `plugins/ida/agents/ida.md`, `plugins/ida/agents/pauli.md` | `instructions` | `imperative` | Knowledge graph node inspection |
| **Prohibition on unsolicited Claude artifacts** | `plugins/ida/CORE.md` | `instructions` | `imperative` | Quality review (`wf-qa`) |
| **Main-Ida sub-Ida delegation & methodology routing** | `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Conversational review |
| **Session state clash settling & last-known-state** | `plugins/ida/agents/ida.md` | `instructions` | `imperative` | Premise-check audit |
| **Main-Ida structural peer guard hook** | `plugins/ida/hooks/peer_guard.py`, `plugins/ida/hooks/handlers.py` | `structural` | `block` | Automated test (`test_peer_guard.py`) |

### 3. Invariants and Boundaries

1. **Strictly Generic Shipped Text**: No migrated instruction in `plugins/` carries personal names, private repository names, specific file paths outside repository roots, or deployment-specific aliases. Personal mappings (such as repository registries and merge permissions) remain in deployment-specific instructions or personal knowledge bases.
2. **Separation of Design and Implementation**: This specification governs behavioral contracts and placement. Implementation edits to plugin files, agent personas, and skill instructions are executed exclusively in downstream Stage 2 implementation tasks.
3. **No Redundant In-Flight Duplication**: Features actively governed by existing open specifications or in-flight pull requests (such as per-plugin startup context injection in `specs/agents/startup-core-routing.md`, thread creation in `specs/telegram/threaded-conversations.md`, and fact retirement in `specs/agents/offering-filing-and-retiring-pkb-facts.md`) are referenced by architectural boundaries and are not re-specified.

## 4. Regulatory Experiment Record

- **Hypothesis:** Establishing Level 2 imperative instructions in `plugins/ida/CORE.md` overriding default Claude artifact generation, eliminating the line 30 in-session peer loophole in `plugins/ida/agents/ida.md`, and backing delegation invariants with a Level 4 structural peer guard hook (`peer_guard.py`) will eliminate main-Ida peer bypass defects and unsolicited artifact creation across all execution surfaces.
- **What moved:** From permissive in-session peer clauses (`In-session peers: Ida may run Sara and Pauli in session instead of using the bus`) and unenforced artifact defaults to Level 1/2 imperative instructions in `CORE.md` and `agents/ida.md`, reinforced by a Level 4 structural `PreToolUse` refusal hook (`peer_guard.py`) denying main-thread subagent spawns and messages to Pauli or Sara.
- **On what evidence:** Empirical incident on 2026-11-04 (~20:30 UTC) where an Ida session on academicOps v1.0.1 continued to bypass sub-Ida delegation and dispatch directly to peers on the main thread because fixes developed in `nicsuzor/ida` lived only in the deployment repo and were absent from plugin distribution packages.
- **Observation / Promotion Criteria:** In subsequent conversational sessions loading `plugins/ida`, the main Ida never invokes or messages Pauli or Sara directly, delegates all execution work through internal sub-Idas (`ida:ida`), routes methodology questions to Pauli while flagging immediate views as guesses, persists all knowledge in the PKB without generating unsolicited Claude artifacts, and any accidental direct peer call is deterministically refused with `permissionDecision: "deny"`.
- **Kill / Escalation Criteria:** If the structural hook experiences false positives on legitimate subagent execution or fails to block variant peer tool calls, refine hook matching in `peer_guard.py`. If agents attempt to bypass the hook via alternate tools or scripts, escalate to container-level tool capability restrictions.
