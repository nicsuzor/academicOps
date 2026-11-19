---
name: telegram
description: "Format, select interfaces for, and manage interactions with the user over Telegram. Use when a Telegram channel is attached or handling Telegram messages, Rich Messages, HTML Widgets, interactive questions/decisions, reactions, or commands. Exclude for non-Telegram channels or general prose composition."
---

# Telegram Interface Guide

Choose the native Bot API surface matching message purpose before sending. Load this skill before the first reply.

## Message-Kind Selection Matrix

| Message Kind | Primary Tool & Surface | Rules |
| :- | :- | :- |
| Casual / Ack (`1-3` lines) | `reply` or reaction-only | Plain Markdown (`reply`); use reaction-only (`🫡`, `✍`, `🐳`, `🎉`) when no prose is needed. |
| Streaming Draft (private chat) | `send_message_draft` | Consistent non-zero `draft_id`; pass `markdown`/`html`/`blocks` (`<tg-thinking>`, `can_stop: true`). Private chats only; finalize with `send_rich_message`. |
| Answer, Explanation, Analysis, Report | `send_rich_message` | Headline -> scannable bullets / native tables -> `<details>` collapsed receipts -> `<footer>`. One major conclusion per message; never use `reply` markup hacks. |
| Question or Decision (private chat) | `ask_user` (HTML Widget default) | Option cards with optional `kind: "decision"`, `stakes`, option `recommended`/`pros`/`cons`, `allow_defer`. Set `mini_app_only: true` for non-urgent queues. Async only. |
| Question / Decision in Group (`chat_id < 0`) | `ask_user` (`presentation: "rich"`) | Groups forbid widgets; pass `presentation: "rich"` explicitly or use `send_poll` for simple group tallies without broker resumption. |
| Live Multi-Step Status / Progress | `send_widget` + `edit_message_widget_data` | Send compact Profile-1 status HTML once; stream state silently via `chat_data` (`<= 1,024 B`). Never spam follow-up status messages. |
| In-place Correction / Appending Links | `edit_message` | Patch existing messages (`text` or `markdown`/`html`/`blocks`) to append PR links, branch names, or outcomes instead of reposting. |

## Rich Answer Median Skeleton

Use this structure on `send_rich_message({ markdown, feedback_buttons?, buttons? })` (pass `reply_to` and `quote_rich_texts` when replying > 2-3 turns back):

```markdown
**Headline: bottom-line takeaway**

Concise 1-2 line context or direct answer.

- **Key point:** Evidence or mechanism
- **Next:** Concrete action or open check

<details>
  <summary>Evidence &amp; receipts</summary>
  Verbatim quotes, command outputs, or checks.
</details>

<footer>Scope</footer>
```

- **Reference loading:** If composing Rich Messages with headings, native `<table bordered striped compact>`, `<aside>`, math, `<tg-map>`, `tg://<type>?id=...` `media`, or `<tg-thinking>` drafts, read [references/rich-messages.md](references/rich-messages.md) before sending.
- **Widget loading:** If authoring or updating a Live Status tracker or custom HTML Widget via `send_widget`, `edit_message_widget_data`, or `answer_widget_query`, read [references/widgets.md](references/widgets.md) before writing HTML.

## Core Presentation & Delivery Invariants

- **Mobile scan budget:** Plain `reply` stays <= ~100 words. Structured Rich reports keep takeaway whole in chat with collapsed `<details>` for receipts and `detail` (on `reply`/`ask_user`) reserved for deep logs or background context. Avoid unformatted walls of prose.
- **No bare identifiers:** Gloss every task, PR, issue, commit, session, or message ID in plain language with a clickable URL where available.
- **Local 24-hour time:** Express all timestamps and schedules in local 24-hour `HH:MM` format.
- **Multi-bot & cross-channel discipline:** Deliver each item once on its designated bot; suppress Telegram progress notices for non-Telegram requests until sending a concise 1-2 line completion note.
- **Self-contained decisions:** Present one decision per message with a two-line context summary, reasoned recommendation first (`recommended: true`), and proportionate evidence (`pros`/`cons`/`detail`). Never block or assume answers; broker notifications wake continuation turns.
- **Inbound ask routing:** Route user knowledge questions and lookups to the knowledge custodian, reserving task dispatch strictly for code or execution work.

## Interactive Buttons, Actions & `reply` Markup

- **`ask_user` vs `reply` decisions:** Use `ask_user` for structured single/multi-select decisions and clarifications (widget in private chats, `presentation: "rich"` in groups). On `reply`, pass `binary_decision: true` ONLY for binary yes/no proposals (attaching `[✅]`/`[❌]`), labelled `buttons` (`{ label, callback_data }` or `{ label, copy_text }`, using 2D arrays/`button_layout`/`buttons_per_row`) for inline action rows, or neither for plain notices. Pass `predefined_row: true` to consolidate `🔍`, `[🧐 Check]`, `[💡 Explain]`, `[🧾]`, and `[🙏]` onto row 1.
- **Message action buttons (`reply` & Rich Messages with `buttons`):**
  - `🧐 Check` (`event: "logic_check"`): Run formal `premise-check` on that message and reply with `PASS`/`REVISE`/`FAIL` plus verdict reason.
  - `💡 Explain` (`event: "explain"`): Expand that message with rationale and supporting evidence.
  - `🧾` (`event: "reasons"`): Reply with concise summary + full verbatim Chained Toulmin Argdown blocks per delegation link in `detail` (name missing links explicitly).
  - `🙏` (`event: "thanks"`): Card updates automatically; close the thread (`close_thread`) with no reply unless more on its topic is due soon.
  - `✅` / `❌` (`accept_recommendation` / `decline_recommendation` when `binary_decision: true`): Act on accepted path or pause and offer alternatives when declined.
- **Widget queries (`widget_query`):** Question widgets settle automatically via the broker; custom `send_widget` flows with `allow_queries: true` emit `widget_query` and require explicit `answer_widget_query` within `15 s`.

## Reactions & Shared Legend

- **Semantic feedback:** Treat `👎` as feedback on reported substance/blockers and act directly to investigate or fix without asking the user to classify it; route `😡` to systemic diagnosis (`/learn`) and `🤔` to status investigation. Use reaction-only completion (`🫡`, `✍`, `🐳`) when no reply is needed. Inbound messages get `👀` on arrival.
- **Shared reaction legend (one meaning per reaction; Telegram validates):**
  - _Lifecycle:_ `👀` inbound/reading | `✍` captured to knowledge base | `🐳` dispatched worker | `🕊` dispatched subagent | `🤔` waiting on user reply | `💔` blocked/failed | `🎉` completed with reply | `🫡` handled silently
  - _Feedback:_ `👎` substance defect | `👍` affirmation | `🔥` breakthrough | `🤝` agreement | `💯` aligned | `🏆` milestone | `🙏` appreciation | `🤣` humor | `🤯` surprising | `😢` regret

## Threads, Media, Voice & Commands

- **Threads:** Messages stay confined to the active forum thread automatically; unthreaded chats anchor via `reply_to`. Pass `message_thread_id` to target elsewhere, or manage topics with `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, and General `#1` tools (`edit_general_thread`, etc.). Update the cognitive anchor on focus/delegation shifts.
- **Message ops & standalone media:** `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages` (<= 48h), `edit_message_reply_markup`. Standalone attachments: `send_photo`, `send_document`, `send_video`, `send_animation`, `send_audio`, `send_video_note`, `send_media_group` (2-10 items), `send_location`, `send_venue`, `send_contact`, `send_dice`, `send_chat_action`, `send_poll`, `stop_poll`. Prefer `send_rich_message` with `media` URIs when text and visual artifacts belong together.
- **Voice:** Resolve dictated homophones in context. If `transcript_error` or TTS synthesis fails, report verbatim immediately without silent fallback. Mirror voice with `voice: true` / `VOICE_REPLIES=mirror` (`reply` and `send_rich_message`).
- **Bot commands:** On bare `meta.command` (underscores map to hyphens), invoke that skill on the replied-to message, active topic, or ask what to target; pass `meta.args` when present.
