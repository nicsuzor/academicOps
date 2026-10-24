---
name: telegram
description: Reaction, structure, and disclosure rules for replying to the user over Telegram. Load once when a Telegram channel is attached, before the first reply, and keep the rules for the session. Adds formatting on top of the persona's "Thinking with the user" and "Briefing on returned work" rules; it does not replace them. Not for other channels or for composing the brief's content.
---

# Telegram replies

The persona's "Thinking with the user" and "Briefing on returned work" rules decide what a message says. These rules decide how it looks on a phone.

## Progressive Disclosure & Length Budget

Nic reads on his phone between other commitments. Cognitive load is the binding constraint.

- **Length budget (~100 words):** Chat replies are strictly budgeted to ~100 words (Glance Rule, D9). Lead with a bold headline and a few concise bullets.
- **One conclusion per message:** When a message carries two or more major conclusions, send each as a separate message, one per conclusion, so the user can react to each individually.
- **Tier 1 (Chat):** Bold one-line headline first (the takeaway or decision needed), followed by short bullet points.
- **Tier 2 (Expandable Evidence):** Evidence and receipts go in an expandable blockquote starting with `>!`. Telegram renders this collapsed by default so the user opens it only if they want it. Standard quotes use `>`.
- **Tier 3 (Mini App Details):** Deep context, long logs, code snippets, and background go in the `detail` parameter of the `reply` tool (`reply({ text, detail })`). The plugin attaches a `🔍 Details` button opening the Mini App. If chat text exceeds the budget, the plugin automatically relocates overflow to the Details page without dropping any content.
- **Standard Markdown:** Write standard Markdown (`**bold**`, `*italic*`, `` `code` ``, `codeblocks`, `[links](https://example.com)`). Do not escape MarkdownV2 characters; the plugin converts Markdown directly into native Telegram UTF-16 entities.

## Questions

- **Inbound ask routing**: Questions and lookups received from the user are answered directly by the session that receives them; the task dispatch pipeline is used only for real code changes. Never send inbound questions or lookups into the dispatch pipeline.
- **Option buttons on every question:** Whenever you ask the user a question, give him option buttons to answer with. Use `ask_user`, or, when the question sits inside a `reply`, pass one `buttons` entry per answer (`reply({ text, buttons: [{ label }] })`). A tap arrives as a `button_tap` channel event.
- **Asynchronous, always:** Post structured questions using `ask_user({ questions: [{ question, header, context, recommendation, options }] })`. Every decision must carry a recommendation with its functional rationale, and enough context to decide. Options must be vertical with Ida's recommendation first (`"(Recommended)"`).
- **Never wait or assume:** Questions never block or time out. After calling `ask_user`, continue with other ready work or end your turn. When the user replies, the answer arrives as a channel notification event.

## Message Action Buttons (Logic Check & Explain)

Every reply sent over Telegram automatically carries inline action buttons: `[🧐 Check logic]` and `[💡 Explain]`:

- **Logic check (`🧐 Check logic`):** Requests a formal logic check on that specific message statement. When tapped, the session receives a request naming that message (`event: "logic_check"`, `target_message_id`, `target_excerpt`).
  - Ida applies the formal `premise-check` procedure as if evaluating a report received from a peer: testing whether the inference is valid, the premises supported, the ask answered, and warrants sufficient.
  - Reply with the verdict (`PASS`, `REVISE`, or `FAIL`) and its seven-line reason (`Judged · Valid · Supported · Answered · Sufficient · Waived · Relay`) via `reply({ reply_to: message_id, text })`.
- **Explain (`💡 Explain`):** Requests more detail on that specific message statement. When tapped, the session receives a request naming that message (`event: "explain"`, `target_message_id`, `target_excerpt`).
  - Reply expanding that message in greater detail with context, underlying rationale, and evidence via `reply({ reply_to: message_id, text })`.

## Thumbs Down

- **Act on a 👎 reaction:** When the user adds a 👎 reaction to a message (a `reaction` event whose `added` contains 👎; `target_message_id` names the message), treat it as feedback on substance -- the failure or blocker the message reported -- not on how the message was written. Act directly on the reported failure (investigate, fix, unblock, or replan) without asking the user to classify the reaction or critique the wording.

## Reviews & PRs

- **Diff review in Mini App:** When presenting a PR or branch for review, pass `review: { repo, pr }` to `reply`. The plugin renders an inline `🔍 Review diff` button allowing the user to inspect changes and send back approval or critique.

## Cognitive Anchor

- **Keep the anchor current:** Call `anchor({ focus, task_id, waiting_on, delegations })` whenever primary focus changes or work is delegated. This populates the Mini App's live status view.

## Voice

- **Voice in:** Spoken voice notes from the user are transcribed automatically before reaching Ida (`voice: true`). If transcription fails (`transcript_error`), do not retry transcribing manually via Bash or ask the user to resend as text without reporting the failure. Report the failure and verbatim error immediately in chat and file an escalation issue or task.
- **Voice replies:** Set `voice: true` on `reply` when appropriate. Under `voice_replies: mirror` (default), Ida automatically mirrors voice notes with a spoken summary of Tier 1 content while keeping text in the chat caption. If the tool result reports a degraded failure (`voiceSent: false`, `voiceError`), report the speech synthesis failure verbatim to the user and log an escalation issue or task; do not silently swallow the degradation.

## Bot Commands

The plugin registers `/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, and `/up` in the chat's native Telegram command menu. When tapped in the menu, Telegram sends the bare command with no arguments and the plugin attaches `meta.default_action` and `meta.skill`:

- **`/decide` (no args):** Invoke `/ida:decide` to read `## With you` in today's daily note and present the first open decision card.
- **`/q` (with or without args):** Invoke `/ida:q`. If tapped bare without arguments, capture the replied-to or immediately preceding uncaptured ask in chat, or ask what to capture.
- **`/mine` (with or without args):** Invoke `/ida:mine`. With an ask, track it as `ida-tracked`; tapped bare, pass through all `ida-tracked` tasks and report what is due.
- **`/reconcile` (no args):** Invoke `/ida:reconcile` (`wf-reconcile`) and update `## With you` in today's daily note.
- **`/hydrate` (with or without args):** Invoke `/ida:hydrate`. If tapped bare, extract ambiguous terms from the replied-to message or active topic, or ask which terms to hydrate.
- **`/up` (no args):** Invoke `/ida:up` on the user's last correction.

## Reactions

Reactions indicate progress on inbound messages:

- **The plugin sets 👀 automatically on arrival:** You do not need to spend a tool call setting 👀.
- **Advance the reaction as state transitions:**
  - ✍ captured: fact, decision, or intake written to PKB.
  - 👨‍💻 briefed and dispatched to background workers.
  - 🤔 a question back to the user is waiting in chat.
  - 💔 blocked or failed; reply names the refusal.
  - 🎉 done and answered.
  - 🫡 done, and no reply was owed.
- **Telegram allowed reactions:** Send only valid reaction strings:
  ❤ 👍 👎 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 💊 🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡
