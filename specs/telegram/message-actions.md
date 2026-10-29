---
title: Telegram Message Action Buttons
status: ready
---

# Telegram Message Action Buttons

This specification defines the default inline message action buttons (`🧐 Check logic`, `💡 Explain`, and `🧾 Reasons`) attached to replies in the `ida-telegram` plugin, their callback tap events, and the structured response forms delivered back to the operator. It serves operators interacting with conversational agents over Telegram who need to interrogate specific message statements through formal premise checks, detailed explanations, or transparent multi-level argument and delegation chains.

## User stories

### US-1 Default Message Action Buttons Attached to Replies

As an operator reading agent replies in Telegram chat, I want every message statement to carry inline actions for logic verification, explanation, and underlying reasons by default, so that I can inspect or challenge any claim with a single tap.

- **AC-1.1 (Default Action Buttons)** Given an outbound reply with action buttons enabled by default (`actions !== false`), when the reply is sent, then the message inline keyboard carries `[🧐 Check logic]`, `[💡 Explain]`, and `[🧾 Reasons]`.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`reply attaches [🧐 Check logic], [💡 Explain], and [🧾 Reasons] buttons by default`) asserts all three buttons are present with callback data `logic_check`, `explain`, and `reasons`.
- **AC-1.2 (Action Buttons Suppression)** Given an outbound reply with message actions disabled (`actions: false`), when the reply is sent, then all action buttons (`Check logic`, `Explain`, `Reasons`) are omitted from the inline keyboard.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`reply with actions: false suppresses action buttons`) asserts no action buttons are present in the inline keyboard.
- **AC-1.3 (Predefined Row Consolidation & Relocation)** Given `predefined_row: true`, when the reply is sent, then `Reasons` is consolidated onto row 0 beside `Details`, `Check logic`, and `Explain`; whenever `Explain` is suppressed or relocated, `Reasons` follows the identical placement.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (`AC1: whatever suppresses or relocates Explain (actions: false, predefined_row) does the same to Reasons`) verifies both suppression and single-row consolidation.

### US-2 Button Tap Event Delivery

As an operator tapping an action button on a message card, I want the card marked with the selected action and an inbound event delivered to the agent naming the target message, so that the agent knows which statement is being queried and what form of inspection is requested.

- **AC-2.1 (Logic Check Tap)** Given an operator taps `🧐 Check logic`, when the callback arrives, then the card is edited to append `Selected: 🧐 Check logic ✅`, action buttons are filtered out while preserving remaining buttons, and Ida receives an inbound event with `event: "logic_check"` naming the target message ID and excerpt.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC1: pressing logic-check button delivers request naming message and Ida replies with premise-check verdict`).
- **AC-2.2 (Explain Tap)** Given an operator taps `💡 Explain`, when the callback arrives, then the card is edited to append `Selected: 💡 Explain ✅`, action buttons are filtered out, and Ida receives an inbound event with `event: "explain"` naming the target message ID and excerpt.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC2: pressing explain button delivers request naming message and Ida replies expanding that message`).
- **AC-2.3 (Reasons Tap)** Given an operator taps `🧾 Reasons`, when the callback arrives, then the card is edited to append `Selected: 🧾 Reasons ✅`, action buttons are filtered out, and Ida receives an inbound event with `event: "reasons"` naming the target message ID, excerpt, and asking "How do you know that? Show the reasons and argument chain behind message...".
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC2: pressing reasons button marks card and delivers request naming message to Ida`) and `plugins/ida-telegram/test/inbound.test.ts` (`delivers reasons button tap event naming target message and excerpt`).

### US-3 Multi-Level Argument Chain Answer Form

As an operator requesting reasons behind a message, I want Ida's reply to provide a concise chat takeaway and a complete delegation tree in the reply's details holding verbatim Chained Toulmin Argdown arguments for every link in the delegation chain, so that I can audit exactly who argued what to whom without relying on post-hoc agent summaries.

- **AC-3.1 (Verbatim Arguments in Details)** Given a `reasons` event for a message, when Ida constructs the response, then the reply targets the queried message (`reply_to: message_id`), chat text stays within the ~100-word budget summarizing the takeaway and chain structure, and the `detail` parameter carries the complete delegation tree holding verbatim Chained Toulmin Argdown blocks for each available link of the chain.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC3: Ida handles reasons event by returning multi-level verbatim argument chain in details`) asserts `storedDetail.markdown` contains the verbatim Argdown blocks.
- **AC-3.2 (Sender, Recipient & Delegation Depth Nesting)** In the details argument chain, every link is explicitly labelled with who argued it and to whom (e.g. `Ida Prime → User`, `Sara → Ida Prime`, `Worker → Sara`) and formatted with hierarchical indentation or depth markers reflecting delegation nesting.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC3: Ida handles reasons event by returning multi-level verbatim argument chain in details`) asserts sender/recipient labels and delegation depth nesting across levels 1, 2, and 3.
- **AC-3.3 (Missing Arguments Explicitly Designated)** When an argument block for any delegation link cannot be found in the trace or task record, that link is explicitly named as missing (e.g. `[Missing argument: no premise-check record found for ...]`), never paraphrased or synthetically reconstructed.
  - _Check_: `plugins/ida-telegram/test/message-actions.test.ts` (`AC3: Ida handles reasons event by returning multi-level verbatim argument chain in details`) asserts missing link text appears unparaphrased in stored details.

## Design

### 1. Inline Action Buttons Configuration (US-1)

1. **Button Construction:**
   - Every reply sent via `reply` attaches message action buttons unless explicitly disabled with `actions: false`.
   - The action button set comprises:
     1. `{ text: "🧐 Check logic", callback_data: "logic_check" }`
     2. `{ text: "💡 Explain", callback_data: "explain" }`
     3. `{ text: "🧾 Reasons", callback_data: "reasons" }`
2. **Layout Placement:**
   - **Default Layout (`predefined_row: false`):** Action buttons sit on their own row at the bottom of the inline keyboard, below caller buttons, feedback buttons, and details/review buttons.
   - **Consolidated Layout (`predefined_row: true`):** Action buttons join `🔍 Details`, `🔍 Review diff`, and feedback buttons on a single top row (row 0) above caller buttons.
   - **Suppression:** Setting `actions: false` removes all three buttons equally.

### 2. Callback Ingestion & In-Place Selection (US-2)

1. **In-Place Card Marking:**
   - When a callback query with `data: "logic_check"`, `data: "explain"`, or `data: "reasons"` is received:
     - The message text is edited to append `\n\nSelected: <label> ✅`.
     - All action buttons (`logic_check`, `explain`, `reasons`) are stripped from `reply_markup.inline_keyboard`, leaving other buttons (such as `🔍 Details` or custom caller buttons) intact.
     - `answerCallbackQuery` is called to acknowledge the tap in the Telegram client.
2. **Channel Event Delivery:**
   - An inbound event is dispatched to the active agent session:
     - `event: "logic_check" | "explain" | "reasons"`
     - `action: "logic_check" | "explain" | "reasons"`
     - `meta.target_message_id`: ID of the queried message card.
     - `meta.target_excerpt`: Text excerpt of the queried message.
     - `content`: Formatted query string naming the message ID and excerpt.
       - Logic check: `Give me a logic check on message <id>: "<excerpt>" as if you were receiving it from a peer.`
       - Explain: `Please explain message <id>: "<excerpt>" in more detail.`
       - Reasons: `How do you know that? Show the reasons and argument chain behind message <id>: "<excerpt>".`

### 3. Structured Answer Forms (US-3)

1. **Logic Check Answer Form:**
   - Reply to target message (`reply_to: message_id`).
   - Chat text formatted as formal premise check verdict:
     - Headline: `**Verdict: PASS | REVISE | FAIL**`
     - Expandable blockquote (`>!`): Keyed premise check lines (`Judged`, `Valid`, `Supported`, `Answered`, `Sufficient`, `Waived`, `Relay`).
2. **Explain Answer Form:**
   - Reply to target message (`reply_to: message_id`).
   - Chat text expanding statement rationale, context, and operational implications within the ~100-word budget.
3. **Reasons Answer Form:**
   - Reply to target message (`reply_to: message_id`).
   - **Tier 1 (Chat):** Concise ~100-word summary stating the core conclusion, the delegation path, and pointing to Details for the audit record.
   - **Tier 3 (`detail` / Details Page):** Full verbatim argument chain:
     - Structure: Hierarchical delegation outline showing nesting depth (Level 1, Level 2, Level 3...).
     - Link Identity: Each node states `Sender → Recipient` (e.g. `Ida Prime → Nic (User)`, `Sara → Ida Prime`, `Worker (rbg) → Sara`).
     - Verbatim Argdown: Attached Chained Toulmin Argdown blocks enclosed in `argdown ... ` verbatim as received from each agent or task report.
     - Missing Arguments: If an argument record was unrecorded or missing for any link in the chain, it is explicitly labelled `[Missing argument: no premise-check record found for ...]`, adhering to the honest epistemics axiom (`honest-epistemics.md`) and the explanations-not-reasons axiom (`explanations-not-reasons.md`).
