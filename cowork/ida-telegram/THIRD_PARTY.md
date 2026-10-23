# Third-Party Notices and Attribution

The `ida-telegram` plugin incorporates architecture, algorithms, and reference patterns from several open-source projects:

### 1. 2naive/claude-telegram-topics

- **Commit:** `d945146`
- **License:** MIT License
- **Usage:** Entity formatting base (Markdown to Telegram UTF-16 code unit entity spans) and monospace table rendering.

### 2. k1p1l0/claude-telegram-supercharged

- **Commit:** `688e8fc`
- **License:** Apache License 2.0
- **Usage:** Callback multiplexing design reference (secondary send mode excluded).

### 3. qwwiwi/dashi-plugin-claude-code

- **Commit:** `eb26d44`
- **License:** MIT License
- **Usage:** `AskUserQuestion` PreToolUse hook architecture communicating with local Unix domain socket bridge.

### 4. rennf93/cc-tg-hub

- **Commit:** `f4abecc`
- **License:** MIT License
- **Usage:** Telegram Mini App `initData` HMAC-SHA256 validation pattern (adapted with a 1-hour freshness expiration).

### 5. alexei-led/ccgram and jerry12122/Claude-Code-Mini-App

- **Commits:** `alexei-led/ccgram@0b8ae82`, `jerry12122/Claude-Code-Mini-App@861ad73`
- **License:** MIT License
- **Usage:** Mini App approval card layouts and diff visualization views.

### 6. anthropics/claude-plugins-official

- **Commit:** `1e96c6b0`
- **License:** MIT License
- **Usage:** Claude Code Channel MCP protocol specification and tool schema references.
