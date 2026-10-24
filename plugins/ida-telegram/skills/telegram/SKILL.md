---
name: telegram
description: "Format, structure, and interaction rules for communicating with the user over Telegram. Use when a Telegram channel is attached or when processing Telegram messages, reactions, or commands. Not for other channels or for general content composition."
---

# Telegram replies

Core interaction rules determine message content; these rules govern presentation and interaction over Telegram.

## Progressive Disclosure & Length Budget

The user reads on a phone between other commitments. Cognitive load is the binding constraint.

- **Length budget (~100 words):** Keep chat replies strictly budgeted to ~100 words. Lead with a bold headline and concise bullets.
- **Tier 1 (Chat):** Lead with a bold one-line headline stating the takeaway or decision needed, followed by concise bullet points.
- **Tier 2 (Expandable evidence):** Place receipts, quotes, and evidence in expandable blockquotes (`>!`). Telegram renders these collapsed by default so the user opens them on demand. Use standard blockquotes (`>`) for ordinary quotes.
- **Tier 3 (Details page):** Place deep context, long logs, code snippets, and background into details or extended properties rather than inline chat text. If chat text exceeds the budget, overflow relocates to details automatically without losing content.
- **Standard Markdown:** Write standard Markdown (`**bold**`, `*italic*`, `` `code` ``, code blocks, `[links](https://example.com)`). Do not escape MarkdownV2 characters; formatting converts directly to native Telegram entities.

## Questions

- **Option buttons on questions:** Provide selectable option buttons whenever asking questions so the user can reply with a single tap.
- **Asynchronous by default:** Post questions with structured options, placing the recommended choice first (`"(Recommended)"`).
- **Never wait or block:** Questions never block or time out. Proceed with other ready work or conclude the turn; answers arrive asynchronously as channel events.

## Reactions & Feedback

- **Act on negative feedback:** When the user reacts with 👎 to a message, prompt for clarification (e.g. `Too verbose`, `Wrong premise`, `Poor logic`, `Say why`) and route the critique to the learning or diagnostic workflow.
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

## Voice

- **Inbound voice:** Spoken voice notes from the user are transcribed automatically before reaching the agent.
- **Voice replies:** Mirror voice input with spoken audio replies for primary takeaways when voice response mode is enabled, keeping text captions in chat.

## Bot Commands

- **Bare commands:** When a native Telegram menu command arrives without arguments, follow the default action or skill specified in the event metadata (`meta.default_action` or `meta.skill`).
- **Commands with arguments:** When user arguments are provided with a command, process them within the target workflow.
