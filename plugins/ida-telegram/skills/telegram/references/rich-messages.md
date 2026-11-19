# Telegram Rich Messages Reference (Bot API 10.1-10.3)

Use `send_rich_message`, `send_message_draft` (private chats), and `edit_message` with mutually exclusive `markdown`, `html`, or `blocks` (`<= 32,768` characters, `<= 500` blocks).

## Format Selection & Constraints

- Provide **exact exclusivity**: supply exactly one of `markdown`, `html`, or `blocks`. Mixing formats or combining `text` with `markdown`/`html`/`blocks` on `edit_message` or `send_message_draft` rejects locally.
- Rich formatting compiles natively on Telegram's renderer: write standard Markdown or Rich HTML directly; never manually escape MarkdownV2 punctuation.
- Media attachments (`media`): up to `50` items (`{ id, type, file, mime_type?, duration?, performer?, title?, width?, height?, has_spoiler?, supports_streaming?, disable_content_type_detection? }`). Every `id` matches `[A-Za-z0-9_-]{1,64}` and is unique. Local filesystem `file` paths upload transparently over multipart `FormData`; HTTPS URLs and Telegram `file_id` pass by reference. Allowed `type` values: `photo`, `video`, `audio`, `document`, `animation`, `voice` / `voice_note` (normalized to `voice_note`).
- `quote_rich_texts`: pass exact quoted snippets from a target Rich Message under `reply_parameters.quote_rich_texts` when replying to a specific passage.
- `voice: true` (or `VOICE_REPLIES=mirror` after an inbound voice turn): synthesizes spoken audio from extracted prose (stripping collapsed `<details>` content) alongside the Rich Message.

## Rich Markdown & HTML Tag Catalog

| Feature | Markdown Form | HTML Form | Notes |
| :- | :- | :- | :- |
| Headings | `# Title` .. `###### Title` | `<h1>` .. `<h6>` | Hierarchy in reports; prefer 1-3 levels on phone screens. |
| Collapsed receipts | `<details><summary>Proof</summary>\n...\n</details>` | `<details><summary>Proof</summary>...</details>` | Always collapsed initially. Put command outputs, quotes, and secondary checks here. |
| Callout note | `<aside>Key caveat</aside>` | `<aside>Key caveat</aside>` | Subtle bordered callout for constraints, scope, or warnings. |
| Native table | `<table bordered striped compact>...</table>` | `<table bordered striped compact><thead><tr><th>...</th></tr></thead><tbody>...</tbody></table>` | Real scrollable/aligned native grid; prefer compact `<= 4` columns for mobile width. |
| Inline math | `$O(n \log n)$` | `<tg-math>O(n \log n)</tg-math>` | Inline formula rendering. |
| Block math | `$$\sum_{i=1}^n x_i$$` | `<tg-math display="block">...</tg-math>` | Centered display equation. |
| Spoiler | `\|\|hidden\|\|` | `<tg-spoiler>hidden</tg-spoiler>` | Click-to-reveal inline redaction. |
| Code block | ` ```ts\n...\n``` ` | `<pre><code class="language-ts">...</code></pre>` | Native syntax highlighting and horizontal scroll. |
| Embedded media | `![alt](tg://photo?id=chart_1)` | `<img src="tg://photo?id=chart_1"/>` | Also supports `tg://video?id=`, `tg://audio?id=`, `tg://document?id=`, `tg://animation?id=`, `tg://voice_note?id=`. Matching item must exist in `media`. |
| Map preview | `<tg-map lat="-27.47" lon="153.02" title="Lab"/>` | `<tg-map lat="-27.47" lon="153.02" title="Lab"/>` | Embedded interactive location card inside Rich body. |
| Footer metadata | `<footer>Scope</footer>` | `<footer>Scope</footer>` | Subdued footer for scope glosses or attribution. |
| In-body button row | `<tg-button-row>` | `<tg-button-row>` | Prefer inline `reply_markup` (`buttons`) when message actions or callback mutation (`editMessageReplyMarkup`) are needed. |

## Private-Chat Streaming Drafts (`send_message_draft`)

Use `send_message_draft` with a consistent non-zero integer `draft_id` when streaming incremental answers in private chats (`chat_id > 0`):

- Pass `markdown`, `html`, or `blocks` instead of `text` to invoke `sendRichMessageDraft`.
- Wrap internal reasoning progress in `<tg-thinking>Checking repository state...</tg-thinking>` above partial output; strip or exclude transient thinking blocks from final `send_rich_message`.
- Set `can_stop: true` (`keep_on_stop` optional) to expose Telegram's Stop button. Pressing Stop delivers `event: "stopped_message_generation"` (`draft_id`, `message_thread_id`); halt generation cleanly without overwriting.
- Private-chat Rich drafts forbid `media` attachments and group chats (`chat_id < 0`). Keep `text` plain Markdown when drafting in groups.
- Finalize by calling `send_rich_message` with the finished body (`draft_id` disappears automatically when replaced or finalized).

## Editing & Callbacks on Rich Messages

- Call `edit_message` with `message_id` and `markdown`, `html`, or `blocks` to patch Rich Messages in place via `editMessageText(rich_message=...)` (media arrays cannot be attached during edits).
- Inline `buttons` and `feedback_buttons: true` share `reply_markup`. Inbound taps mutate only the keyboard via `editMessageReplyMarkup` so Rich Message bodies remain untouched.
