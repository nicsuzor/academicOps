---
title: Telegram Reply Button Layout and Predefined Row
status: ready
---

# Telegram Reply Button Layout and Predefined Row

This specification defines the button layout customization and predefined button consolidation contracts for reply messages in the `ida-telegram` plugin. It serves operators interacting with conversational agents over Telegram who need compact, multi-row button grids and a single prominent header row for system actions.

## User stories

### US-1 Caller-Specified Button Layout Grid

As an operator interacting with multi-option prompts (such as skill or workflow selection checklists), I want reply buttons arranged in multi-column rows rather than an unwieldy single vertical column, so that option choices fit comfortably on a mobile screen without excessive scrolling.

- **AC-1.1** Given a reply request carrying 8 option buttons arranged in a multi-row grid (via a 2D button array or layout specifications), when the message is sent, then the Telegram inline keyboard contains the buttons arranged in the caller's chosen multi-row grid rather than one button per row.
- **AC-1.2** Given a flat array of buttons with a `button_layout` array (e.g. `[3, 3, 2]`), when the message is sent, then the Telegram inline keyboard groups buttons into rows according to the specified count per row.
- **AC-1.3** Given a flat array of buttons with `buttons_per_row` (or numeric `button_layout`), when the message is sent, then the Telegram inline keyboard partitions buttons into rows of that size.
- **AC-1.4** Given a flat array of buttons without layout options, when the message is sent, then the plugin preserves backward compatibility by placing one button per row.

### US-2 Predefined Buttons Consolidated on the Default First Row

As an operator reading agent replies with system actions (such as Details, Check logic, Explain, Reasons, and Accept/Decline recommendation), I want all active predefined buttons grouped together on a single default row so that common navigational and meta-actions remain predictable and compact without consuming multiple rows or truncating labels on mobile widths.

- **AC-2.1** Given `detailsId` present and message actions disabled (`actions: false`), when the reply is sent, then `🔍` is placed on its row alone without label text beside the icon.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (Details icon alone on row 0).
- **AC-2.2** Given `detailsId` present and message actions enabled (`actions: true`), when the default reply is sent, then Details (`🔍`), Check logic (`🧐 Check`), Explain (`💡 Explain`), Reasons (`🧾`), Accept (`✅`), and Decline (`❌`) all sit together on the same row.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (default reply keyboard with Details and action buttons on the same row).
- **AC-2.3** Given `predefined_row: true` with both predefined buttons and caller buttons present, when the reply is sent, then the consolidated predefined row sits at the top (row 0) above the caller's custom button rows.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (predefined row at row 0 above caller grid).
- **AC-2.4** Given `predefined_row: false` or omitted with caller buttons present, when the reply is sent, then the consolidated predefined row sits below caller buttons, with Details on the same row as the other predefined action buttons.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (predefined row below caller buttons with Details on same row).

### US-3 Recommendation Action Buttons on Replies

As an operator receiving agent recommendations in chat, I want direct accept and decline recommendation buttons attached alongside Check logic and Explain on replies, with clear and compact icons alone (`✅`, `❌`), so that I can accept or decline recommendations with a single tap and immediately notify the agent of my choice without horizontal label truncation.

- **AC-3.1** Every reply that carries default message actions attaches `[✅]` and `[❌]` alongside `[🧐 Check]`, `[💡 Explain]`, and `[🧾]`. Passing `actions: false` suppresses all default action buttons including both recommendation buttons; Details sits on the same row.
  - _Check_: `plugins/ida-telegram/test/recommendation-actions.test.ts` (AC1 default attachment and suppression) and `plugins/ida-telegram/test/reply-buttons.test.ts` (AC2).
- **AC-3.2** Tapping `[✅]` or `[❌]` acknowledges the callback, edits the Telegram message card to show the user's choice (`Selected: <label> ✅`), removes the recommendation buttons from the inline keyboard while preserving other buttons (Details, Review diff, Check logic, Explain, Reasons), and delivers an event to Ida (`accept_recommendation` or `decline_recommendation`) naming the target message ID, text excerpt, and whether the user accepted or declined the recommendation.
  - _Check_: `plugins/ida-telegram/test/recommendation-actions.test.ts` (AC2 tapping, card marking, button filtering, and event delivery).

### US-4 Caller-Supplied Reply Button Tap Acknowledgement

As an operator tapping a custom option button on an agent reply card (such as a workflow, skill, or decision choice), I want the button tap immediately acknowledged in the Telegram client, the card marked with my chosen label, and the choice forwarded to the agent, so that I receive instant visual feedback without waiting on the receiving session or triggering repeated taps.

- **AC-4.1 (Immediate Tap Acknowledgement & In-Place Selection)** Given an operator taps any caller-supplied reply button on a message card, when the callback arrives, then:
  1. The callback query is answered immediately via `answerCallbackQuery` to dismiss the client spinner.
  2. The message card is edited to append `Selected: <label> ✅` to the text or caption.
  3. Caller option buttons are removed from the card's inline keyboard while preserving active predefined buttons (such as `🔍 Details`, `🔍 Review diff`, feedback buttons, or action buttons).
  4. An inbound event is dispatched to the active agent session with `event: "button_tap"`, `content: "tapped <label>"`, `callback_prefix`, `payload`, `label`, and target message identity.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (`AC3: defect check: tapping caller-supplied reply button acknowledges callback, marks card, preserves Details button, and delivers event to session`).
- **AC-4.2 (Universal Callback Acknowledgement Across All Button Families)** Every callback-button family emitted by the plugin (`reply` caller buttons, predefined action buttons `logic_check`/`explain`/`reasons`, recommendation buttons `accept_recommendation`/`decline_recommendation`, feedback buttons `fb:*`, question buttons `q:*`, and permission buttons `perm:*`) immediately acknowledges incoming callback queries via `answerCallbackQuery`. Client-side WebApp buttons (`web_app` for Details, Review diff, Mini App review, and caller Mini Apps) are exempt because Telegram handles WebApps client-side without emitting `callback_query` updates.
  - _Check_: `plugins/ida-telegram/test/reply-buttons.test.ts` (`AC4: defect check: every callback-button family emitted by the plugin acknowledges callback query immediately`).

## Design

### 1. Custom Button Layouts (US-1)

1. **Input Flexibility:**
   The `reply` tool accepts buttons in either of two structures:
   - **2D Grid Array (`buttons: ReplyButtonOption[][]`):** The caller directly defines each row as an array of button objects.
   - **Flat Array (`buttons: ReplyButtonOption[]`):** Sliced into rows using layout parameters:
     - `button_layout: number[]` specifies the explicit button count for each successive row (e.g. `[3, 3, 2]`). Any remaining buttons are placed in subsequent rows following the last specified count or 1.
     - `buttons_per_row: number` (or numeric `button_layout: number`) partitions the flat array into uniform rows of that maximum width.
     - `row: number` property on individual button objects allows sparse or explicit row grouping.
   - **Default Behavior:** A flat button array without layout parameters defaults to 1 button per row for backward compatibility.

2. **Verification Check:**
   - Checked by `plugins/ida-telegram/test/reply-buttons.test.ts` (AC1 tests: 2D array grid, `button_layout: [3, 3, 2]`, `buttons_per_row: 4`, and default single-column fallback).

### 2. Predefined Row Consolidation and Button Labels (US-2)

1. **Button Labels:**
   - Predefined buttons show clear, compact labels designed to fit within mobile screen widths:
     1. `🔍` (icon alone): Opens Details page (when `detailsId` is present).
     2. `🧐 Check`: Triggers peer logic check (`callback_data: "logic_check"`).
     3. `💡 Explain`: Requests detailed explanation (`callback_data: "explain"`).
     4. `🧾` (icon alone): Requests underlying argument reasons (`callback_data: "reasons"`).
     5. `✅` (icon alone): Accepts recommendation (`callback_data: "accept_recommendation"`).
     6. `❌` (icon alone): Declines recommendation (`callback_data: "decline_recommendation"`).
   - Reasons, Accept, Decline, and Details carry their icon alone without text beside the icon. Check logic (`🧐 Check`) and Explain (`💡 Explain`) keep short labels so their distinct actions are recognisable at a glance without truncating at phone width.

2. **Default Single-Row Layout and Predefined Row:**
   - **Default Layout:** In the default reply keyboard (`predefined_row: false` or omitted), Details sits on the same row as the predefined action buttons (`[🔍, 🧐 Check, 💡 Explain, 🧾, ✅, ❌]`), below caller buttons if present, or at row 0 if no caller buttons are present. This prevents Details from consuming an extra vertical row.
   - **Top-Row Predefined Option (`predefined_row: true`):** Consolidates all active predefined buttons onto row index 0 at the top, positioned above any caller option buttons.
   - **Zero Predefined Buttons:** When no predefined buttons are active (e.g. `actions: false` without details or feedback), no empty row is prepended.

3. **In-Place Action Interaction:**
   When an operator taps `🧐 Check` or `💡 Explain`, the callback handler filters out the tapped actions while preserving other buttons on that same row (such as `🔍`, `🧾`, `✅`, `❌`) and all caller rows.

4. **Verification Check:**
   - Checked by `plugins/ida-telegram/test/reply-buttons.test.ts` (Details icon alone, action buttons on same row as Details in default reply keyboard, predefined row above caller grid rows, and short button labels).

### 3. Recommendation Action Buttons (US-3)

1. **Default Attachment and Suppression:**
   Every reply attaches `[✅]` (callback `accept_recommendation`) and `[❌]` (callback `decline_recommendation`) alongside `[🧐 Check]`, `[💡 Explain]`, and `[🧾]` unless `actions: false` is passed. Details (`🔍`) sits on the same row.

2. **In-Place Card Update & Filtering:**
   When an operator taps either button:
   - The bot acknowledges the callback query immediately to dismiss the client spinner.
   - The message text is edited in-place to append `Selected: <label> ✅`.
   - The inline keyboard filters out both recommendation buttons (`accept_recommendation` and `decline_recommendation`) while preserving other buttons (such as `🔍`, `[🧐 Check]`, `[💡 Explain]`, `[🧾]`, and custom caller rows).

3. **Event Delivery:**
   The bot delivers an inbound event to Ida (`event: "accept_recommendation"` or `event: "decline_recommendation"`), including:
   - `content`: `"The user accepted the recommendation for message <id>: \"<excerpt>\"."` or `"The user declined the recommendation for message <id>: \"<excerpt>\"."`
   - `meta`: `target_message_id`, `target_excerpt`, `action`, `event`, `recommendation` (`"accepted"` / `"declined"`), `choice` (`"accept"` / `"decline"`), `label`, `chat_id`, `user_id`.

4. **Verification Checks:**
   - Attachment, suppression, and row consolidation checked by `plugins/ida-telegram/test/recommendation-actions.test.ts` (AC1) and `plugins/ida-telegram/test/reply-buttons.test.ts` (AC2).
   - Tapping, card marking, button filtering, and event delivery checked by `plugins/ida-telegram/test/recommendation-actions.test.ts` (AC2) and `plugins/ida-telegram/test/inbound.test.ts`.

### 4. Caller-Supplied Button Tap Acknowledgement (US-4)

1. **Immediate Client Acknowledgement:**
   When any `callback_query` arrives for a caller-supplied button, the bot calls `answerCallbackQuery` immediately with `callback_query_id: cb.id`, dismissing the loading spinner in the operator's client without waiting for turn completion or downstream session execution.

2. **In-Place Card Marking & Filtering:**
   - Appends `\n\nSelected: <label> ✅` to the message text or caption (stripping previous selection if already present to prevent duplicate markings on retry).
   - Filters out all caller-supplied option buttons from `inline_keyboard` so the operator cannot double-submit choices, while preserving active predefined buttons (such as `🔍 Details`, `🔍 Review diff`, feedback buttons, and predefined action buttons).
   - If the message was sent with audio or caption, updates the message caption; falls back to unformatted plain text if Telegram rejects formatted entities.

3. **Channel Event Delivery:**
   - Dispatches `button_tap` inbound event to the active session via `emitChannelEvent`:
     - `content`: `"tapped <label>"`
     - `meta`: `event: "button_tap"`, `callback_id`, `callback_prefix`, `payload`, `label`, `target_message_id`, `chat_id`, `user_id`, and `message_thread_id` / `thread_id` when inside a forum thread.

4. **Universal Callback Acknowledgement Contract:**
   All callback-button families emitted by the plugin (`reply` caller buttons, predefined action buttons, recommendation buttons, feedback buttons, question cards, and permission cards) immediately acknowledge incoming callback queries via `answerCallbackQuery`. Client-side WebApp buttons (`web_app` for Details, Review diff, Mini App review, and caller Mini Apps) are exempt because Telegram handles WebApps client-side without emitting `callback_query` updates.

5. **Verification Checks:**
   - Checked by `plugins/ida-telegram/test/reply-buttons.test.ts` (AC3 for caller-supplied button tap, card marking, Details preservation, and session delivery; AC4 for immediate acknowledgement across all emitted callback-button families).
