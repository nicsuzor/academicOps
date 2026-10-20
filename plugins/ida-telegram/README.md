# ida-telegram

Ida's custom Telegram channel and Mini App plugin for Claude Code.

## Architecture

- **Channel Protocol:** Stdio MCP server with `experimental["claude/channel"]` support.
- **Progressive Disclosure:**
  - Tier 1: Bold headline and bullets in chat.
  - Tier 2: Expandable blockquotes (`>!`) collapsed by default.
  - Tier 3: Immutable Details pages viewed via the Telegram Mini App (`🔍 Details` button).
  - Overflow handling: Text exceeding `max_chat_chars` (default 1200) splits at whole paragraphs and relocates cleanly to the Details page without loss.
- **Asynchronous Questions:**
  - `ask_user` tool and `PreToolUse` hook for `AskUserQuestion`.
  - Vertical numbered keyboard options with recommendation first.
  - Never blocks or assumes answers; delivers answers as channel notification events upon reply.
- **Option Buttons:**
  - `reply` takes `buttons` (one per row) for the answers to a question asked in the reply; a tap edits the card to `Selected: <label> ✅` and emits a `button_tap` channel event.
- **Mini App Security, Details, Review, Questions & Anchor:**
  - Loopback-only Bun HTTP server (`127.0.0.1:<port>`) serving `/app/*` and `/api/app/*`.
  - Telegram `initData` HMAC-SHA256 validation with 1-hour expiration and `allowFrom` whitelist check.
  - **Details tab (`FR-4.3`, `FR-1.6`):** Renders stored Details Markdown as formatted HTML (headings, inline formatting, collapsible `>!` quotes, syntax-highlighted code blocks, and HTML `<table>` elements).
  - **Review tab (`FR-4.4`, `FR-4.5`):** Displays live pending tool permission requests (`Bash` copyable scripts, `Edit`/`MultiEdit`/`Write` unified diffs, JSON inputs) with `Allow` / `Deny` actions that resolve the relay and edit the Telegram chat card (`Allowed via Mini App ✅`), alongside PR/branch diffs fetched via `GITHUB_TOKEN` with a file tree, syntax-highlighted hunks, and `Approve` / `Request changes` actions that emit channel events to Ida without mutating GitHub directly.
  - **Questions tab (`FR-4.6`):** Renders pending questions with `header`, option `description` lines, Recommended badges, radio options for single-select, checkboxes with a Submit button for `multiSelect`, a free-text input box for custom answers, and the `"To answer by voice, send a voice note in chat"` hint.
  - **Anchor tab (`FR-4.7`):** Displays live `focus`, `taskId`, `uptime`, `waitingOn`, `delegations`, `pendingQuestions`, `recentTurns` (inbound and outbound), context window gauge (`contextTokens`), `🛑 Stop Session`, and the overwhelm dashboard link.
- **Voice In & Out:**
  - Voice notes transcribed via pluggable script without spending tool calls.
  - Voice replies via speech synthesis for spoken audio delivery.
- **Native Bot Commands:**
  - Registers persona-tailored command menus via `setMyCommands` at `botCommandScopeChat` for each `allowFrom` chat on startup, surviving channel restarts and overriding `all_private_chats` defaults.
  - Ida Prime registers `/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, and `/up`.
  - Strategic Ida registers `/strategize`, `/remember`, `/decompose`, `/q`, `/hydrate`, and `/up`.
  - Persona is configured via `IDA_TELEGRAM_PERSONA` / `TELEGRAM_PERSONA` or inferred from `STATE_DIR` (`telegram-pauli` / `telegram-prime` -> `prime`, `telegram-ida` / `telegram-strategic` -> `strategic`).
  - Custom JSON override via `TELEGRAM_BOT_COMMANDS` overrides persona defaults.
  - Excludes reserved official-plugin commands (`/start`, `/help`, `/status`).
  - Enriches bare menu taps (commands with no arguments) with each command's defined no-argument behavior (`meta.default_action` and `meta.skill`).
- **Concurrency & Host Locks:**
  - Gated to `IDA_TELEGRAM_ROLE=primary`.
  - Non-primary instances register zero tools, run no poller, and leave hooks inert.
  - Same-host PID locking and exponential 409 Conflict backoff policy.
