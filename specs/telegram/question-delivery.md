---
title: Telegram Question Card Delivery Guarantee
status: ready
---

# Telegram Question Card Delivery Guarantee

This specification defines the delivery guarantee for structured questions posted to the operator over Telegram via the `ask_user` MCP tool and the native `AskUserQuestion` `PreToolUse` hook in the `ida-telegram` plugin. It guarantees that a question reported posted was actually delivered to the operator's chat with its option buttons, and that delivery failures halt and surface immediately rather than leaving agents waiting indefinitely for answers to undelivered questions.

## User stories

### US-1 Confirmed Delivery Verification and Button Rendering

As an operator interacting with an agent over Telegram, I want every question reported posted by the agent to actually appear in my chat with its selectable option buttons, so that I can make decisions and reply directly in the client.

- **AC-1.1 (Delivery Confirmation & Button Rendering)** Given a question sent via `ask_user` or the `AskUserQuestion` Unix socket bridge, when the question is processed with chat delivery enabled (`chat !== false` and `mini_app_only !== true`), then the bot sends `sendMessage` carrying formatted entities and vertical inline keyboard buttons, receives a successful Telegram response with `message_id`, records `messageId` on the stored question record, and only then reports the question as posted to the operator.
  - _Check_: `plugins/ida-telegram/test/questions.test.ts` (`AC1: question reported posted is confirmed delivered with buttons and messageId`) asserts `sendMessage` was called, option buttons are present in `reply_markup.inline_keyboard`, `broker.getQuestion(qid).messageId` matches Telegram's `message_id`, and the success response is returned.
- **AC-1.2 (Active Bot Instance Resolution in Bridge Server)** Given the plugin lifecycle where `createBridgeServer` and `TelegramBotClient` are instantiated during server startup, when the bridge receives an `ask_user` request from the Unix domain socket, the bridge resolves the live `TelegramBotClient` instance dynamically (via direct reference or getter closure) and delivers the question card.
  - _Check_: `plugins/ida-telegram/test/questions.test.ts` (`AC1 & AC2: bridge server resolves live bot instance and dispatches chat card instead of dropping cards due to startup null binding`) asserts the bridge dispatches the card even when the bot reference is resolved dynamically.
- **AC-1.3 (Plain-Text Entity Fallback)** Given Telegram Bot API rejects formatted markdown entities on a question card, then the plugin resends the card once as plain text with the vertical inline keyboard buttons preserved.
  - _Check_: `plugins/ida-telegram/test/questions.test.ts` (`sendQuestionCard falls back to plain text send when formatted entities are rejected`) asserts plain-text fallback succeeds with buttons intact.

### US-2 Loud Failure Surfacing on Delivery Errors

As an autonomous agent invoking `AskUserQuestion` or `ask_user`, I want infrastructure failures (missing bot client, Telegram network or API errors, missing allowed chat ID) to halt loudly and surface immediately, so that I am never told a question was posted when it was not delivered and never end my turn waiting for an impossible answer.

- **AC-2.1 (Error Surfacing in MCP `ask_user`)** When chat delivery is requested but the bot client is not running, the destination chat ID is missing, or the Telegram `sendMessage` API call fails, `ask_user` returns an error result (`{ success: false, error: "..." }`) rather than reporting that the question was posted.
  - _Check_: `plugins/ida-telegram/test/questions.test.ts` (`AC2: ask_user returns error and does not report question posted when Telegram API fails`) asserts `{ success: false }` is returned with the error description.
- **AC-2.2 (Fast Failure in `AskUserQuestion` Hook)** When the `AskUserQuestion` `PreToolUse` hook encounters a bridge error or delivery failure from the socket, the hook exits with non-zero status and writes the failure description to `stderr`, rather than outputting a denial payload that claims the question was posted over Telegram.
  - _Check_: `plugins/ida-telegram/test/questions.test.ts` (`AC2: PreToolUse hook on AskUserQuestion fails fast on socket delivery error instead of claiming delivery`) asserts the process exits non-zero, outputs diagnostic error on stderr, and emits no false success block payload.

## Design

### 1. Dynamic Bot Resolution in Bridge Server

The Unix domain socket server created by `createBridgeServer` accepts `bot: TelegramBotClient | null | (() => TelegramBotClient | null)`. When handling `type: "ask_user"`, the bridge evaluates `const activeBot = typeof bot === "function" ? bot() : bot;`. This ensures that even if `bot` is instantiated or reconnected after the socket server begins listening, the bridge dispatches to the live client rather than capturing a stale `null` reference.

### 2. Confirmed Send Contract

Before returning `{ status: "ok" }` across the Unix domain socket or returning success in `executeTool("ask_user")`:

1. If `isMiniAppOnly` is false:
   - Check that `activeBot` is running and `defaultChatId` is configured;
   - Render the question card;
   - Await `activeBot.sendQuestionCard(defaultChatId, result.questionId, card, effectiveThreadId)`;
   - Verify that `sendRes?.ok` is true and `sendRes?.result?.message_id` exists;
   - If sending fails, return `{ status: "error", error: sendRes?.description || "Failed to deliver question card over Telegram", questionId: result.questionId }`.
2. Only return success if the question was either confirmed delivered to Telegram chat or explicitly routed to Mini App only.

### 3. Fail-Fast Hook Execution

In `hooks/ask-user-question.js`, `client.on("end")` parses the response and validates `res && res.status === "ok" && res.questionId`. If `res.status !== "ok"` or `res.error` is present:

- The hook writes the error to `process.stderr`;
- The hook exits 1 immediately;
- It never emits `Question ... posted to the user over Telegram` when delivery did not succeed.
