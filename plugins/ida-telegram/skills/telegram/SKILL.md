---
name: telegram
description: "Format, select surfaces for, and manage Telegram interactions (messages, Rich Messages, HTML Widgets, interactive decisions, reactions, threads, media, voice, commands). Exclude for non-Telegram channels or general prose."
---

# Telegram Interface Guide

Mobile cognitive load is the binding constraint: users read on a phone between commitments. Load this skill before your first reply and pick the native Bot API surface matching the message purpose.

**Load references on demand before authoring:**

- [references/formatting-and-widgets.md](references/formatting-and-widgets.md) -- rich formatting, Mini App `detail`, widgets, inline reactions.
- [references/rich-messages.md](references/rich-messages.md) -- headings, `<table bordered striped compact>`, `<aside>`, math, `<tg-map>`, `tg://<type>?id=...` `media`, `<tg-thinking>` drafts.
- [references/widgets.md](references/widgets.md) -- Live Status trackers and custom HTML Widgets (`send_widget`, `edit_message_widget_data`, `answer_widget_query`).

## Message-Kind Selection Matrix

| Message Kind | Surface & Tool | Key Rules |
| :- | :- | :- |
| Casual / Ack (`1–3` lines) | `send_rich_message` or reaction-only | Short Rich Markdown; react only (`🫡`, `✍`, `🐳`, `🎉`) when no prose is needed. |
| Streaming Draft (private) | `send_message_draft` | Reuse non-zero `draft_id`; pass `markdown`/`html`/`blocks` (`<tg-thinking>`, `can_stop: true`). Private chats only; finalize via `send_rich_message`. |
| Answer / Analysis / Report | `send_rich_message` | Headline → bullets/tables → `<details>` receipts → `<footer>`. One major conclusion per message. |
| Question / Decision (private) | `ask_user` (Widget default) | Option cards (`kind: "decision"`, `stakes`, `recommended`/`pros`/`cons`, `allow_defer`). Set `mini_app_only: true` if non-urgent. Async only. |
| Question / Decision (`chat_id < 0`) | `ask_user` (`presentation: "rich"`) | Groups forbid widgets; pass `presentation: "rich"`, or `send_poll` for simple tallies without broker resumption. |
| Live Multi-Step Status | `send_widget` + `edit_message_widget_data` | Send compact Profile-1 HTML once; stream `chat_data` (`<= 1,024 B`). Never spam follow-up status messages. |
| Correction / Late Links | `edit_message` | Patch existing `markdown`/`html`/`blocks` to append PRs, branches, IDs, or outcomes instead of reposting. |

## Rich Answer Skeleton

Pass to `send_rich_message({ markdown, feedback_buttons?, buttons? })` (include `reply_to` and `quote_rich_texts` when replying > 2–3 turns back):

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

## Presentation, Length & Delivery Rules

- **Length & formatting:** Keep casual replies concise (`<= ~100` words). Structured reports on `send_rich_message` may use up to `32,768` characters, collapsing long receipts into `<details>`. Write functional summaries (how each change fixes its target) with zero prose walls.
- **Mini App `detail` (`ask_user`):** Keep takeaways in chat; put deep context, long logs, and code in `detail` (rendered as phone-width Markdown: `##` per topic, one idea per `-` bullet or short paragraph, bold lead phrases only). Never wrap the entire `detail` page in `>!` or `>`--reserve quotes for short section receipts.
- **Identifiers, time & anchoring:** Gloss every task, PR, issue, commit, session, or message ID in plain language with a clickable URL when available. Use local 24-hour `HH:MM` time. Pass `reply_to` when referencing messages > 2–3 turns back or replying outside a forum thread.
- **Routing & multi-bot hygiene:** Deliver once on the designated bot without echoing others. For off-Telegram requests, suppress progress updates and send only a 1–2 line completion summary. Route knowledge lookups to the knowledge custodian, reserving task/code dispatch for execution work. Never block or assume user answers--continue other ready work or end the turn until broker resumption wakes you.

## Decisions, Buttons & Widget Queries

- **Self-contained decisions:** Present one decision per message with a 2-line context summary, reasoned recommendation first (`recommended: true` / `(Recommended)`), and proportionate `pros`/`cons`/`detail`.
- **Inline buttons:** Pass `buttons` (`{ label, callback_data | copy_text }`, 2D arrays / `button_layout` / `buttons_per_row`) or `<tg-button-row>` on `send_rich_message` for inline actions, and neither for plain notices.
- **Action button events:**
  - `🧐 Check` (`logic_check`): Run `premise-check` on that message; reply `PASS`/`REVISE`/`FAIL` + reason.
  - `💡 Explain` (`explain`): Expand rationale and supporting evidence.
  - `🧾` (`reasons`): Reply with a concise summary + verbatim Chained Toulmin Argdown per delegation link in `detail` (name missing links explicitly).
  - `🙏` (`thanks`): Card updates automatically; end discussion or `close_thread` silently unless more on that topic is imminent.
  - `✅` / `❌` (`accept_recommendation` / `decline_recommendation`): Execute accepted path, or pause and offer alternatives.
- **Widget queries:** `ask_user` widgets settle via the broker; custom `send_widget` flows (`allow_queries: true`) emit `widget_query` and require `answer_widget_query` within `15 s`.

## Reactions

- **Handling:** Inbound messages auto-mark `👀`. Use reaction-only completion (`🫡`, `✍`, `🐳`) when no reply is owed. On `👎`, investigate, fix, or replan reported substance/blockers directly without asking the user to reword or classify; route `😡` to systemic diagnosis (`/learn`) and `🤔` to an immediate progress check.
- **Shared legend (one meaning each; Telegram-validated):**
  - _Lifecycle:_ `👀` reading | `✍` saved to KB | `🐳` worker dispatched | `🕊` subagent dispatched | `🤔` awaiting user | `💔` blocked/failed | `🎉` completed with reply | `🫡` handled silently
  - _Feedback:_ `👎` substance defect | `👍` affirm | `🔥` breakthrough | `🤝` agree | `💯` aligned | `🏆` milestone | `🙏` thanks | `🤣` humor | `🤯` surprising | `😢` regret

## Threads, Media, Voice & Commands

- **Threads:** Inbound `meta.message_thread_id` confines outbound replies, edits, cards, voice, and reactions automatically; pass `message_thread_id` to post elsewhere, or `reply_to` when unthreaded (avoiding unopenable `# General`). Manage topics via `list_threads({ state?: "all" | "open" | "closed" })`, `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, and General `#1` tools (`edit_general_thread`, etc.); update cognitive anchors when focus shifts. Because Telegram lacks a list-topics API, `list_threads` reflects plugin-seen state only (`unknown` / `null` name = only a post observed)--check `note` before claiming a thread is the only open one.
- **Message ops & media:** Ops: `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages` (`<= 48h`), `edit_message_reply_markup`. Standalone sends: `send_photo`, `send_document`, `send_video`, `send_animation`, `send_audio`, `send_video_note`, `send_media_group` (`2–10`), `send_location`, `send_venue`, `send_contact`, `send_dice`, `send_chat_action`, `send_poll`, `stop_poll`. Prefer `send_rich_message` with `media` URIs when text and visuals belong together.
- **Voice:** Resolve dictated homophones in context (noting residual ambiguity). On `transcript_error` or TTS failure, report the error verbatim and escalate immediately without silent fallback. Mirror voice via `voice: true` / `VOICE_REPLIES=mirror` (`send_rich_message`).
- **Bot commands:** Bare `meta.command` (underscores → hyphens) invokes the matching skill on the replied-to message or active topic (or asks what to target), forwarding `meta.args` if present.
