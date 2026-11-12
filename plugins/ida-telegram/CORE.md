# ida-telegram Plugin Core

- **Channel Protocol**: Provides Telegram channel integration; all conversational messages and status updates route through the Telegram bridge.
- **Skill Loading**: Every agent with a Telegram channel must load the `telegram` skill (`ida-telegram:telegram`) at startup before sending its first reply.
- **Formatting**: Use progressive disclosure with expandable blockquotes for lengthy details; keep top-level channel messages concise (≤ 3 bullets).
- **Interactive Questions**: User questions must use the `AskUserQuestion` hook/tool; questions are dispatched to the Telegram Mini App broker.
- **Reactions & Status**: Apply the `telegram` skill's reaction legend and status emoji to every message received from the user and every message sent back. The legend remains defined exclusively in the `telegram` skill without bespoke allowlists.
