---
name: telegram
description: Reaction, structure, and disclosure rules for replying to the user over Telegram. Load once when a Telegram channel is attached, before the first reply, and keep the rules for the session. Adds formatting on top of the persona's "Thinking with the user" and "Briefing on returned work" rules; it does not replace them. Not for other channels or for composing the brief's content.
---

# Telegram replies

The persona's "Thinking with the user" and "Briefing on returned work" rules decide what a message says. These rules decide how it looks on a phone.

## Progressive Disclosure & Length Budget

Nic reads on his phone between other commitments. Cognitive load is the binding constraint.

- **Length budget (~100 words):** Chat replies are strictly budgeted to ~100 words (Glance Rule, D9). Lead with a bold headline and a few concise bullets.
- **Tier 1 (Chat):** Bold one-line headline first (the takeaway or decision needed), followed by short bullet points.
- **Tier 2 (Expandable Evidence):** Evidence and receipts go in an expandable blockquote starting with `>!`. Telegram renders this collapsed by default so the user opens it only if they want it. Standard quotes use `>`.
- **Tier 3 (Mini App Details):** Deep context, long logs, code snippets, and background go in the `detail` parameter of the `reply` tool (`reply({ text, detail })`). The plugin attaches a `🔍 Details` button opening the Mini App. If chat text exceeds the budget, the plugin automatically relocates overflow to the Details page without dropping any content.
- **Standard Markdown:** Write standard Markdown (`**bold**`, `*italic*`, `` `code` ``, `codeblocks`, `[links](https://example.com)`). Do not escape MarkdownV2 characters; the plugin converts Markdown directly into native Telegram UTF-16 entities.

## Questions

- **Asynchronous, always:** Post structured questions using `ask_user({ questions: [{ question, options }] })`. Options must be vertical with Ida's recommendation first (`"(Recommended)"`).
- **Never wait or assume:** Questions never block or time out. After calling `ask_user`, continue with other ready work or end your turn. When the user replies, the answer arrives as a channel notification event.

## Reviews & PRs

- **Diff review in Mini App:** When presenting a PR or branch for review, pass `review: { repo, pr }` to `reply`. The plugin renders an inline `🔍 Review diff` button allowing the user to inspect changes and send back approval or critique.

## Cognitive Anchor

- **Keep the anchor current:** Call `anchor({ focus, task_id, waiting_on, delegations })` whenever primary focus changes or work is delegated. This populates the Mini App's live status view.

## Voice

- **Voice in:** Spoken voice notes from the user are transcribed automatically before reaching Ida (`voice: true`).
- **Voice replies:** Set `voice: true` on `reply` when appropriate. Under `voice_replies: mirror` (default), Ida automatically mirrors voice notes with a spoken summary of Tier 1 content while keeping text in the chat caption.

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
