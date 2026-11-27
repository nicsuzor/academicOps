---
title: Telegram Reaction Handling and Shared Legend
status: ready
---

# Telegram Reaction Handling and Shared Legend

This specification defines the Telegram message reaction contract and shared reaction legend across conversational agent personas. It establishes Telegram Bot API as the authoritative source of truth for reaction validity, uses dynamic platform error propagation, and unifies lifecycle state transitions and communicative reactions into a single unambiguous legend shared by all agent personas.

## User stories

### US-1 Telegram-Authoritative Reaction Validation

As an agent communicating over Telegram, I want message reactions validated authoritatively by Telegram, so that any emoji supported by Telegram is accepted and unsupported reactions surface platform errors directly.

- **AC-1.1** Given an agent setting a reaction on a message, when the reaction emoji is sent, then the reaction string is normalized (stripping variation selector VS16 `\uFE0F`, trimming whitespace, and standardizing single-grapheme aliases) and passed directly to Telegram Bot API `setMessageReaction`.
- **AC-1.2** Given an agent attempting a reaction with an emoji unsupported by Telegram, when `setMessageReaction` executes against the Telegram Bot API, then Telegram's authoritative error (such as `400 Bad Request: REACTION_INVALID`) is surfaced verbatim to the calling tool.
- **AC-1.3** Given a reaction input containing multiple emojis or non-emoji text, when normalization runs prior to API dispatch, then the request fails fast with an explicit formatting error before calling the Telegram API.

### US-2 Cross-Persona Shared Reaction Legend

As an operator interacting with multiple bot personas across chat windows, I want a single unified reaction legend with exactly one meaning per reaction and one reaction per lifecycle state, so that message status and semantic feedback remain clear and consistent across all bots.

- **AC-2.1** Given an inbound user message, when the message arrives and advances through lifecycle milestones, then every bot persona updates the message reaction according to the unified lifecycle legend:
  - `👀` : Inbound message received and being read/assessed.
  - `✍` : Captured / Pauli durable-fact capture: note, decision, intake, or task persisted to knowledge base, or message sent to Pauli solely to extract durable facts.
  - `🤓` : Dispatched (Pauli, other knowledge work): message held by Pauli for knowledge work other than durable-fact capture.
  - `🗿` : Dispatched (compliance): message held for compliance or rule review.
  - `👨‍💻` : Dispatched (James): message held by James for execution supervision or review arbitration.
  - `💅` : Dispatched (Marsha): message held by Marsha for qualitative excellence review.
  - `🤪` : Sub-Ida (self): a sub-Ida is judging or handling the message herself.
  - `🐳` : Dispatched (Sara / polecat): briefed and dispatched to Sara or an isolated background polecat worker.
  - `👾` : Dispatched (agy, in-session): work held by an in-session `agy` run.
  - `👻` : Dispatched (agy, containerised synchronous): work held by a containerised synchronous `agy` run.
  - `🕊` : Dispatched (general-purpose subagent): used only when a sub-Ida hands off work to a general-purpose subagent.
  - `🤝` : Dispatched (peer): briefed and handed off to an independent peer agent.
  - `👌` : Understood / addition taken on: acknowledged an addition, modification, or constraint taken on to existing work or direction.
  - `🤔` : Waiting: a question, choice, or clarification is pending user reply.
  - `💔` : Blocked or failed: execution halted or hit an external blocker (reply details the refusal).
  - `🎉` : Completed: task answered or resolved with substantive reply.
  - `🫡` : Acknowledged: request handled/completed where no substantive reply was owed.
- **AC-2.2** Given work execution or delegation, when a sub-Ida handles it herself, then the persona reacts with `🤪`; when sent to Pauli solely for durable-fact capture, `✍`; when held by Pauli for other knowledge work, `🤓`; when held for compliance or rule review, `🗿`; when held by James, `👨‍💻`; when held by Marsha, `💅`; when handed to Sara or an isolated background worker, `🐳`; when held by an in-session `agy` run, `👾`; when held by a containerised synchronous `agy` run, `👻`; when a sub-Ida hands off to a general-purpose subagent, `🕊`; and when briefed and handed off to an independent peer agent, `🤝`.
- **AC-2.3** Given communicative feedback or content-specific reactions, when an agent or operator reacts to message substance, then every reaction carries exactly one semantic meaning across all personas:
  - `👎` : Negative feedback on substance / report failure (prompts autonomous remediation).
  - `👍` : Affirmative confirmation or approval.
  - `🔥` : Exceptional idea, high resonance, or breakthrough.
  - `💯` : Exact agreement, fully aligned (expresses consensus or agreement; `🤝` is reserved strictly for peer dispatch so no emoji carries two meanings).
  - `🏆` : Milestone reached or difficult feat accomplished.
  - `🙏` : Gratitude or appreciation.
  - `🤣` : Humor or joke acknowledged.
  - `🤯` : Surprising or unexpected finding / revelation.
  - `😢` : Regrettable outcome or unfortunate news.
- **AC-2.4 Holding Reaction Lifetime and Bot Delegation Notices:**
  - Given a request being worked on locally or delegated, when the message transitions to a holding state (`👨‍💻`, `🕊`, `🐱`, or `🤝`), then the holding reaction remains on the user's originating message throughout the duration of execution until the substantive answer or resolution is sent (replacing the holding reaction with `🎉`, `🫡`, or `💔`).
  - Given an outbound delegation message sent by the bot informing the user of delegated work (e.g. "I've asked [Peer/Worker]..."), then the bot marks its own delegation message with the matching holding reaction (`🤝`, `🐱`, or `🕊`).

### US-3 Observable Verification Contract

As an implementer and reviewer verifying reaction handling, I want outcome-level build criteria mapped to objective verification checks, so that implementation correctness is deterministically auditable.

- **AC-3.1** Given an implementation of the reaction handling contract, when verification checks run against each build criterion, then every criterion produces its defined observable outcome.

## Design

### 1. Telegram Bot API Reaction Contract & Error Propagation

The Telegram Bot API (`setMessageReaction`) accepts an array containing a single `ReactionTypeEmoji` object: `{ type: "emoji", emoji: string }`. While Telegram provides no global Bot API endpoint listing all supported reaction emojis, Telegram authoritatively validates reactions upon submission. If a requested emoji is unsupported globally or forbidden in the target chat, Telegram returns HTTP `400 Bad Request` with description `Bad Request: REACTION_INVALID`. In chats with restricted reaction sets, `getChat` returns `available_reactions` in `ChatFullInfo`; where omitted, all standard emoji reactions are permitted.

Reaction validation operates under platform authority:

1. **Canonical Normalization:** Reaction normalization strips Unicode variation selector VS16 (`\uFE0F`), trims whitespace, maps canonical equivalents (e.g. `❤️` to `❤`, `✍️` to `✍`), and verifies the input consists of a single Unicode grapheme cluster. Multi-emoji strings (e.g., `💩🦄`) are rejected immediately prior to network dispatch. Multi-codepoint single-grapheme sequences (including ZWJ sequences such as `👨‍💻`) are preserved and passed cleanly.
2. **Authoritative Error Propagation:** The bot client dispatches normalized emojis directly to `setMessageReaction`. When the Telegram Bot API rejects a reaction, the error description is preserved and surfaced directly to the calling tool or agent. The tool returns failure carrying Telegram's verbatim error message.

### 2. Unified Shared Reaction Legend

All agent personas operating over Telegram share a single reaction legend. Each reaction has exactly one meaning, and each state has exactly one designated reaction:

| Reaction | Category | State / Meaning | Transition / Usage Context |
| :- | :- | :- | :- |
| `👀` | Lifecycle | Inbound received | Automatically applied upon message arrival while reading and planning |
| `✍` | Lifecycle | Captured / Pauli durable-fact capture | Applied when note, decision, intake, or task is persisted to knowledge base, or when sent to Pauli solely to extract durable facts |
| `🤓` | Lifecycle | Dispatched (Pauli, other knowledge work) | Applied when held by Pauli for knowledge work other than durable-fact capture |
| `🗿` | Lifecycle | Dispatched (compliance) | Applied when held for compliance or rule review |
| `👨‍💻` | Lifecycle | Dispatched (James) | Applied when held by James for execution supervision or review arbitration |
| `💅` | Lifecycle | Dispatched (Marsha) | Applied when held by Marsha for qualitative excellence review |
| `🤪` | Lifecycle | Sub-Ida (self) | Applied when a sub-Ida is judging or handling the message herself |
| `🐳` | Lifecycle | Dispatched (Sara / polecat) | Applied when briefed and launched to Sara or an isolated background polecat worker |
| `👾` | Lifecycle | Dispatched (agy, in-session) | Applied when held by an in-session `agy` run |
| `👻` | Lifecycle | Dispatched (agy, containerised synchronous) | Applied when held by a containerised synchronous `agy` run |
| `🕊` | Lifecycle | Dispatched (general-purpose subagent) | Applied only when a sub-Ida hands off work to a general-purpose subagent |
| `🤝` | Lifecycle | Dispatched (peer) | Applied when work is briefed and handed off to an independent peer agent |
| `👌` | Lifecycle | Understood / Addition taken on | Applied when acknowledging an addition, modification, or constraint taken on to active work |
| `🤔` | Lifecycle | Waiting | Applied when a question, choice, or clarification is pending in chat |
| `💔` | Lifecycle | Blocked / Failed | Applied when execution fails or an external blocker halts progress |
| `🎉` | Lifecycle | Completed | Applied when task is resolved and a substantive reply is delivered |
| `🫡` | Lifecycle | Acknowledged | Applied when task is completed and no reply was owed |
| `👎` | Feedback | Substance defect | Operator feedback indicating substantive failure (prompts autonomous remediation) |
| `👍` | Feedback | Affirmation | Positive confirmation or approval |
| `🔥` | Semantic | Breakthrough | High resonance or exceptionally strong idea |
| `💯` | Semantic | Aligned | Complete agreement or consensus reached |
| `🏆` | Semantic | Milestone | Significant achievement or completed major effort |
| `🙏` | Semantic | Appreciation | Gratitude or thanks |
| `🤣` | Semantic | Humor | Humorous remark or joke |
| `🤯` | Semantic | Surprising | Unexpected finding or startling discovery |
| `😢` | Semantic | Regret | Unfortunate news or regrettable outcome |

#### Disambiguation and No Duplicate Meanings

To prevent semantic collision:

1. `🤝` is designated exclusively as the lifecycle state for peer dispatch ("a peer holds it", e.g. Sara or Pauli).
2. Semantic agreement or consensus is expressed through `💯` ("aligned") or `👍` ("affirmation"), eliminating dual use of `🤝` for both lifecycle dispatch and semantic consensus.
3. Every agent kind and execution surface has a distinct holding reaction:
   - `🤪`: Sub-Ida judging or handling it herself.
   - `✍`: Pauli solely capturing durable facts (and persisted capture).
   - `🤓`: Pauli on other knowledge work.
   - `🗿`: Compliance/rule review (stone-faced bench; Telegram's `ReactionTypeEmoji` set has no judge or gavel emoji).
   - `👨‍💻`: James execution supervision / review arbitration.
   - `💅`: Marsha qualitative excellence review.
   - `🐳`: Sara and isolated background polecat workers.
   - `👾`: In-session `agy` run (Telegram's `ReactionTypeEmoji` set has no robot emoji).
   - `👻`: Containerised synchronous `agy` run.
   - `🕊`: General-purpose subagent hand-off from a sub-Ida only.
   - `🤝`: Independent peer agent delegation.
4. `👌` provides a dedicated acknowledgment for additions and mid-flight constraints taken on, distinct from initial receipt (`👀`) and complete acknowledgement where no reply was owed (`🫡`).

#### Holding Reaction Lifetime and Bot Delegation Notices

The holding reactions (`👨‍💻`, `🕊`, `🐱`, `🤝`) communicate active ownership of pending work:

- **Lifetime on user messages:** When a user request enters a holding state, the holding reaction remains on the originating user message throughout execution. It is replaced only when execution concludes: transitioning to `🎉` (completed with substantive reply), `🫡` (acknowledged), or `💔` (blocked or failed).
- **Outbound delegation notice tagging:** When a bot informs the user that work has been delegated (e.g. posting "I've asked Sara to...", "I've briefed a worker to..."), the bot also tags its own outbound notice message with the corresponding holding reaction (`🤝`, `🐱`, or `🕊`).

### 3. Outcome-Level Build Criteria Mapped to Checks

Implementation tasks must satisfy seven outcome-level build criteria, each validated by an observable verification check:

| Build Criterion | Outcome Description | Verification Check |
| :- | :- | :- |
| **BC-1: Unified Legend in Instructions** | Agent instructions define the unified shared legend with `🐳` for polecat work and `🕊` for subagent work, with no conflicting definitions across personas. | Inspection of agent instructions shows the unified legend documented with `🐳` for polecats and `🕊` for subagents and no conflicting reaction mappings. |
| **BC-2: Normalization & Single-Grapheme Validation** | Normalization cleans Unicode variation selectors, maps canonical equivalents, validates single grapheme clusters, and accepts arbitrary valid single emojis. | Demonstration that arbitrary valid emojis normalize cleanly, variation selectors are stripped, and multi-emoji payloads are rejected upfront. |
| **BC-3: Authoritative Error Propagation** | The reaction tool and bot client propagate Telegram API responses directly, returning failure with Telegram's verbatim error on rejection. | Demonstration that Telegram `REACTION_INVALID` responses return failure carrying Telegram's verbatim error description, and accepted reactions return success. |
| **BC-4: Regression & Automated Invariants** | Automatic reaction behavior (such as `👀` on inbound messages) and lifecycle transitions remain fully operational. | Successful execution of the full regression test suite with zero test failures. |
| **BC-5: Four Added Reaction Meanings in Shared Legend** | The shared legend defines `👨‍💻` for local execution, `🤝` for peer dispatch, `👌` for additions taken on, and `💯` for agreement (with `🤝` removed from semantic reactions so no reaction carries two meanings) across all bot persona instructions. | Inspection of `plugins/ida-telegram/skills/telegram/SKILL.md` and `specs/telegram/reactions.md` verifies each of the four meanings is assigned one reaction and no reaction carries two meanings. |
| **BC-6: Holding Reaction Lifetime and Bot Delegation Notices** | Holding reactions (`👨‍💻`, `🕊`, `🐱`, `🤝`) persist on the originating user message until resolution (`🎉`, `🫡`, `💔`), and outbound bot delegation messages ("I've asked...") are tagged with the corresponding holding reaction. | Inspection of agent instructions and channel message logs demonstrates holding reactions persist on the originating user message throughout execution and outbound delegation notices are tagged. |
| **BC-7: Grapheme Validation and Telegram Acceptance for Added Emojis** | The added emojis `👨‍💻` (multi-codepoint ZWJ sequence), `🤝`, and `👌` normalize cleanly via `normalizeReaction` as valid single grapheme clusters and pass to the Telegram API without upfront rejection. | Execution of automated tests in `plugins/ida-telegram/test/reactions.test.ts` verifying `normalizeReaction` accepts `👨‍💻`, `🤝`, and `👌`. |

### 4. Enforcement Map Extract and Proportionality Pass

#### Enforcement Map Extract

The surfaces touched by this design correspond to the following entry in [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md):

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Skill Rule: Telegram Shared Reaction Legend](../../plugins/ida-telegram/skills/telegram/SKILL.md) -- Bot personas share a unified reaction legend with Telegram API error propagation replacing static allowlists. | instructions, structural | imperative, protection | `plugins/ida-telegram/skills/telegram/SKILL.md:50-75`, `specs/telegram/reactions.md:20-140`, `plugins/ida-telegram/src/telegram/reactions.ts:1-25`, `plugins/ida-telegram/test/reactions.test.ts:72-120` |

#### Proportionality Pass (`specs/enforcement/enforcement.md`)

This design is evaluated against the enforcement pyramid options pass in [`specs/enforcement/enforcement.md`](../enforcement/enforcement.md):

1. **Instructions (`imperative`):** Shared legend semantics, holding reaction lifetimes, and delegation notice tagging are specified directly in agent instructions (`plugins/ida-telegram/skills/telegram/SKILL.md`) and the governing specification (`specs/telegram/reactions.md`). Instructions work across the full persona class without requiring brittle mechanical state machines.
2. **Structural (`protection`):** Unicode normalization (`normalizeReaction`) validates single-grapheme clusters prior to API dispatch, preventing invalid multi-character payloads from hitting the network while relying on Telegram's authoritative error propagation for emoji validity.
3. **No over-engineering:** No custom parser, deterministic NLP keyword matcher, or bespoke middleware is introduced. The design relies exclusively on standard agent instructions and existing Telegram Bot API methods, satisfying `no-over-engineering` and `proportionate`.
