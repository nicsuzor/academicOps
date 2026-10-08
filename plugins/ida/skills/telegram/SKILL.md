---
name: telegram
description: Reaction and format rules for replying to the user over a Telegram channel. Load once when a Telegram channel is attached, before the first reply, and keep the rules for the session. Adds formatting on top of the persona's "Briefing the user" rules; it does not replace them. Not for other channels or for composing the brief's content.
---

# Telegram replies

The persona's "Briefing the user" rules decide what a message says. These rules decide how it looks on a phone.

## Reactions

The reaction on each user message shows its state, so the user can see progress without opening a reply. A message holds one reaction; setting a new one replaces it.

- **React 👀 before anything else**, including hydration. It means read and thinking.
- **Move the reaction on as the state changes:**
  - ✍ captured: the dump, decision or fact is written to the PKB.
  - 👨‍💻 briefed and running in the background.
  - 🤔 a question back to the user is waiting in a reply.
  - 💔 failed or blocked; the reply names what refused.
  - 🎉 done and answered.
  - 🫡 done, and no reply is owed.
- **End on the reaction that fits the message, not only the done mark:** 🏆 the user reports finishing something hard; 🤝 a decision agreed; 💯 exactly right; 🔥 a strong idea; 🙏 thanks; 🤣 a joke; 🤯 surprising news; 😢 bad news. Vary them.
- **Acknowledge with a reaction, never a text.** A "got it" message is one more notification to read.
- **Telegram accepts only these reactions.** Send each string exactly as listed; several carry no emoji variation selector (`✍`, not `✍️`), and any other string is rejected:
  ❤ 👍 👎 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 💊 🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡

## Formatting

- **Bold one-line headline first**: the result, or the decision needed.
- **Evidence goes in an expandable blockquote** (`**>` … `||`), sent with `format: 'markdownv2'`, so the user opens it only if they want it. Escape MarkdownV2's reserved characters yourself, because the channel sends the text as written.
- **No `#` headings and no `|` tables.** MarkdownV2 and plain text render neither; they arrive as literal characters or get the send rejected. Use bold lines and bullets.
- **Keep each reply under 4096 characters.** Longer text is split into chunks, and a split can break a formatting span.
- **If a send fails, resend it as plain text** (`format: 'text'`) rather than retrying the same markup.
