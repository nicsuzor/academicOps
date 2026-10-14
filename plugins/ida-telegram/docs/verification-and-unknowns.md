---
title: Ida Telegram Verification and Build-Time Unknowns
type: reference
description: Live verification findings, resolved §6 build-time unknowns, audit of note_1772bc3e, and inventory of omitted or incomplete features for plugins/ida-telegram.
---

# Ida Telegram Verification and Build-Time Unknowns

This document records the verification of `plugins/ida-telegram` at commit `6dd43888099c3953c63e7e67308cfcf1194e9f50` (`v0.10.17`) against `[[spec_7a9caca5]]` (§4, §5, §6), task `[[aops_af92a2f6]]`, and `[[note_1772bc3e]]`.

## 1. End-to-End Verification Summary (`aops_af92a2f6`)

### 1.1 Packaging and Integrated Build Verification (`[[mem_51ba4651]]`)

`build/build.py:553-576` packages `plugins/ida-telegram` into `dist/ida-telegram-claude` via `make build`:

- Copies `server.ts` (`chmod 0755`), `package.json`, `src/**`, `app/**`, `hooks/**` (`hooks.json`, `ask-user-question.js`), and `test/**`.
- Emits `plugin.json` (`version: "0.10.17+g6dd43888"`) with `mcpServers.telegram` (`command: "bun"`, `args: ["run", "${CLAUDE_PLUGIN_ROOT}/server.ts"]`) and `hooks: "./hooks/hooks.json"`.
- `bun test` on the packaged `test/` suite passes 48 tests across 14 files (`0 fail`).

### 1.2 Live Environment Blocker

In the polecat verification container:

1. `TELEGRAM_BOT_TOKEN` is absent from environment variables and all container files (`env` and recursive search across `/home/nic`, `/etc`, `/run` returned 0 matches). Live calls to `https://api.telegram.org` and live Telegram client renders in chat `8860530746` cannot be executed inside the headless container.
2. Claude Code (`v2.1.296`) in the container logs `Channel notifications skipped: channels not enabled by org policy (set channelsEnabled: true in managed settings)` when launched with `--dangerously-load-development-channels plugin:ida-telegram@aops`.

To verify runtime behavior against the installed build (`dist/ida-telegram-claude`), the Mini App server was booted and rendered in headless Chromium across all four tabs (`Details`, `Questions`, `Review`, `Anchor`), and the MCP server + `TelegramBot` + `QuestionBroker` were driven end to end against a local mock Telegram Bot API server.

### 1.3 Acceptance Criteria Verdicts (`aops_af92a2f6`)

| # | Acceptance Criterion (Verbatim)                                                                                                            | Verdict   | Summary of Evidence and What Fails                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| - | ------------------------------------------------------------------------------------------------------------------------------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Each §5 scenario (chat cards, every Mini App tab) is shown by a capture of the live render -- capture region cited.                        | **UNMET** | Live Telegram chat renders are blocked by missing `TELEGRAM_BOT_TOKEN`. Live Mini App renders (`800x600` captures of all 4 tabs) and local Bot API simulations expose defects in **Details** (raw monospace Markdown instead of HTML tables/code highlighting, `plugins/ida-telegram/app/app.js:61`), **Review** (static placeholder; no permission/PR fetch in `plugins/ida-telegram/app/app.js` or `plugins/ida-telegram/src/web/routes.ts`), **Questions** (`multiSelect` rendered as single-click buttons without checkboxes, missing `header`/descriptions/`Other` free-text input, `plugins/ida-telegram/app/app.js:84-103`), **Anchor** (omits `waitingOn`, `delegations`, recent turns, uptime, `plugins/ida-telegram/app/app.js:125-141`), **Blockquotes** (emits per-line `expandable_blockquote` entities instead of one multi-line entity, `plugins/ida-telegram/src/telegram/format.ts:198-217`), **Feedback** (`👍` deletes `🔍 Details` button; `↩ Cancel` falls through to generic custom button handler, `plugins/ida-telegram/src/telegram/bot.ts:422-518`), and **Voice out** (`sendVoice` is an unimplemented comment stub, `plugins/ida-telegram/src/telegram/bot.ts:140-155`). |
| 2 | An inbound message of each type draws no reaction Ida did not choose -- captures cited.                                                    | **UNMET** | Blocked on live Telegram by missing `TELEGRAM_BOT_TOKEN`. Furthermore, `plugins/ida-telegram/src/telegram/bot.ts:338-341` unconditionally calls `setReaction(chat.id, message_id, "👀")` on every inbound `update.message` (text, quote-reply, photo/document, bot command, voice/audio) on arrival per `FR-9`, before Ida receives the channel event or chooses a reaction. Only `message_reaction` updates draw 0 automatic reactions.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 3 | A decision card renders and its answer reaches the session -- capture and session event quoted.                                            | **UNMET** | Live Telegram render blocked by missing `TELEGRAM_BOT_TOKEN`. In local runtime simulation of `dist/ida-telegram-claude`, `ask_user` posts the card with vertical buttons, persists across `QuestionBroker` restart, edits the card to `Selected: Refactor Poller ✅` with `inline_keyboard: []`, and emits the session notification. However: (a) `plugins/ida-telegram/src/telegram/questions.ts:238` emits `meta.event: "question_answer"` instead of `FR-2.5`'s `question_answered`; (b) `turn_id` is not accepted in `plugins/ida-telegram/src/mcp/tools.ts:52-84` or emitted in `meta`; (c) `plugins/ida-telegram/src/telegram/questions.ts:232-236` misaligns bold entity offsets on edited cards when `header` and multi-line `question` are combined; (d) `plugins/ida-telegram/hooks/ask-user-question.js:81-85` emits `{"decision":"deny"}` which Claude Code `v2.1.296` rejects (`Unknown hook decision type: deny. Valid types are: approve, block`).                                                                                                                                                                                                                                    |
| 4 | `getMyCommands` scoped to the chat lists the native commands after a start from `dev` and again after a restart -- outputs quoted.         | **UNMET** | Cannot hit live `api.telegram.org` without `TELEGRAM_BOT_TOKEN`. Against the local Bot API harness running `dist/ida-telegram-claude` (`plugins/ida-telegram/src/telegram/bot.ts:250-276`), both initial start and restart register and return all 6 commands (`decide`, `q`, `mine`, `reconcile`, `hydrate`, `up`) scoped to `{ "type": "chat", "chat_id": 8860530746 }`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 5 | A voice message in a don't-ask session is transcribed into the session -- transcript event quoted.                                         | **UNMET** | Cannot test live against Telegram without `TELEGRAM_BOT_TOKEN`. In local runtime simulation of `dist/ida-telegram-claude`, child-process transcription executes inside the channel server without any agent tool call (satisfying don't-ask mode), emitting `meta.event: "voice"`. However, on a fresh `stateDir`, `plugins/ida-telegram/src/telegram/bot.ts:535-538` writes `join(this.config.stateDir, "inbox", ...)` without `mkdirSync(..., { recursive: true })` (while `plugins/ida-telegram/src/store.ts:36-40` only creates `details/`), causing `ENOENT` on the first voice message until `inbox/` is created. In addition, `plugins/ida-telegram/src/config.ts:45` defaults `VOICE_TRANSCRIBE_CMD` to `~/.claude/channels/telegram/transcribe.sh` rather than `$HOME/.local/bin/transcribe.sh`, and `plugins/ida-telegram/src/telegram/voice.ts:29-31` drops `quoted_text` on voice replies.                                                                                                                                                                                                                                                                                               |
| 6 | `plugins/ida-telegram/docs/verification-and-unknowns.md` gives each §6 unknown its verified answer and source, plus the features left out. | **MET**   | Published in this document with verified answers and pinpoint sources for all 10 `[[spec_7a9caca5]]` §6 items, all 10 rows of `[[note_1772bc3e]]`, and the complete list of omitted and incomplete features.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

---

## 2. Verified Answers to `spec_7a9caca5` §6 Build-Time Unknowns

### Unknown 1: Blocking Mode vs Async Return for `ask_user`

- **Spec question (`spec_7a9caca5` §6.1)**: Can `mcp__telegram__ask_user` return immediately and deliver the answer via a later `<channel>` notification, or is blocking mode needed?
- **Verified answer**: **Confirmed -- blocking mode is not needed and was dropped.** `ask_user` registers the question in `QuestionBroker`, sends the inline keyboard card to Telegram, and immediately returns:
  `Question <id> posted to Nic. Do not assume an answer; continue other work or end your turn.`
  When the user taps an option in chat or submits in the Mini App, `QuestionBroker.resolve()` persists the answer to `questions.json` and calls `emitChannelEvent` to send a `notifications/claude/channel` event into the session.
- **Defects found during verification**:
  - `plugins/ida-telegram/src/telegram/questions.ts:238` emits `meta.event = "question_answer"` whereas `spec_7a9caca5` `FR-2.5` specifies `event="question_answered"`.
  - `plugins/ida-telegram/src/mcp/tools.ts:52-84` and `plugins/ida-telegram/src/mcp/server.ts:236-243` do not accept `turn_id` or include `turn_id` in `meta`.
- **Sources**:
  - `plugins/ida-telegram/src/mcp/server.ts:236-243`
  - `plugins/ida-telegram/src/telegram/questions.ts:116-146`
  - `plugins/ida-telegram/src/telegram/questions.ts:207-244`

### Unknown 2: `PreToolUse` Hook Output Contract for Denying `AskUserQuestion`

- **Spec question (`spec_7a9caca5` §6.2)**: What is the exact JSON stdout schema a `PreToolUse` hook must return in Claude Code so `AskUserQuestion` is denied cleanly with a redirection message to the model?
- **Verified answer**: **Live CLI test disproves the current hook output schema.**
  - `plugins/ida-telegram/hooks/ask-user-question.js:81-85` currently writes:
    `{"decision": "deny", "reason": "Telegram is active for this session. Do not use AskUserQuestion..."}`
  - Tested live against `/opt/nic/home/.local/bin/claude` (`2.1.296 (Claude Code)`): when a `PreToolUse` hook outputs `{"decision": "deny", "reason": "..."}`, Claude Code rejects the hook output with:
    `Hook PreToolUse (AskUserQuestion) error: JSON validation failed: Unknown hook decision type: deny. Valid types are: approve, block`
    and proceeds to execute the tool anyway.
  - Tested live against Claude Code `2.1.296`: outputting either top-level `{"decision": "block", "reason": "..."}` or `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}` passes validation (`Hook PreToolUse (AskUserQuestion) success: <reason>`) and blocks the tool call cleanly while surfacing the reason to the model.
- **Sources**:
  - `plugins/ida-telegram/hooks/ask-user-question.js:81-86`
  - `plugins/ida-telegram/hooks/hooks.json:1-16`
  - Live execution against `/opt/nic/home/.local/bin/claude --version` (`2.1.296 (Claude Code)`) with `--debug-file` trace inspection.

### Unknown 3: Channel Permission Relay and Modified Input Support

- **Spec question (`spec_7a9caca5` §6.3)**: Does Claude Code's channel permission relay protocol (`claude/channel/permission`) support returning `updatedInput` (modified tool arguments), or only binary `allow` / `deny`?
- **Verified answer**: **Binary `allow` / `deny` only; furthermore, `ida-telegram` implements the wrong capability path and JSON-RPC method names.**
  - Inspected `/opt/nic/home/.local/bin/claude` (`2.1.296`) channel permission schemas and donor plugin (`external_plugins/telegram`):
    1. Server capabilities must declare `capabilities: { tools: {}, experimental: { "claude/channel": {}, "claude/channel/permission": {} } }`. `plugins/ida-telegram/src/mcp/server.ts:69-74` omits `"claude/channel/permission": {}`.
    2. Inbound permission prompts from Claude Code arrive as notification `notifications/claude/channel/permission_request` with params `{ request_id: string, tool_name: string, description: string, input_preview: string }` (`input_preview` is a 200-char truncated string, not the full input object).
    3. Outbound permission replies from the channel server are sent as notification `notifications/claude/channel/permission` with params `{ request_id: string, behavior: "allow" | "deny" }` -- there is no `updatedInput` field in the channel permission schema.
  - `plugins/ida-telegram/src/mcp/server.ts:137-152` instead registers a request handler on `method === "claude/channel/permission"` returning `{ allowed }`, which never fires in Claude Code `2.1.296`.
- **Sources**:
  - `plugins/ida-telegram/src/mcp/server.ts:69-74`
  - `plugins/ida-telegram/src/mcp/server.ts:137-152`
  - `plugins/ida-telegram/src/mcp/permissions.ts:1-60`
  - `/opt/nic/home/.local/bin/claude` (`2.1.296`) embedded channel schemas (`notifications/claude/channel/permission_request`, `notifications/claude/channel/permission`).

### Unknown 4: Official Route for Interrupt / Compact (`Stop Session` in Anchor Tab)

- **Spec question (`spec_7a9caca5` §6.4)**: Does Claude Code expose a programmatic MCP/channel method to interrupt an in-flight turn or trigger `/compact`, or must `Stop Session` send a high-priority channel event?
- **Verified answer**: **No programmatic interrupt or compact RPC exists on the channel protocol.**
  - Claude Code's channel protocol exposes only `notifications/claude/channel` and `notifications/claude/channel/permission`.
  - `POST /api/app/anchor/stop` in `plugins/ida-telegram/src/web/routes.ts:182-196` calls `ctx.onStopSession()`, which (`plugins/ida-telegram/server.ts:75-78`) calls `bot.emitChannelEvent("Stop requested by user via Mini App Anchor tab.", { event: "stop_session" })`.
  - Because `notifications/claude/channel` messages are queued into the conversation stream, this delivers a user-turn channel notification rather than a hard OS/CLI signal interrupt (`SIGINT`) during an active tool execution.
- **Sources**:
  - `plugins/ida-telegram/src/web/routes.ts:182-196`
  - `plugins/ida-telegram/server.ts:75-78`

### Unknown 5: Official Source for Context-Window Usage (`statusLine` vs Transcript)

- **Spec question (`spec_7a9caca5` §6.5)**: What is the authoritative source for context-window usage (`contextTokens`, `contextMax`) displayed on the Anchor tab?
- **Verified answer**: **No automatic feed is wired in `ida-telegram`; `contextTokens` is optional in `AnchorState` and defaults to `0%` in the UI (`plugins/ida-telegram/app/app.js:132`).**
  - `plugins/ida-telegram/src/store.ts:11-22` defines `AnchorState` with optional `contextTokens?: { usedTokens: number; totalTokens: number; percentage: number }` persisted in `anchor.json` (`plugins/ida-telegram/src/store.ts:64-85`).
  - Neither `plugins/ida-telegram/server.ts`, `plugins/ida-telegram/src/mcp/server.ts`, nor `plugins/ida-telegram/src/store.ts` reads Claude Code's `statusLine` JSON input (`context_window.used_percentage` / `current_usage`) or session JSONL usage records, and the `update_anchor` MCP tool (`plugins/ida-telegram/src/mcp/tools.ts:86-110`, `plugins/ida-telegram/src/mcp/server.ts:246-254`) does not expose a `context_tokens` parameter. Unless `anchor.json` is edited externally, the Anchor tab gauge remains at `0%`.
- **Sources**:
  - `plugins/ida-telegram/src/store.ts:11-22`
  - `plugins/ida-telegram/src/store.ts:64-85`
  - `plugins/ida-telegram/src/mcp/tools.ts:86-110`
  - `plugins/ida-telegram/src/mcp/server.ts:246-254`

### Unknown 6: Whether Plugin MCP Servers Inherit Launcher Environment Variables

- **Spec question (`spec_7a9caca5` §6.6)**: Do plugin MCP servers spawned by Claude Code inherit the parent shell's environment variables (`TELEGRAM_BOT_TOKEN`, `IDA_WEB_URL`, `VOICE_TRANSCRIBE_CMD`, etc.), or only variables declared in `plugin.json`?
- **Verified answer**: **Confirmed -- Claude Code merges `process.env` into spawned stdio MCP server environments, and `plugins/ida-telegram/src/config.ts` also loads `~/.claude/channels/telegram/.env` directly as a fallback.**
  - In the generated `plugin.json` (`build/build.py:558-571`), `mcpServers.telegram` declares `"command": "bun", "args": ["run", "${CLAUDE_PLUGIN_ROOT}/server.ts"]` with no restrictive `env` block. Claude Code spawns stdio MCP servers with `{ ...process.env, ...serverConfig.env }`.
  - Additionally, `plugins/ida-telegram/src/config.ts:19-33` explicitly reads `join(homedir(), ".claude", "channels", "telegram", ".env")` and populates `envMap` before falling back to `process.env`.
- **Sources**:
  - `plugins/ida-telegram/src/config.ts:19-56`
  - `build/build.py:558-571`

### Unknown 7: Five Telegram Platform and Bot API Behaviours

1. **`web_app` inline keyboard buttons in 1:1 private chats (`spec_7a9caca5` §6.7a)**:
   - **Verified answer**: Supported by Telegram Bot API (`InlineKeyboardButton.web_app`) in private chats with the bot. Used in `plugins/ida-telegram/src/telegram/feedback.ts:56-65` (`🔍 Details` and `🔍 Review diff`). Requires `IDA_WEB_URL` to be a valid `https://` URL (Telegram rejects `http://` URLs in `web_app` buttons).
2. **`message_reaction` updates in private chats (`spec_7a9caca5` §6.7b)**:
   - **Verified answer**: Telegram delivers `message_reaction` updates when explicitly listed in `allowed_updates` on `getUpdates`. `plugins/ida-telegram/src/telegram/bot.ts:294-298` passes `allowed_updates: ["message", "callback_query", "message_reaction"]`, and `plugins/ida-telegram/src/telegram/inbound.ts:86-117` parses `update.message_reaction`.
   - **Defect found**: `plugins/ida-telegram/src/telegram/bot.ts:576` calls `parseInboundUpdate(update, this.config.allowFrom)` without passing the third `getExcerpt` callback parameter (`plugins/ida-telegram/src/telegram/inbound.ts:39-43`), so `meta.target_excerpt` is never populated at runtime.
3. **`expandable_blockquote` entity (`spec_7a9caca5` §6.7c)**:
   - **Verified answer**: Telegram Bot API 7.4+ supports `type: "expandable_blockquote"` in `MessageEntity` arrays with UTF-16 code-unit `offset` and `length`.
   - **Defect found**: `plugins/ida-telegram/src/telegram/format.ts:53-82` groups consecutive `>!` lines into `expandableQuotes`, but `plugins/ida-telegram/src/telegram/format.ts:198-217` discards `expandableQuotes`, re-splits the raw markdown by `\n`, and emits a separate `expandable_blockquote` entity for each individual line instead of a single collapsible multi-line block.
4. **`sendVoice` caption limit (`spec_7a9caca5` §6.7d)**:
   - **Verified answer**: Telegram Bot API limits `sendVoice` captions to 1,024 UTF-16 characters (`sendMessage` allows 4,096).
   - **Defect found**: `plugins/ida-telegram/src/telegram/bot.ts:140-155` contains only comments (`// If caption fits under 1024, attach caption to sendVoice...`) and never calls `sendVoice` or `synthesizeVoice` (`plugins/ida-telegram/src/telegram/voice.ts:59-83`).
5. **Microphone access in Telegram Mini App WebView (`spec_7a9caca5` §6.7e)**:
   - **Verified answer**: Unreliable across iOS/Android WebViews, so `spec_7a9caca5` `FR-4.6` intentionally avoided WebView `getUserMedia` in favor of native Telegram chat voice notes. However, the `FR-4.6` UI hint (`"send a voice note in chat"`) is missing from `plugins/ida-telegram/app/index.html` and `plugins/ida-telegram/app/app.js`.

### Unknown 8: `--dangerously-load-development-channels` CLI Flag Syntax

- **Spec question (`spec_7a9caca5` §6.8)**: What is the exact CLI syntax for `--dangerously-load-development-channels` in Claude Code?
- **Verified answer**: Verified live against `/opt/nic/home/.local/bin/claude` (`2.1.296 (Claude Code)`):
  - The flag takes a space-separated list of channel specifiers in the form `plugin:<name>@<marketplace>` or `server:<name>`.
  - Passing an invalid prefix returns:
    `error: option '--dangerously-load-development-channels <channels...>' argument 'ida-telegram' is invalid. Invalid channel entry "ida-telegram" -- specify as plugin:<name>@<marketplace> or server:<name>`
  - Passing `--dangerously-load-development-channels plugin:ida-telegram@aops` is accepted by the CLI parser.
- **Sources**:
  - Live execution of `/opt/nic/home/.local/bin/claude --dangerously-load-development-channels` (`v2.1.296`)
  - `[[kb_ee859e3f]]`

### Unknown 9: Donor Provenance in `NOTICE` and `THIRD_PARTY.md`

- **Spec question (`spec_7a9caca5` §6.9)**: Which files derive from `anthropics/claude-plugins-official` (`external_plugins/telegram`, Apache-2.0) and is provenance recorded in `THIRD_PARTY.md` and `NOTICE`?
- **Verified answer**:
  - `THIRD_PARTY.md:107-118` records `anthropics/claude-plugins-official` (`external_plugins/telegram`, Apache-2.0) and states that `plugins/ida-telegram/NOTICE` preserves the upstream copyright and license header.
  - `plugins/ida-telegram/NOTICE:1-9` preserves the Apache-2.0 attribution for `external_plugins/telegram`.
  - Inspection of the donor plugin against `plugins/ida-telegram/` shows that `plugins/ida-telegram` was written as a clean-room native `fetch` + `bun:sqlite` implementation rather than copying the `grammy`-based donor file verbatim, while retaining compatible `.env` paths (`~/.claude/channels/telegram/.env`) and channel notification concepts.
- **Sources**:
  - `THIRD_PARTY.md:107-118`
  - `plugins/ida-telegram/NOTICE:1-9`

### Unknown 10: PKB Conflict About Prime's Host (`kb_3ac2fd36` vs `kb_11d2b2d7`)

- **Spec question (`spec_7a9caca5` §6.10)**: Resolve the contradiction between `[[kb_3ac2fd36]]` (`academicOps Architecture Map`, claiming `aops-crew` runs on `tryptamine`) and `[[kb_11d2b2d7]]` (`Telegram Single-Poller Role Separation`, stating Ida Prime runs on `hospital`).
- **Verified answer**: **Ida Prime's primary interactive host and Telegram poller is `hospital` (`[[kb_11d2b2d7]]`, `[[kb_3cc78da3]]`).**
  - `[[kb_11d2b2d7]]` and `[[kb_3cc78da3]]` document that `hospital` runs the live `aops-crew` session (`claude --dangerously-load-development-channels plugin:ida-telegram@aops`) and `aops-app.hospital.fcb282.ts.net`, while `tryptamine` is the secondary workstation (`IDA_TELEGRAM_ROLE=client`, `VOICE_TRANSCRIBE_URL=http://hospital:8090/...`).
  - `[[kb_3ac2fd36]]` was stale regarding `aops-crew` placement.
- **Sources**:
  - `[[kb_11d2b2d7]]`
  - `[[kb_3cc78da3]]`
  - `[[kb_3ac2fd36]]`

---

## 3. Audit and Correction of `note_1772bc3e` (`Ida-Telegram §6 Build-Time Unknowns`)

`[[note_1772bc3e]]` (created during PR `#2899` before the 14 Oct rewrite of `[[spec_7a9caca5]]`) contains a 10-row table that cites non-existent file paths and libraries in 9 of its 10 rows. The table below records the verified reality in `plugins/ida-telegram` at `6dd43888099c3953c63e7e67308cfcf1194e9f50`:

| #  | Unknown Topic in `note_1772bc3e`                  | Claimed in `note_1772bc3e` (Incorrect)                                                                              | Verified Reality in `plugins/ida-telegram` (`6dd43888`)                                                                                                                                                                                                                                                                                                                                   |
| -- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Expandable blockquote syntax (`>!`)               | Claimed `MarkdownV2` spoiler-quote markers inside a non-existent root `format.ts` (`L12-L54`).                      | Implemented via UTF-16 `MessageEntity` (`type: "expandable_blockquote"`) in `plugins/ida-telegram/src/telegram/format.ts:53-82,198-217` (no `MarkdownV2` strings). Currently defective for multi-line quotes because lines `198-217` emit one entity per line instead of grouping consecutive `>!` lines.                                                                                 |
| 2  | Message reaction updates (`message_reaction`)     | Claimed `grammy` `bot.start({ allowed_updates: [...] })` inside a non-existent root `inbound.ts` (`L88-L115`).      | No `grammy` dependency exists (`plugins/ida-telegram/package.json:1-21`). Raw `fetch` long-polling in `plugins/ida-telegram/src/telegram/bot.ts:294-298` requests `allowed_updates: ["message", "callback_query", "message_reaction"]`, and `plugins/ida-telegram/src/telegram/inbound.ts:86-117` parses `message_reaction`.                                                              |
| 3  | WebApp `initData` HMAC-SHA256 validation          | Cited `plugins/ida-telegram/src/web/auth.ts:15-62` (only verified citation in `note_1772bc3e`).                     | Verified in `plugins/ida-telegram/src/web/auth.ts:14-63`: computes `HMAC_SHA256("WebAppData", botToken)` and `timingSafeEqual` with a `maxAgeSeconds = 86400` replay check on `auth_date`.                                                                                                                                                                                                |
| 4  | Deep-linking into Mini App tabs                   | Claimed `tgWebAppStartParam` parsing in a non-existent `app.html` (`L42-L78`).                                      | Implemented via URL query parameters in `plugins/ida-telegram/app/app.js:41-52`: reads `params.get("d")` (`Details`), `params.get("q")` (`Questions`), `params.get("anchor")` (`Anchor`). Missing `params.get("tab") === "review"` handler for `🔍 Review diff` buttons (`plugins/ida-telegram/src/telegram/feedback.ts:62`).                                                             |
| 5  | Question broker crash persistence                 | Claimed atomic `.tmp` rename in `plugins/ida-telegram/src/telegram/questions.ts:30-95`.                             | Implemented via direct `writeFileSync(this.filePath, JSON.stringify(list, null, 2), "utf8")` (no `.tmp` rename) in `plugins/ida-telegram/src/telegram/questions.ts:69-88`, plus SQLite storage in `plugins/ida-telegram/src/store.ts:51-77`.                                                                                                                                              |
| 6  | Diff chunking and syntax highlighting in Mini App | Claimed `highlight.js` + 500KB limit in non-existent `review.ts` and `app.html`.                                    | `plugins/ida-telegram/src/web/review.ts:52-119` parses unified diffs into `DiffFile`/`DiffLine` structs and HTML spans, but is **dead code**: `formatPrDiff` is never imported or called in `plugins/ida-telegram/src/web/routes.ts` or `plugins/ida-telegram/app/app.js`, and no `highlight.js` exists.                                                                                  |
| 7  | Voice transcription fallback & timeout            | Claimed 15s `AbortSignal.timeout(15000)` HTTP POST to `STT_BASE_URL` in a non-existent root `voice.ts` (`L22-L68`). | Implemented by spawning a local child process (`config.voiceTranscribeCmd`, `timeout: 30000`) in `plugins/ida-telegram/src/telegram/voice.ts:37-57`. No `STT_BASE_URL` exists in the plugin.                                                                                                                                                                                              |
| 8  | Outbound TTS OGG/Opus encoding                    | Claimed `ffmpeg -c:a libopus -b:a 32k -vbr on` pipeline in a non-existent root `voice.ts` (`L75-L120`).             | `plugins/ida-telegram/src/telegram/voice.ts:59-83` spawns `config.voiceSpeakCmd` (`timeout: 30000`), and `plugins/ida-telegram/src/telegram/bot.ts:140-155` leaves `sendVoice` completely unimplemented (comment stub only).                                                                                                                                                              |
| 9  | Multi-host single-poller lock mechanism           | Claimed `409 Conflict` switches the process into `client` proxy mode in a non-existent `poller.ts` (`L40-L85`).     | No `poller.ts` exists. `plugins/ida-telegram/src/role.ts:46-79` acquires a local filesystem `poller.lock` (`O_CREAT` + `O_EXCL`) and sets a Unix socket proxy (`ipc.sock`) for same-host processes. On Telegram `409 Conflict`, `plugins/ida-telegram/src/telegram/bot.ts:309-325` backs off (5s to 60s) and emits a warning after 3 consecutive 409s; it does not switch to client mode. |
| 10 | Native command `/decide` & `/q` payload routing   | Claimed `loadTasksSnapshot` in a non-existent `commands.ts` (`L18-L64`).                                            | No `commands.ts` or `loadTasksSnapshot` exists. `plugins/ida-telegram/src/telegram/inbound.ts:122-146` maps `/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, `/up` to `COMMAND_SKILLS` and emits a `bot_command` channel event (`meta.skill`, `meta.default_action`) for Ida to execute in-session.                                                                                    |

---

## 4. Features Left Out or Incomplete

### 4.1 Features Intentionally Left Out by Spec Design (`spec_7a9caca5`)

1. **Blocking `ask_user` RPC mode (§6.1)**: Omitted in favor of immediate tool return + asynchronous `notifications/claude/channel` delivery so the session is never deadlocked waiting on a human tap.
2. **In-WebView microphone recording (`getUserMedia`, §6.7e)**: Omitted from the Mini App (`FR-4.6`) because mobile WebView microphone permissions are unreliable; users send native Telegram voice notes in chat instead.
3. **Modified tool input (`updatedInput`) in channel permission relay (§6.3)**: Omitted because Claude Code's `notifications/claude/channel/permission` schema only supports binary `behavior: "allow" | "deny"`.
4. **Hard process-level turn interrupt / `/compact` RPC from Mini App (§6.4)**: Omitted because Claude Code's channel protocol provides no out-of-band interrupt or compact RPC; `Stop Session` emits a `stop_session` channel event.
5. **Grammy / external Telegram SDK and `MarkdownV2` escaping**: Replaced by zero-dependency native `fetch` calls to `api.telegram.org` and UTF-16 `MessageEntity` arrays (`plugins/ida-telegram/src/telegram/format.ts`).

### 4.2 Spec Features Currently Unbuilt or Defective in `plugins/ida-telegram` (`6dd43888`)

1. **Outbound Voice Replies (`FR-7.1–FR-7.4`)**:
   - `plugins/ida-telegram/src/telegram/bot.ts:140-155` contains a comment stub instead of calling `synthesizeVoice` and Telegram's `sendVoice` endpoint.
   - `config.voiceReplies` (`mirror` / `always` / `off` in `plugins/ida-telegram/src/config.ts:47`) is never checked in `plugins/ida-telegram/src/mcp/server.ts:168-203`.
   - `reply` tool result omits `voiceSent` and `voiceError`, and Tier 2 blockquotes are not moved to Details when sending voice.
2. **Mini App Review Tab (`FR-4.4`, `FR-4.5`)**:
   - `plugins/ida-telegram/app/index.html:37-39` is a static placeholder (`"No pending permissions or PR diffs waiting for review."`).
   - `plugins/ida-telegram/src/web/routes.ts` has no `GET` endpoints for pending permissions (`PermissionRelay.list()` in `plugins/ida-telegram/src/mcp/permissions.ts:46-48` is unused) or PR diffs (`formatPrDiff` in `plugins/ida-telegram/src/web/review.ts:82` and `config.githubToken` in `plugins/ida-telegram/src/config.ts:50` are unused).
   - `POST /api/app/review/permission` (`plugins/ida-telegram/src/web/routes.ts:156-168`) does not call `ctx.editTelegramCard` to update the chat card to `"Allowed via Mini App ✅"`.
   - `plugins/ida-telegram/app/app.js:41-52` does not handle `?tab=review` from the `🔍 Review diff` button (`plugins/ida-telegram/src/telegram/feedback.ts:62`).
3. **Channel Permission Protocol Wiring (`FR-4.4`)**:
   - `plugins/ida-telegram/src/mcp/server.ts:69-74` omits `experimental["claude/channel/permission"]`, and lines `137-152` listen for a JSON-RPC request `claude/channel/permission` instead of Claude Code's notification `notifications/claude/channel/permission_request` and outbound notification `notifications/claude/channel/permission`.
4. **Mini App Details Markdown Rendering (`FR-4.3`, `FR-1.6`)**:
   - `plugins/ida-telegram/app/app.js:61` renders `<div class="markdown-body" style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(data.markdown)}</div>` -- raw unparsed Markdown text rather than rendered HTML tables and syntax-highlighted code blocks.
   - `plugins/ida-telegram/src/telegram/format.ts:234` (`formatTable`) and `plugins/ida-telegram/src/telegram/format.ts:286` (`chunkMessage`) are never called by `plugins/ida-telegram/src/mcp/server.ts` or `plugins/ida-telegram/src/telegram/bot.ts`.
5. **Mini App Questions Multi-Select, Free-Text, and Metadata (`FR-4.6`)**:
   - `plugins/ida-telegram/app/app.js:84-103` renders `multiSelect` options as immediate single-click submit buttons instead of checkboxes with a submit button; omits `header`, option `description`, an `"Other"` free-text input box, and the `"send a voice note in chat"` hint.
6. **Mini App Anchor Completeness and Context Gauge (`FR-4.7`)**:
   - `plugins/ida-telegram/app/index.html:43-65` and `plugins/ida-telegram/app/app.js:125-141` omit `waitingOn`, `delegations`, recent turns, and uptime (`GET /api/app/anchor` returns `waitingOn` and `delegations`, but `app.js` ignores them). Nothing updates `contextTokens` in `anchor.json`.
7. **Multi-Line Expandable Blockquote Entities (`FR-1.2`, `FR-1.5`)**:
   - `plugins/ida-telegram/src/telegram/format.ts:198-217` discards multi-line quote groupings from lines `53-82` and emits one `expandable_blockquote` entity per line.
8. **Feedback Row Preservation, Cancel Handler, and Critique Prompt (`FR-3.2`, `FR-3.3`)**:
   - `plugins/ida-telegram/src/telegram/bot.ts:371,422-436` calls `answerCallbackQuery` without `"Noted 👍"` toast text and replaces the entire `inline_keyboard` with `[[{ text: "👍 saved", callback_data: "noop" }]]`, deleting `🔍 Details` and `🔍 Review diff` buttons.
   - `plugins/ida-telegram/src/telegram/bot.ts:422-518` has no handler for `fb:cancel:<id>` (`plugins/ida-telegram/src/telegram/feedback.ts:91`), causing `↩ Cancel` to fall through to the generic custom button handler (`Selected: ↩ Cancel ✅`).
   - Tapping `🎙 Say why` (`fb:why:<id>`) immediately emits `critique: "Say why"` instead of prompting for a voice/text reply.
9. **`PreToolUse` Hook Decision Type (`FR-2.1`)**:
   - `plugins/ida-telegram/hooks/ask-user-question.js:81-85` outputs `"decision": "deny"`, which fails validation in Claude Code `v2.1.296` (must use `"decision": "block"` or `hookSpecificOutput.permissionDecision: "deny"`).
10. **Inbound Voice `inbox/` Creation and Attachment Tool Handler (`FR-6.1`, `FR-8`)**:
    - `plugins/ida-telegram/src/telegram/bot.ts:535-538` does not call `mkdirSync(join(this.config.stateDir, "inbox"), { recursive: true })` before writing `voice_<ts>.ogg`, failing with `ENOENT` on a fresh `stateDir`.
    - `download_attachment` is declared in `plugins/ida-telegram/src/mcp/tools.ts:112-123` but has no handler in `plugins/ida-telegram/src/mcp/server.ts:161-287` (`Unknown tool: download_attachment`).
    - `plugins/ida-telegram/src/telegram/bot.ts:576` omits the `getExcerpt` argument to `parseInboundUpdate`, leaving `target_excerpt` empty on `message_reaction` events.
    - `plugins/ida-telegram/src/telegram/bot.ts:316-318` passes 3 arguments to `this.emitChannelEvent(content, meta)` (which takes 2 arguments at `plugins/ida-telegram/src/telegram/bot.ts:41`), dropping `content` on 409 conflict warnings.
