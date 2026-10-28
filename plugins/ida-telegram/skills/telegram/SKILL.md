---
name: telegram
description: "Format, structure, and interaction rules for communicating with the user over Telegram. Use when a Telegram channel is attached or when processing Telegram messages, reactions, or commands. Not for other channels or for general content composition."
---

# Telegram replies

Core interaction rules determine message content; these rules govern presentation and interaction over Telegram.

## Progressive Disclosure & Length Budget

The user reads on a phone between other commitments. Cognitive load is the binding constraint.

- **Length budget (~100 words):** Keep chat replies strictly budgeted to ~100 words unless detail was requested. Lead with a bold headline and concise bullets. A summary is functional, not a length cap: a summary of a plan or proposal explains how the plan fixes each problem (the mechanism), using Tier 2 and Tier 3 to carry depth without dropping the mechanism.
- **One conclusion per message:** When a message carries two or more major conclusions, send each as a separate message, one per conclusion, so the user can react to each individually.
- **Tier 1 (Chat):** Lead with a bold one-line headline stating the takeaway or decision needed, followed by concise bullet points.
- **Tier 2 (Expandable evidence):** Place receipts, quotes, and evidence in expandable blockquotes (`>!`). Telegram renders these collapsed by default so the user opens them on demand. Use standard blockquotes (`>`) for ordinary quotes.
- **Tier 3 (Details page):** Place deep context, long logs, code snippets, and background into details or extended properties (e.g. `detail` parameter of `reply` or `ask_user` questions) rather than inline chat text. If chat text exceeds the budget, overflow relocates to details automatically without losing content.
- **Standard Markdown:** Write standard Markdown (`**bold**`, `*italic*`, `` `code` ``, code blocks, `[links](https://example.com)`). Do not escape MarkdownV2 characters; formatting converts directly to native Telegram entities.

## Questions

- **Inbound ask routing:** Questions and lookups received from the user are answered in the receiving session through an internal subagent it spawns, never in its main context; the task dispatch pipeline is used only for real code changes. Never send inbound questions or lookups into the dispatch pipeline.
- **Option buttons on questions:** Provide selectable option buttons whenever asking questions so the user can reply with a single tap. Use multi-row layouts (`button_layout`, `buttons_per_row`, or 2D button arrays) when offering multiple options (such as skill or checklist proposals) to keep choices compact on mobile screens.
- **Predefined row consolidation:** Pass `predefined_row: true` on `reply` to consolidate all active system actions (`🔍 Details`, `[🧐 Check logic]`, `[💡 Explain]`) onto a single default header row above custom option buttons.
- **Mini App-only questions:** To keep chat clear of decisions best reviewed in the dashboard, set `mini_app_only: true` (or `chat: false`) on `ask_user` or individual questions. The question appears interactively in the Mini App without posting a card to chat.
- **Fuller background behind Details:** Provide deep context, evidence, logs, or detailed tradeoffs in the `detail` parameter of a question. The Mini App displays a `🔍 Details` button on the question card that opens this fuller background on demand, keeping the card compact.
- **Asynchronous by default:** Post questions with structured options, placing the recommended choice first (`"(Recommended)"`). When no recommendation is available, offer to have one assessed.
- **Remove answered questions from outstanding list:** Once a question you asked has been answered in your session or resolved outside channel events, remove that question from the Mini App's outstanding list immediately using `close_question({ question_id, reason })` or `answer_question({ question_id, choice })`. (Questions answered via Telegram cards or the Mini App are dismissed automatically by the broker.) Never leave settled questions pending in the user's outstanding list.
- **Never wait or block:** Questions never block or time out. Proceed with other ready work or conclude the turn; answers arrive asynchronously as channel events.

## Message Action Buttons (Logic Check & Explain)

Every reply sent over Telegram automatically carries inline action buttons: `[🧐 Check logic]` and `[💡 Explain]`:

- **Logic check (`🧐 Check logic`):** Requests a formal logic check on that specific message statement (`event: "logic_check"`).
  - Apply the formal premise-check procedure: test whether the inference is valid, the premises supported, the ask answered, and warrants sufficient.
  - Reply with the verdict (`PASS`, `REVISE`, or `FAIL`) and its reason (`Judged · Valid · Supported · Answered · Sufficient · Waived · Relay`).
- **Explain (`💡 Explain`):** Requests more detail on that specific message statement (`event: "explain"`).
  - Reply expanding that message in greater detail with context, underlying rationale, and evidence.

## Reactions & Feedback

- **Act on a 👎 reaction:** When the user adds a 👎 reaction to a message (a `reaction` event whose `added` contains 👎), treat it as feedback on substance -- the failure or blocker the message reported -- not on how the message was written. Act directly on the reported failure (investigate, fix, unblock, or replan) without asking the user to classify the reaction or critique the wording.
- **Inbound message status:** The channel marks inbound messages with 👀 upon arrival. Advance reactions as state transitions:
  - ✍ captured: note, decision, or intake recorded.
  - 👨‍💻 dispatched: briefed and dispatched to background workers.
  - 🤔 waiting: a question or clarification is pending in chat.
  - 💔 blocked: execution failed or hit a blocker; reply details the issue.
  - 🎉 completed: task answered or resolved.
  - 🫡 acknowledged: completed when no reply was owed.
- **Allowed reactions:** Send only valid Telegram reaction strings:
  ❤ 👍 👎 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 💊 🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡

## Reviews & State Tracking

- **Diff reviews:** Attach review metadata when presenting a pull request or branch for review, allowing the user to inspect changes and submit approval or critique directly.
- **Cognitive anchor:** Update the live cognitive anchor whenever primary focus changes or work is delegated, keeping the status view current.

## Threaded Conversations

- **Thread confinement by default:** In Telegram supergroups with forum topics enabled, messages arriving in a thread are tagged with `meta.message_thread_id` and `meta.thread_id`. All outbound paths (replies, voice notes, question cards, edits, and reactions) automatically stay in that thread without configuration.
- **Explicit target overriding:** If work requires posting into a specific topic, pass `message_thread_id` (or `thread_id`) explicitly to `reply` or `ask_user`.

## Voice

- **Inbound voice:** Spoken voice notes from the user are transcribed automatically before reaching the agent. If transcription fails (`transcript_error`), report the failure and error immediately in chat and log an escalation; do not retry manually via Bash or silently drop it.
- **Voice replies:** Mirror voice input with spoken audio replies for primary takeaways when voice response mode is enabled, keeping text captions in chat. If speech synthesis fails, report the failure verbatim and log an escalation rather than silently swallowing the degradation.

## Bot Commands

- **Bare commands:** When a native Telegram menu command arrives without arguments, follow the default action or skill specified in the event metadata (`meta.default_action` or `meta.skill`).
- **Commands with arguments:** When user arguments are provided with a command, process them within the target workflow.
