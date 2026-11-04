export interface TelegramBotCommand {
  command: string;
  description: string;
}

/**
 * Commands consumed by the official Telegram plugin that must not be reused
 * for Ida's command menu (Telegram functional specification FR-8.1).
 */
export const RESERVED_COMMANDS = ["start", "help", "status"] as const;

/**
 * Headless worker lifecycle commands that must never appear in conversational menus
 * per headless-workers.md and the Telegram functional specification FR-8.1.
 */
export const WORKER_COMMANDS = ["pull", "dump"] as const;

export function normalizeCommandName(raw: string): string {
  const withoutSlash = raw.trim().replace(/^\/+/, "");
  const withoutBotMention = withoutSlash.split("@")[0] || "";
  return withoutBotMention.toLowerCase().replace(/-/g, "_").replace(/[^a-z0-9_]/g, "");
}

/**
 * Resolves the native command menu from the operator's configured JSON list
 * (`TELEGRAM_BOT_COMMANDS`). The plugin builds no menu of its own: what each
 * command does is left to the agent's instructions. Unset or invalid config
 * yields an empty menu.
 */
export function resolveBotCommands(customJson?: string): TelegramBotCommand[] {
  if (!customJson || !customJson.trim()) return [];
  const excludedSet = new Set<string>([...RESERVED_COMMANDS, ...WORKER_COMMANDS]);
  try {
    const parsed = JSON.parse(customJson) as Array<{ command: string; description: string }>;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((entry) => ({
        command: normalizeCommandName(entry.command),
        description: String(entry.description || "").trim(),
      }))
      .filter(
        (entry) =>
          /^[a-z0-9_]{1,32}$/.test(entry.command) &&
          !excludedSet.has(entry.command) &&
          entry.description.length >= 1 &&
          entry.description.length <= 256
      );
  } catch (err) {
    console.error("[ida-telegram] Error parsing TELEGRAM_BOT_COMMANDS JSON:", err);
    return [];
  }
}
