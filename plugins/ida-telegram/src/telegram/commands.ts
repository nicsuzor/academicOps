export interface TelegramBotCommand {
  command: string;
  description: string;
}

export interface IdaCommandSpec extends TelegramBotCommand {
  skill: string;
  bareAction: string;
}

/**
 * MAINTAINER NOTE:
 * When an underlying skill is renamed (for instance in `plugins/ida/skills/`),
 * remember to update the corresponding Telegram command names and skill mappings
 * in this package (`PRIME_COMMANDS`, `STRATEGIC_COMMANDS`, and associated tests)
 * to keep command menus and bare action dispatches congruent with skill definitions.
 */

/**
 * Commands consumed by the official Telegram plugin that must not be reused
 * for Ida's command menu (kb_ee859e3f).
 */
export const RESERVED_COMMANDS = ["start", "help", "status"] as const;

/**
 * Chosen native Telegram commands for Ida Prime (routine operations, triage, dispatch, tracking):
 * 1. /decide — Walk through open decisions from today's daily note one at a time.
 * 2. /q — Stage 1 intake and capture onto the strategic task graph.
 * 3. /mine — Track a must-not-drop ask across sessions, or pass through tracked tasks.
 * 4. /reconcile — Run wf-reconcile truth maintenance and update today's daily note.
 * 5. /hydrate — Fast disambiguation search over the PKB graph.
 * 6. /up — Step up a level on the last correction and fix the structural class.
 * 7. /reify — Compose dispatchable tasks on the graph from an objective.
 * 8. /dispatch — Start polecat workers on queued tasks already on the graph.
 * 9. /daily — Update today's daily note and reply with a run-down on Telegram.
 */
export const PRIME_COMMANDS: readonly IdaCommandSpec[] = [
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
  {
    command: "reify",
    description: "Compose dispatchable tasks on the graph from an objective",
    skill: "ida:reify",
    bareAction:
      "Invoke /ida:reify: turn the active objective or task into complete dispatchable tasks on the graph.",
  },
  {
    command: "dispatch",
    description: "Start polecat workers on queued tasks already on the graph",
    skill: "ida:dispatch",
    bareAction:
      "Invoke /ida:dispatch: start polecat workers on ready queued tasks on the graph.",
  },
  {
    command: "daily",
    description: "Update the daily note and reply with a run-down on Telegram",
    skill: "ida:daily",
    bareAction:
      "Invoke /ida:daily: update today's daily note and reply with a scannable run-down of priorities, progress, and open decisions on Telegram.",
  },
];

/**
 * Chosen native Telegram commands for Strategic Ida (high-altitude reasoning, decomposition, PKB memory):
 * 1. /strategize — Reason at strategic altitude and interrogate the core question.
 * 2. /remember — Persist facts, decisions, and constraints to the PKB.
 * 3. /decompose — Expand an objective into sub-objectives and decision forks.
 * 4. /q — Stage 1 intake and capture onto the strategic task graph.
 * 5. /hydrate — Disambiguate terms or hydrate context from the PKB.
 * 6. /up — Step up a level on the last correction and fix the class.
 * 7. /plan — Facilitate strategic exploration and structure plans under uncertainty.
 * 8. /strategic_review — Modular multi-agent dialectical review of an artifact.
 * 9. /argument_map — Build a reviewable map of a text's argument in Argdown.
 * 10. /reify — Compose dispatchable tasks on the graph from an objective.
 * 11. /dispatch — Start polecat workers on queued tasks already on the graph.
 * 12. /daily — Update today's daily note and reply with a run-down on Telegram.
 */
export const STRATEGIC_COMMANDS: readonly IdaCommandSpec[] = [
  {
    command: "strategize",
    description: "Reason at strategic altitude and interrogate the core question",
    skill: "ida:strategize",
    bareAction:
      "Invoke /ida:strategize: examine the current topic at strategic altitude, assess reversibility and effectuation, and interrogate the core question.",
  },
  {
    command: "remember",
    description: "Persist facts, decisions, and constraints to the PKB",
    skill: "ida:remember",
    bareAction:
      "Invoke /ida:remember: summarise and persist the active discussion's durable facts, decisions, and constraints to the PKB.",
  },
  {
    command: "decompose",
    description: "Expand an objective into sub-objectives and decision forks",
    skill: "ida:decompose",
    bareAction:
      "Invoke /ida:decompose: break down the current strategic objective into sub-objectives, decision forks, and prerequisites.",
  },
  {
    command: "q",
    description: "Capture an ask or idea onto the strategic task graph",
    skill: "ida:q",
    bareAction:
      "Invoke /ida:q: if this command replies to a message or follows an uncaptured ask in chat, capture it onto the graph; otherwise ask the user what to capture.",
  },
  {
    command: "hydrate",
    description: "Disambiguate terms or hydrate context from the PKB",
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
  {
    command: "plan",
    description: "Facilitate strategic exploration and structure plans under uncertainty",
    skill: "ida:plan",
    bareAction:
      "Invoke /ida:plan: facilitate strategic exploration, structure hypotheses, and assess next steps under uncertainty.",
  },
  {
    command: "strategic_review",
    description: "Modular multi-agent dialectical review of an artifact",
    skill: "ida:strategic-review",
    bareAction:
      "Invoke /ida:strategic-review: coordinate modular multi-agent review across compliance, quality, and strategic congruence.",
  },
  {
    command: "argument_map",
    description: "Build a reviewable map of a text's argument in Argdown",
    skill: "ida:argument-map",
    bareAction:
      "Invoke /ida:argument-map: reconstruct the core argument as Chained Toulmin Argdown with every gap tagged.",
  },
  {
    command: "reify",
    description: "Compose dispatchable tasks on the graph from an objective",
    skill: "ida:reify",
    bareAction:
      "Invoke /ida:reify: turn the active objective or task into complete dispatchable tasks on the graph.",
  },
  {
    command: "dispatch",
    description: "Start polecat workers on queued tasks already on the graph",
    skill: "ida:dispatch",
    bareAction:
      "Invoke /ida:dispatch: start polecat workers on ready queued tasks on the graph.",
  },
  {
    command: "daily",
    description: "Update the daily note and reply with a run-down on Telegram",
    skill: "ida:daily",
    bareAction:
      "Invoke /ida:daily: update today's daily note and reply with a scannable run-down of priorities, progress, and open decisions on Telegram.",
  },
];

export const DEFAULT_IDA_COMMANDS: readonly IdaCommandSpec[] = PRIME_COMMANDS;

export const PERSONA_COMMANDS: Record<string, readonly IdaCommandSpec[]> = {
  prime: PRIME_COMMANDS,
  pauli: PRIME_COMMANDS,
  strategic: STRATEGIC_COMMANDS,
  ida: STRATEGIC_COMMANDS,
  default: PRIME_COMMANDS,
};

export const ALL_IDA_COMMANDS: readonly IdaCommandSpec[] = [
  ...PRIME_COMMANDS,
  ...STRATEGIC_COMMANDS.filter((sc) => !PRIME_COMMANDS.some((pc) => pc.command === sc.command)),
];

export function normalizeCommandName(raw: string): string {
  const withoutSlash = raw.trim().replace(/^\/+/, "");
  const withoutBotMention = withoutSlash.split("@")[0] || "";
  return withoutBotMention.toLowerCase();
}

function parseCustomCommands(customJson: string, persona?: string): TelegramBotCommand[] {
  const reservedSet = new Set<string>(RESERVED_COMMANDS);
  try {
    const parsed = JSON.parse(customJson);
    let list: Array<{ command: string; description: string }> = [];
    if (Array.isArray(parsed)) {
      list = parsed;
    } else if (parsed && typeof parsed === "object") {
      const normPersona = (persona || "default").trim().toLowerCase();
      if (Array.isArray(parsed[normPersona])) {
        list = parsed[normPersona];
      } else if (Array.isArray(parsed["default"])) {
        list = parsed["default"];
      } else if (normPersona === "default" && Array.isArray(parsed["prime"])) {
        list = parsed["prime"];
      }
    }
    return list
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
  } catch {
    return [];
  }
}

export function resolveBotCommands(
  personaOrCustomJson?: string,
  customJson?: string
): TelegramBotCommand[] {
  const normalizedPersona = (personaOrCustomJson || "default").trim().toLowerCase();

  if (customJson && customJson.trim().length > 0) {
    const custom = parseCustomCommands(customJson, normalizedPersona);
    if (custom.length > 0) {
      return custom;
    }
  }

  if (personaOrCustomJson && (personaOrCustomJson.trim().startsWith("[") || personaOrCustomJson.trim().startsWith("{"))) {
    const custom = parseCustomCommands(personaOrCustomJson, "default");
    if (custom.length > 0) {
      return custom;
    }
  }

  const commandSpecs = PERSONA_COMMANDS[normalizedPersona] || DEFAULT_IDA_COMMANDS;
  return commandSpecs.map(({ command, description }) => ({
    command,
    description,
  }));
}

export function getBareCommandBehavior(
  rawCommand: string,
  persona?: string,
  customCommands?: readonly IdaCommandSpec[]
): IdaCommandSpec | undefined {
  const normalized = normalizeCommandName(rawCommand);
  const normalizedUnderscore = normalized.replace(/-/g, "_");
  if (customCommands && customCommands.length > 0) {
    const match = customCommands.find((c) => c.command === normalized || c.command === normalizedUnderscore);
    if (match) return match;
  }
  if (persona) {
    const personaList = PERSONA_COMMANDS[persona.trim().toLowerCase()];
    if (personaList) {
      const match = personaList.find((c) => c.command === normalized || c.command === normalizedUnderscore);
      if (match) return match;
    }
  }
  return ALL_IDA_COMMANDS.find((c) => c.command === normalized || c.command === normalizedUnderscore);
}
