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
- **Feedback & Learning:**
  - Inline `👍` and `👎` on replies.
  - Upvotes recorded to trace sinks without waking the agent.
  - Downvotes prompt critique tags (`Too verbose`, `Wrong premise`, etc.) and emit a single `feedback_down` event to invoke `/ida:learn`.
- **Mini App Security & Review:**
  - Loopback-only Bun HTTP server (`127.0.0.1:<port>`) serving `/app/*` and `/api/app/*`.
  - Telegram `initData` HMAC-SHA256 validation with 1-hour expiration and `allowFrom` whitelist check.
  - Permission diff viewer for `Edit`, `Write`, and `Bash` tool approvals.
  - PR diff browser for reviewing changes without directly mutating GitHub.
  - Live Cognitive Anchor tracking current focus, task IDs, delegations, and context window metrics.
- **Voice In & Out:**
  - Voice notes transcribed via pluggable script without spending tool calls.
  - Voice replies via speech synthesis for spoken audio delivery.
- **Native Bot Commands:**
  - Registers `/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, and `/up` via `setMyCommands` at `botCommandScopeChat` for each `allowFrom` chat on startup, surviving channel restarts and overriding `all_private_chats` defaults.
  - Excludes reserved official-plugin commands (`/start`, `/help`, `/status`).
  - Enriches bare menu taps (commands with no arguments) with each command's defined no-argument behavior (`meta.default_action` and `meta.skill`).
- **Concurrency & Host Locks:**
  - Gated to `IDA_TELEGRAM_ROLE=primary`.
  - Non-primary instances register zero tools, run no poller, and leave hooks inert.
  - Same-host PID locking and exponential 409 Conflict backoff policy.
