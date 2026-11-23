# Telegram Buttons, Reactions, Details, and Tools Reference

Inline keyboard options, Mini App Details layout, action-button events, shared reaction legend, and topic/media tool contracts.

## Inline Keyboard & Quote Parameters

- `copy_text`: `{ label, copy_text }` inline buttons for one-tap clipboard copy of commands or identifiers.
- `quote_rich_texts`: pass quoted rich text fragments in `send_rich_message` (`reply_parameters.quote_rich_texts`).
- `show_caption_above_media` on media sends; `message_effect_id` on `send_rich_message` and `send_widget` when appropriate.
- `button_layout`, `buttons_per_row`, or 2D button arrays: compact multi-row option layouts on mobile.

## Mini App Details (`detail`) Layout

The Mini App renders `detail` as a phone-width Markdown page:

- Use a short `##` heading per topic, one idea per `-` bullet or short paragraph, and bold only for lead phrases.
- Use `-` bullets (never emoji or `!` as bullet markers).
- Never wrap the whole page or most of it in `>!` or `>`; reserve blockquotes only for short receipts inside a section.

## Message Action Button Events

Messages carrying action callback buttons (`logic_check`, `explain`, `reasons`, `thanks`, `accept_recommendation`, `decline_recommendation`) emit the corresponding channel events when tapped:

| Button | Event | Required Handling |
| - | - | - |
| `🧐 Check` | `logic_check` | Run formal `premise-check` on the face of the record (zero _de novo_ fact-checking); record and reply with verdict (`PASS`/`REVISE`/`FAIL`) and appealable natural-language administrative-law reasons via `verdict.py`. |
| `💡 Explain` | `explain` | Reply expanding that message with context, rationale, and evidence. |
| `🧾` | `reasons` | Place verbatim Argdown argument blocks in `detail` labelled by link (`lead to user`, `coordinator to lead`, `worker to coordinator`), marking missing links `[Missing argument: ...]`; summarize the chain in ~100 chat words. |
| `🙏` | `thanks` | Meta carries `target_message_id`, `chat_id`, `user_id`, optional `message_thread_id`. Call `close_thread` unless more on the topic is due soon; send no reply (`Selected: 🙏 Thanks ✅`). |
| `✅` / `❌` | `accept_recommendation` / `decline_recommendation` | Available when `binary_decision: true`. Execute/confirm on `✅`; halt declined course and clarify or offer alternatives on `❌`. |

## Shared Reaction Legend

Telegram validates reactions authoritatively against its `ReactionTypeEmoji` set (no bespoke plugin allowlist); unsupported emojis surface platform errors directly. Every persona and worker role shares one reaction per state:

| Emoji | State | Meaning |
| - | - | - |
| `👀` | Inbound | Message received and being assessed |
| `✍` | Captured | Note, decision, intake, or task persisted to knowledge base, or held solely for durable-fact capture |
| `🤓` | Dispatched (knowledge) | Held by knowledge-base custodian for non-capture knowledge work |
| `🗿` | Dispatched (compliance) | Held by compliance/rule reviewer |
| `👨‍💻` | Dispatched (supervision) | Held by execution supervisor or review arbitrator |
| `💅` | Dispatched (qualitative) | Held by qualitative excellence reviewer |
| `🤪` | Self-handled | Handled directly by the active session agent |
| `🐳` | Dispatched (background worker) | Briefed and dispatched to an isolated background worker |
| `👾` | Dispatched (in-session client) | Held by an interactive in-session client run |
| `👻` | Dispatched (synchronous container) | Held by a containerised synchronous run |
| `🕊` | Dispatched (subagent) | Handed off to a general-purpose subagent |
| `🤔` | Waiting | Question, choice, or clarification pending user reply in chat |
| `💔` | Blocked / failed | Execution halted or hit external blocker (reply details refusal) |
| `🎉` | Completed | Request resolved with substantive reply |
| `🫡` | Acknowledged | Handled or completed with no substantive reply owed |

Feedback reactions: `👎` (substance defect/reported failure), `👍` (affirmation), `🔥` (breakthrough), `🤝` (agreement), `💯` (aligned), `🏆` (milestone), `🙏` (appreciation), `🤣` (humor), `🤯` (surprising), `😢` (regret).

## Topic, Message, Media, and Review Tools

- **Topic tools**: `create_thread({ name })` (custom icons via `get_forum_topic_icon_stickers`; auto-activates the new thread), `rename_thread`, `close_thread`, `reopen_thread`, `unpin_all_thread_messages`, `delete_thread`, `list_threads({ state?: "all" | "open" | "closed" })`. Standard tools reject `message_thread_id: 1`; manage `#1` via `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, and `unpin_all_general_thread_messages`.
- **Message management**: `pin_message` (`disable_notification: true` by default), `unpin_message`, `unpin_all_messages`, `forward_messages` / `copy_messages` (1--100 messages per call), `delete_messages` (48-hour window), `edit_message_reply_markup` (`buttons: []` to clear).
- **Rich media, location, drafts & polls**: `send_photo`, `send_document`, `send_video`, `send_animation`, `send_audio`, `send_video_note` (local path, `file_id`, or URL; optional `caption`, `has_spoiler`, `buttons`), `send_media_group` (2--10 items), `send_location`, `send_venue`, `send_contact`, `send_dice` (`🎲`, `🎯`, `🏀`, `⚽`, `🎳`, `🎰`), `send_chat_action`, `send_message_draft` (non-zero `draft_id`, Rich drafts in private chats), `send_poll` (2--12 options, optional `type: "quiz"` + `correct_option_id` + `explanation`) / `stop_poll`. Use `ask_user` when selection must resume the agent turn.
- **Reviews & focus**: Attach diff review metadata when presenting a PR or branch; update the live cognitive anchor when primary focus shifts or work is delegated.
