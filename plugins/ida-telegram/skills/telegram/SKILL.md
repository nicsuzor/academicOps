---
name: telegram
description: "Format, structure, and interaction rules for communicating with the user over Telegram. Use when a Telegram channel is attached or when processing Telegram messages, reactions, or commands. Not for other channels or general content composition."
---

# Telegram Replies

Mobile cognitive load is the binding constraint: the user reads on a phone between commitments.

Before building rich messages, Mini App Details, widgets, or inline reactions, read [references/formatting-and-widgets.md](references/formatting-and-widgets.md).

## Message Structure & Length Budget

- **Pre-reply setup**: Load this skill before the first reply. Pass `reply_to` when referencing messages more than 2--3 turns back, use local 24-hour time, and pair every identifier (task, PR, issue, commit, session, message ID) with a plain-language gloss and clickable URL when available.
- **Two-tier length budget (~100 words plain; up to ~4,000 chars formatted)**: Keep plain conversational replies under ~100 words.
  - Structured mobile-scannable replies (bold headline, `#` headings, bold lead-in bullets, `>!` expandable receipts, `||spoilers||`, tables, code blocks) may use up to `maxChatChars` (`4000`) so rich content stays whole; Markdown converts directly to native Telegram UTF-16 entities without escaping MarkdownV2.
  - Keep summaries functional (explain how each change fixes its target), send one major conclusion per message, and update existing messages via `edit_message` for late links or IDs.
- **Mini App Details (`detail` parameter)**: Keep essential takeaways in chat; put deep context, long logs, and code into `detail`. The Mini App renders `detail` as a phone-width Markdown page (`##` heading per topic, one idea per `-` bullet or short paragraph, bold lead phrases only). Never wrap the whole `detail` page in `>!` or `>`; reserve quotes for short receipts inside a section.
- **Delivery hygiene**: Deliver each item once on its designated bot without echoing other bots. For requests originating off-Telegram, suppress progress notices and send a 1--2 line completion summary.

## Questions, Action Buttons & Reactions

- **Inbound routing and async flow**: Route inbound knowledge lookups to the knowledge-base custodian, reserving code-dispatch pipelines for real code changes. Never wait or block on user answers -- proceed with other ready work or conclude the turn.
- **Decision markup**: Provide self-contained context, proportionate evidence (`detail`), and a first-listed `(Recommended)` choice. Pass `binary_decision: true` (`[✅]`/`[❌]`) only for binary yes/no proposals, `buttons` for multi-option choices, and neither for status or informational replies; use `mini_app_only: true` for non-urgent decisions.
- **Action buttons**: Replies include `[🧐 Check]` (`ida:premise-check` face-of-record verdict and appealable natural-language reasons, zero _de novo_ fact-checking), `[💡 Explain]` (expanded detail), `[🧾]` (verbatim Argdown argument chain nested by delegation depth in `detail`, marking unfound links `[Missing argument: ...]`), and `[🙏]` (`event: "thanks"`).
  - When the user taps `🙏`, they have read the message and finished its thread: call `close_thread` unless more on its topic is due soon, and send no reply (`Selected: 🙏 Thanks ✅`).
- **Reactions**: Inbound messages are marked `👀`. Treat `👎` as feedback on substance or the reported failure (investigate, fix, or replan directly without asking to reword); route `😡` to systemic diagnosis (`/learn`) and `🤔` to an immediate progress check; use reaction-only completion (`🫡`, `✍`, `🐳`) when no reply is owed.

## Threads, Media & Voice

- **Thread confinement and `list_threads`**: Inbound threaded messages tag `meta.message_thread_id`; outbound replies, edits, cards, voice notes, and reactions stay in that thread automatically.
  - Outside any thread, attach via `reply_to` rather than falling into an unopenable `# General` topic. Manage topics with `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, and `list_threads({ state?: "all" | "open" | "closed" })`.
  - Because Telegram's Bot API has no list-topics method, `list_threads` reflects only the plugin's own record (`unknown` state / `null` name means only a post was seen); read `note` before telling the user a thread is the only one open.
- **Media, voice, and bot commands**: Send media, albums, locations, drafts, and polls via dedicated send tools (see reference).
  - Resolve odd words in dictated voice notes as homophones in context (noting residual ambiguity); on `transcript_error` or synthesis failure, report the error verbatim and escalate without silent fallback.
  - For bare `meta.command`, invoke the matching skill (underscores become hyphens) on the replied-to message or active topic.
