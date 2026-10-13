export interface TelegramBotCommand {
  command: string;
  description: string;
}

export interface IdaCommandSpec extends TelegramBotCommand {
  skill: string;
  bareAction: string;
}

/**
 * Commands consumed by the official Telegram plugin that must not be reused
 * for Ida's command menu (kb_ee859e3f).
 */
export const RESERVED_COMMANDS = ["start", "help", "status"] as const;

/**
 * Chosen native Telegram commands for Ida (aops_telegram_native_commands, FR-8.1):
 *
 * 1. /decide — Walk through open decisions from today's daily note one at a time
 *    (replaces the retired /gather and /morning-decisions per aops_8949023b).
 * 2. /q — Stage 1 intake and capture onto the strategic task graph.
 * 3. /mine — Track a must-not-drop ask across sessions, or pass through tracked tasks.
 * 4. /reconcile — Run wf-reconcile truth maintenance and update today's daily note.
 * 5. /hydrate — Fast disambiguation search over the PKB graph.
 * 6. /up — Step up a level on the last correction and fix the structural class.
 */
export const DEFAULT_IDA_COMMANDS: readonly IdaCommandSpec[] = [
  {
    command: "decide",
    description: "Walk through open decisions from today's daily note one at a time",
    skill: "ida:decide",
    bareAction:
      "Invoke /ida:decide: read the '## With you' section of today's daily note and present the first open decision card.",
  },
  {
    command: "q",
    description: "Capture an ask or idea onto the strategic task graph",
    skill: "ida:q",
    bareAction:
      "Invoke /ida:q: if this command replies to a message or follows an uncaptured ask in chat, capture it onto the graph; otherwise ask the user what to capture.",
  },
  {
    command: "mine",
    description: "Track a must-not-drop ask or pass through tracked tasks",
    skill: "ida:mine",
    bareAction:
      "Invoke /ida:mine with no argument: pass through all ida-tracked tasks, advance what is due, and report items needing a decision.",
  },
  {
    command: "reconcile",
    description: "Reconcile the task graph and update today's daily note",
    skill: "ida:reconcile",
    bareAction:
      "Invoke /ida:reconcile: run wf-reconcile truth maintenance over returned work and update '## With you' in today's daily note.",
  },
  {
    command: "hydrate",
    description: "Disambiguate terms or hydrate current conversation context",
    skill: "ida:hydrate",
    bareAction:
      "Invoke /ida:hydrate: if replying to a message or active topic, extract ambiguous terms and return a PKB shortlist; otherwise ask which terms to hydrate.",
  },
  {
    command: "up",
    description: "Step up a level on the last correction and fix the class",
    skill: "ida:up",
    bareAction:
      "Invoke /ida:up on the user's last correction: identify the structural class, check why existing rules did not fire, and make the structural fix.",
  },
];

export function normalizeCommandName(raw: string): string {
  const withoutSlash = raw.trim().replace(/^\/+/, "");
  const withoutBotMention = withoutSlash.split("@")[0] || "";
  return withoutBotMention.toLowerCase();
}

export function resolveBotCommands(customJson?: string): TelegramBotCommand[] {
  const reservedSet = new Set<string>(RESERVED_COMMANDS);

  if (customJson && customJson.trim().length > 0) {
    const parsed = JSON.parse(customJson) as Array<{ command: string; description: string }>;
    return parsed
      .map((entry) => ({
        command: normalizeCommandName(entry.command),
        description: String(entry.description || "").trim(),
      }))
      .filter(
        (entry) =>
          /^[a-z0-9_]{1,32}$/.test(entry.command) &&
          !reservedSet.has(entry.command) &&
          entry.description.length >= 1 &&
          entry.description.length <= 256
      );
  }

  return DEFAULT_IDA_COMMANDS.map(({ command, description }) => ({
    command,
    description,
  }));
}

export function getBareCommandBehavior(rawCommand: string): IdaCommandSpec | undefined {
  const normalized = normalizeCommandName(rawCommand);
  return DEFAULT_IDA_COMMANDS.find((c) => c.command === normalized);
}
