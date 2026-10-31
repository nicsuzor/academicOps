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
- **Option Buttons & Message Actions:**
  - `reply` takes `buttons` for the answers to a question asked in the reply; a tap edits the card to `Selected: <label> ✅` and emits a `button_tap` channel event. Supports 2D row arrays (`ReplyButtonOption[][]`), layout chunking via `button_layout` (e.g. `[3, 3, 2]`) or `buttons_per_row` (e.g. `4`), and per-button `row` properties, defaulting to 1 button per row when flat.
  - Setting `predefined_row: true` groups all active predefined buttons (`🔍 Details`, `🔍 Review diff`, `👍`/`👎`, `[🧐 Check logic]`, `[💡 Explain]`, `[🧾 Reasons]`, `[✅ Accept recommendation]`, `[❌ Decline recommendation]`) onto a single consolidated first row above any caller buttons.
  - Every reply automatically attaches `[🧐 Check logic]`, `[💡 Explain]`, `[🧾 Reasons]`, `[✅ Accept recommendation]`, and `[❌ Decline recommendation]` action buttons (unless `actions: false` is passed). Tapping `🧐 Check logic` delivers an inbound request naming the message for Ida to run a peer `premise-check`. Tapping `💡 Explain` delivers an inbound request for Ida to expand that message in more detail. Tapping `🧾 Reasons` delivers an inbound request for Ida to provide the argument chain ("how do you know that?") with verbatim Argdown blocks attached in Details. Tapping `✅ Accept recommendation` or `❌ Decline recommendation` marks the card with the choice and delivers an event naming the message and whether the recommendation was accepted or declined.
- **Mini App Security, Details, Review, Questions & Anchor:**
  - Loopback-only Bun HTTP server (`127.0.0.1:<port>`) serving `/app/*` and `/api/app/*`.
  - Telegram `initData` HMAC-SHA256 validation with 1-hour expiration and `allowFrom` whitelist check.
  - **Details tab (`FR-4.3`, `FR-1.6`):** Renders stored Details Markdown as formatted HTML (headings, inline formatting, collapsible `>!` quotes, syntax-highlighted code blocks, and HTML `<table>` elements).
  - **Review tab (`FR-4.4`, `FR-4.5`):** Displays live pending tool permission requests (`Bash` copyable scripts, `Edit`/`MultiEdit`/`Write` unified diffs, JSON inputs) with `Allow` / `Deny` actions that resolve the relay and edit the Telegram chat card (`Allowed via Mini App ✅`), alongside PR/branch diffs fetched via `GITHUB_TOKEN` with a file tree, syntax-highlighted hunks, and `Approve` / `Request changes` actions that emit channel events to Ida without mutating GitHub directly.
  - **Questions tab (`FR-4.6`):** Renders pending questions with `header`, option `description` lines, Recommended badges, radio options for single-select, checkboxes with a Submit button for `multiSelect`, a free-text input box for custom answers, and the `"To answer by voice, send a voice note in chat"` hint.
  - **Anchor tab (`FR-4.7`):** Displays live `focus`, `taskId`, `uptime`, `waitingOn`, `delegations`, `pendingQuestions`, `recentTurns` (inbound and outbound), context window gauge (`contextTokens`), `🛑 Stop Session`, and the overwhelm dashboard link.
- **Voice In & Out:**
  - **Voice In (Inbound transcription):** Inbound Telegram voice notes (`voice` and `audio` updates) are downloaded to `inbox/` under `stateDir`. The plugin executes `VOICE_TRANSCRIBE_CMD <audio-path>` with `cwd` set to `stateDir` and merged environment variables from `stateDir/.env` and `process.env`. The transcribed text is delivered directly as a `notifications/claude/channel` event without agent tool calls.
  - **Voice Out (Outbound speech synthesis):** When `voice: true` is specified on `reply` (or by default when `voice_replies` is `mirror` and the last inbound message was a voice note), the plugin synthesises Tier 1 text (headline and bullets, stripping Markdown syntax, quotes, and links) using Gemini 3.8 Flash TTS via `VOICE_SPEAK_CMD <text-file> <out.ogg>` and sends it as a Telegram voice note (`sendVoice`) with inline keyboards and captions. Tier 2 quotes are relocated to the Details page.
  - **Required Dependencies:**
    - `ffmpeg` with `libopus` encoder: Required in `PATH` by voice-out to transcode Gemini synthesized audio into Telegram voice note OGG/Opus format.
    - `python3` (≥ 3.10): Required to run speech synthesis (`scripts/speak-gemini.py` via `scripts/speak.sh`) and transcription scripts.
    - `uv` (or `assemblyai` Python package): Required by `transcribe-voice` script.
    - Stable working directory & environment inheritance: Child processes run with `cwd` explicitly set to `stateDir` (guaranteed to exist), preventing `getcwd` and `(os error 2)` failures in ephemeral containers, and inherit merged variables from `stateDir/.env` and `process.env`.
  - **Required Environment Variables:**
    - `ASSEMBLY_AI_API_KEY`: API key for AssemblyAI transcription service (used by `transcribe-voice` / `transcribe.sh` for voice-in).
    - `GEMINI_API_KEY`: API key for Gemini 3.8 Flash TTS (`gemini-3.8-flash-tts`) speech synthesis (used by `scripts/speak.sh` for voice-out).
    - `VOICE_TRANSCRIBE_CMD`: Optional path override for transcription command. Defaults to `~/.claude/channels/telegram/transcribe.sh`.
    - `VOICE_SPEAK_CMD`: Optional path override for speech synthesis command. Defaults to the bundled `${CLAUDE_PLUGIN_ROOT}/scripts/speak.sh`.
    - `GEMINI_TTS_VOICE`: Optional prebuilt voice name for Gemini TTS (default: `Aoede`).
    - `VOICE_REPLIES`: Speech synthesis reply policy: `off`, `mirror`, or `always` (default: `mirror`).
- **Threaded Conversations by Default:**
  - Messages arriving in Telegram forum topics or message threads are received with their thread identity (`meta.message_thread_id` and `meta.thread_id`).
  - Outbound paths (`reply`, `ask_user` question cards, `force_reply` prompts for `✏️ Other`, message edits, and emoji reactions) automatically stay in that thread without requiring configuration or opt-in settings.
  - Callers may optionally supply `message_thread_id` (or `thread_id`) explicitly to target a specific thread.
  - Unthreaded chats maintain legacy behaviour with parameters omitted from outbound requests.
- **Native Bot Commands:**
  - Registers the native command menu via `setMyCommands` at `botCommandScopeChat` for each `allowFrom` chat on startup, surviving channel restarts and overriding `all_private_chats` defaults.
  - Registers the single shared command menu for every Ida instance, dynamically built from all installed skills at poller start per the Telegram functional specification FR-8.1.
  - Custom JSON override via `TELEGRAM_BOT_COMMANDS` overrides defaults.
  - Excludes reserved official-plugin commands (`/start`, `/help`, `/status`).
  - Enriches bare menu taps (commands with no arguments) with each command's defined no-argument behavior (`meta.default_action` and `meta.skill`).
  - **Maintainer Note on Skill Renaming:** When an underlying skill is added, removed, or renamed in the framework, the registered menu updates dynamically at startup with no edits required to plugin code. Hyphens in skill names are automatically converted to underscores for valid Telegram command identifiers.
- **Concurrency & Host Locks:**
  - Gated to `IDA_TELEGRAM_ROLE=primary`.
  - Non-primary instances register zero tools, run no poller, and leave hooks inert.
  - Same-host PID locking and exponential 409 Conflict backoff policy.
