# ida-telegram Plugin Core

- **Channel Protocol**: Provides Telegram channel integration; all conversational messages and status updates route through the Telegram bridge.
- **Formatting**: Use progressive disclosure with expandable blockquotes for lengthy details; keep top-level channel messages concise (≤ 3 bullets).
- **Interactive Questions**: User questions must use the `AskUserQuestion` hook/tool; questions are dispatched to the Telegram Mini App broker.
- **Reactions & Status**: Use `ida-telegram:telegram` for standard reaction legends and emoji status indicators without bespoke allowlists.
