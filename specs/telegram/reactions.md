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
  - `✍` : Captured: note, decision, intake, or task persisted to knowledge base.
  - `🕊` : Dispatched: briefed and dispatched to an autonomous background worker.
  - `🤔` : Waiting: a question, choice, or clarification is pending user reply.
  - `💔` : Blocked or failed: execution halted or hit an external blocker (reply details the refusal).
  - `🎉` : Completed: task answered or resolved with substantive reply.
  - `🫡` : Acknowledged: request handled/completed where no substantive reply was owed.
- **AC-2.2** Given the "dispatched" lifecycle milestone, when work is handed to an autonomous background worker, then all personas react with `🕊`.
- **AC-2.3** Given communicative feedback or content-specific reactions, when an agent or operator reacts to message substance, then every reaction carries exactly one semantic meaning across all personas:
  - `👎` : Negative feedback on substance / report failure (prompts autonomous remediation).
  - `👍` : Affirmative confirmation or approval.
  - `🔥` : Exceptional idea, high resonance, or breakthrough.
  - `🤝` : Agreement or consensus reached.
  - `💯` : Exact agreement, fully aligned.
  - `🏆` : Milestone reached or difficult feat accomplished.
  - `🙏` : Gratitude or appreciation.
  - `🤣` : Humor or joke acknowledged.
  - `🤯` : Surprising or unexpected finding / revelation.
  - `😢` : Regrettable outcome or unfortunate news.

### US-3 Observable Verification Contract

As an implementer and reviewer verifying reaction handling, I want outcome-level build criteria mapped to objective verification checks, so that implementation correctness is deterministically auditable.

- **AC-3.1** Given an implementation of the reaction handling contract, when verification checks run against each build criterion, then every criterion produces its defined observable outcome.

## Design

### 1. Telegram Bot API Reaction Contract & Error Propagation

The Telegram Bot API (`setMessageReaction`) accepts an array containing a single `ReactionTypeEmoji` object: `{ type: "emoji", emoji: string }`. While Telegram provides no global Bot API endpoint listing all supported reaction emojis, Telegram authoritatively validates reactions upon submission. If a requested emoji is unsupported globally or forbidden in the target chat, Telegram returns HTTP `400 Bad Request` with description `Bad Request: REACTION_INVALID`. In chats with restricted reaction sets, `getChat` returns `available_reactions` in `ChatFullInfo`; where omitted, all standard emoji reactions are permitted.

Reaction validation operates under platform authority:

1. **Canonical Normalization:** Reaction normalization strips Unicode variation selector VS16 (`\uFE0F`), trims whitespace, maps canonical equivalents (e.g. `❤️` to `❤`, `✍️` to `✍`), and verifies the input consists of a single Unicode grapheme cluster. Multi-emoji strings (e.g., `💩🦄`) are rejected immediately prior to network dispatch.
2. **Authoritative Error Propagation:** The bot client dispatches normalized emojis directly to `setMessageReaction`. When the Telegram Bot API rejects a reaction, the error description is preserved and surfaced directly to the calling tool or agent. The tool returns failure carrying Telegram's verbatim error message.

### 2. Unified Shared Reaction Legend

All agent personas operating over Telegram share a single reaction legend. Each reaction has exactly one meaning, and each state has exactly one designated reaction:

| Reaction | Category | State / Meaning | Transition / Usage Context |
| :- | :- | :- | :- |
| `👀` | Lifecycle | Inbound received | Automatically applied upon message arrival while reading and planning |
| `✍` | Lifecycle | Captured | Applied when note, decision, intake, or task is persisted to knowledge base |
| `🕊` | Lifecycle | Dispatched | Applied when work is briefed and launched to a background worker |
| `🤔` | Lifecycle | Waiting | Applied when a question, choice, or clarification is pending in chat |
| `💔` | Lifecycle | Blocked / Failed | Applied when execution fails or an external blocker halts progress |
| `🎉` | Lifecycle | Completed | Applied when task is resolved and a substantive reply is delivered |
| `🫡` | Lifecycle | Acknowledged | Applied when task is completed and no reply was owed |
| `👎` | Feedback | Substance defect | Operator feedback indicating substantive failure (prompts autonomous remediation) |
| `👍` | Feedback | Affirmation | Positive confirmation or approval |
| `🔥` | Semantic | Breakthrough | High resonance or exceptionally strong idea |
| `🤝` | Semantic | Agreement | Consensus reached or proposal accepted |
| `💯` | Semantic | Aligned | Complete agreement or exact match |
| `🏆` | Semantic | Milestone | Significant achievement or completed major effort |
| `🙏` | Semantic | Appreciation | Gratitude or thanks |
| `🤣` | Semantic | Humor | Humorous remark or joke |
| `🤯` | Semantic | Surprising | Unexpected finding or startling discovery |
| `😢` | Semantic | Regret | Unfortunate news or regrettable outcome |

`🕊` is the designated reaction across all bot personas for work briefed and dispatched to background workers, maintaining gender-neutral phrasing and cross-persona consistency.

### 3. Outcome-Level Build Criteria Mapped to Checks

Implementation tasks must satisfy four outcome-level build criteria, each validated by an observable verification check:

| Build Criterion | Outcome Description | Verification Check |
| :- | :- | :- |
| **BC-1: Unified Legend in Instructions** | Agent instructions define the unified shared legend with `🕊` as the sole reaction for dispatched work, with no conflicting definitions across personas. | Inspection of agent instructions shows the unified legend documented with `🕊` for dispatched work and no conflicting reaction mappings. |
| **BC-2: Normalization & Single-Grapheme Validation** | Normalization cleans Unicode variation selectors, maps canonical equivalents, validates single grapheme clusters, and accepts arbitrary valid single emojis. | Demonstration that arbitrary valid emojis normalize cleanly, variation selectors are stripped, and multi-emoji payloads are rejected upfront. |
| **BC-3: Authoritative Error Propagation** | The reaction tool and bot client propagate Telegram API responses directly, returning failure with Telegram's verbatim error on rejection. | Demonstration that Telegram `REACTION_INVALID` responses return failure carrying Telegram's verbatim error description, and accepted reactions return success. |
| **BC-4: Regression & Automated Invariants** | Automatic reaction behavior (such as `👀` on inbound messages) and lifecycle transitions remain fully operational. | Successful execution of the full regression test suite with zero test failures. |
