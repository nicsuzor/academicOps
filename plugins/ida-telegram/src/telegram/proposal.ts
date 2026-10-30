import { readdirSync, readFileSync, existsSync, statSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import {
  PRIME_COMMANDS,
  STRATEGIC_COMMANDS,
  RESERVED_COMMANDS,
  normalizeCommandName,
  type TelegramBotCommand,
  type IdaCommandSpec,
} from "./commands.js";
import type { TelegramBotClient } from "./bot.js";

export type PersonaAllocation = "prime" | "strategic" | "both" | "none";

export interface CandidateCommand {
  command: string;
  description: string;
  skill: string;
  type: "skill" | "workflow" | "custom";
  usageCount: number;
  currentAllocation: PersonaAllocation;
  bareAction: string;
}

export const HEADLESS_COMMANDS = ["pull", "dump"] as const;

export interface DiscoverOptions {
  pluginRoots?: string[];
  workflowsDirs?: string[];
  telemetryUsage?: Record<string, number>;
  currentCommands?: {
    prime?: readonly IdaCommandSpec[];
    strategic?: readonly IdaCommandSpec[];
  };
}

/**
 * Normalizes a raw skill/workflow identifier to a Telegram-compliant command name (lowercase snake_case).
 */
export function normalizeSkillToCommand(rawName: string): string {
  return normalizeCommandName(rawName).replace(/-/g, "_");
}

/**
 * Parses frontmatter fields (name, description, title) from a markdown string.
 */
function parseFrontmatter(content: string): { name?: string; description?: string; title?: string } {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return {};
  const lines = match[1].split(/\r?\n/);
  const result: Record<string, string> = {};
  for (const line of lines) {
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      let value = line.slice(colonIdx + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      result[key] = value;
    }
  }
  return result;
}

/**
 * Discovers candidate skills and workflows, excluding reserved and headless commands,
 * and normalizing identifiers to snake_case for Telegram Bot API constraints.
 */
export async function discoverCandidates(options: DiscoverOptions = {}): Promise<CandidateCommand[]> {
  const primeSpecs = options.currentCommands?.prime ?? PRIME_COMMANDS;
  const strategicSpecs = options.currentCommands?.strategic ?? STRATEGIC_COMMANDS;
  const usage = options.telemetryUsage ?? {};

  const reservedSet = new Set<string>([...RESERVED_COMMANDS, ...HEADLESS_COMMANDS]);
  const candidatesMap = new Map<string, CandidateCommand>();

  // Determine current allocation for a command name
  function determineAllocation(cmd: string): PersonaAllocation {
    const inPrime = primeSpecs.some((s) => s.command === cmd);
    const inStrategic = strategicSpecs.some((s) => s.command === cmd);
    if (inPrime && inStrategic) return "both";
    if (inPrime) return "prime";
    if (inStrategic) return "strategic";
    return "none";
  }

  function getExistingSpec(cmd: string): IdaCommandSpec | undefined {
    return primeSpecs.find((s) => s.command === cmd) ?? strategicSpecs.find((s) => s.command === cmd);
  }

  function getUsage(skillId: string, cmd: string): number {
    return (
      usage[skillId] ??
      usage[cmd] ??
      usage[`ida:${skillId}`] ??
      usage[`ida:${cmd}`] ??
      usage[cmd.replace(/_/g, "-")] ??
      0
    );
  }

  // 1. Scan plugin roots for skills
  const pluginRoots = options.pluginRoots ?? [
    resolve(process.cwd(), "plugins", "ida"),
    resolve(process.cwd(), "plugins", "ida-telegram"),
    resolve(process.cwd(), "plugins", "tools"),
    resolve(process.cwd(), "plugins", "rbg"),
  ];

  for (const root of pluginRoots) {
    const skillsDir = join(root, "skills");
    if (!existsSync(skillsDir) || !statSync(skillsDir).isDirectory()) continue;

    try {
      const entries = readdirSync(skillsDir, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const skillMd = join(skillsDir, entry.name, "SKILL.md");
        if (!existsSync(skillMd)) continue;

        try {
          const content = readFileSync(skillMd, "utf-8");
          const fm = parseFrontmatter(content);
          const rawName = fm.name || entry.name;
          const cmdName = normalizeSkillToCommand(rawName);

          if (reservedSet.has(cmdName)) continue;

          const desc = fm.description || `Execute skill ${rawName}`;
          const existing = getExistingSpec(cmdName);
          const skillId = `ida:${rawName}`;

          candidatesMap.set(cmdName, {
            command: cmdName,
            description: existing?.description || desc,
            skill: skillId,
            type: "skill",
            usageCount: getUsage(rawName, cmdName),
            currentAllocation: determineAllocation(cmdName),
            bareAction: existing?.bareAction || `Invoke /${skillId}: ${desc}`,
          });
        } catch {
          // ignore read error
        }
      }
    } catch {
      // ignore readdir error
    }
  }

  // 2. Scan workflows directories
  const workflowsDirs = options.workflowsDirs ?? [
    resolve(process.cwd(), "plugins", "ida", "skills", "workflow-library", "workflows"),
    resolve(process.cwd(), ".agents", "templates"),
  ];

  for (const wfDir of workflowsDirs) {
    if (!existsSync(wfDir) || !statSync(wfDir).isDirectory()) continue;

    try {
      const files = readdirSync(wfDir);
      for (const file of files) {
        if (!file.endsWith(".md")) continue;
        const filePath = join(wfDir, file);
        try {
          const content = readFileSync(filePath, "utf-8");
          const fm = parseFrontmatter(content);
          const stem = file.replace(/\.md$/, "");
          const cmdName = normalizeSkillToCommand(stem);

          if (reservedSet.has(cmdName)) continue;

          const desc = fm.description || fm.title || `Execute workflow ${stem}`;
          const existing = getExistingSpec(cmdName);

          if (!candidatesMap.has(cmdName)) {
            candidatesMap.set(cmdName, {
              command: cmdName,
              description: existing?.description || desc,
              skill: stem,
              type: "workflow",
              usageCount: getUsage(stem, cmdName),
              currentAllocation: determineAllocation(cmdName),
              bareAction: existing?.bareAction || `Execute workflow ${stem}`,
            });
          }
        } catch {
          // ignore read error
        }
      }
    } catch {
      // ignore readdir error
    }
  }

  // 3. Ensure configured commands are present if not already added
  for (const spec of [...primeSpecs, ...strategicSpecs]) {
    const cmd = spec.command;
    if (reservedSet.has(cmd)) continue;
    if (!candidatesMap.has(cmd)) {
      candidatesMap.set(cmd, {
        command: cmd,
        description: spec.description,
        skill: spec.skill,
        type: "skill",
        usageCount: getUsage(spec.skill, cmd),
        currentAllocation: determineAllocation(cmd),
        bareAction: spec.bareAction,
      });
    }
  }

  return Array.from(candidatesMap.values());
}

/**
 * Aggregates invocation counts from OpenTelemetry spans for skills and Telegram bot commands.
 */
export function aggregateTelemetryUsage(
  spans: Array<{ name?: string; attributes?: Record<string, unknown> }>
): Record<string, number> {
  const counts: Record<string, number> = {};

  function recordSpan(rawKey: string) {
    const keys = new Set<string>();
    const trimmed = rawKey.trim();
    keys.add(trimmed);
    const unPrefixed = trimmed.replace(/^ida:/, "");
    keys.add(unPrefixed);
    const norm = normalizeSkillToCommand(unPrefixed);
    keys.add(norm);
    const normRaw = normalizeSkillToCommand(trimmed);
    keys.add(normRaw);

    for (const k of keys) {
      if (k) {
        counts[k] = (counts[k] || 0) + 1;
      }
    }
  }

  for (const span of spans) {
    const name = span.name || "";
    const attrs = span.attributes || {};

    // 1. Skill tool calls
    if (typeof attrs["skill.id"] === "string") {
      recordSpan(attrs["skill.id"]);
    } else if (name.startsWith("Skill:")) {
      const match = name.match(/^Skill:\s*([\w:-]+)/);
      if (match) recordSpan(match[1]);
    }

    // 2. Telegram bot commands
    if (attrs.event === "bot_command" && typeof attrs.command === "string") {
      recordSpan(attrs.command.replace(/^\//, ""));
    }
  }

  return counts;
}

/**
 * Formats candidate skills and workflows into a readable proposal matrix.
 * Enforces Telegram Bot API invariant of <= 100 commands per scope.
 */
export function formatProposalMatrix(candidates: CandidateCommand[]): string {
  const lines: string[] = [];

  const primeCount = candidates.filter((c) => c.currentAllocation === "prime" || c.currentAllocation === "both").length;
  const strategicCount = candidates.filter(
    (c) => c.currentAllocation === "strategic" || c.currentAllocation === "both"
  ).length;

  lines.push("## Telegram Bot Menu Proposal");
  lines.push("");
  lines.push(
    `Candidate pool: **${candidates.length} commands** | Current allocations: **Prime: ${primeCount}**, **Strategic: ${strategicCount}**`
  );
  lines.push("");

  if (candidates.length > 100 || primeCount > 100 || strategicCount > 100) {
    lines.push(
      "> [!WARNING] **Telegram API Limit Alert:** Bot command menus cannot exceed 100 commands per persona/scope (Telegram API invariant). High-priority selections should be chosen."
    );
    lines.push("");
  }

  lines.push("| Command | Type | Usage | Allocation | Description |");
  lines.push("| :--- | :--- | :---: | :---: | :--- |");

  const allocationLabel: Record<PersonaAllocation, string> = {
    prime: "[Prime]",
    strategic: "[Strategic]",
    both: "[Both]",
    none: "[None]",
  };

  for (const candidate of candidates) {
    lines.push(
      `| \`/${candidate.command}\` | ${candidate.type} | ${candidate.usageCount} | ${allocationLabel[candidate.currentAllocation]} | ${candidate.description} |`
    );
  }

  lines.push("");
  lines.push("### Allocation Options per Command:");
  lines.push("- **Prime only** (`prime`): Allocate exclusively to Ida Prime.");
  lines.push("- **Strategic only** (`strategic`): Allocate exclusively to Strategic Ida (Ida Actual).");
  lines.push("- **Both** (`both`): Register on both bot personas.");
  lines.push("- **None** (`none`): Omit from Telegram command menus.");

  return lines.join("\n");
}

/**
 * Parses user input (structured map or free-text natural language) and returns updated allocations.
 */
export function parseAllocationReply(
  input: string | Record<string, string>,
  currentAllocations: Record<string, PersonaAllocation> = {}
): Record<string, PersonaAllocation> {
  const result: Record<string, PersonaAllocation> = { ...currentAllocations };

  if (typeof input === "object" && input !== null) {
    for (const [key, val] of Object.entries(input)) {
      const normCmd = normalizeSkillToCommand(key);
      const normVal = String(val).toLowerCase().trim() as PersonaAllocation;
      if (["prime", "strategic", "both", "none"].includes(normVal)) {
        result[normCmd] = normVal;
      }
    }
    return result;
  }

  const text = String(input);
  // Split on delimiters (commas, semicolons, 'and', newlines)
  const segments = text.split(/(?:,|\n|;|\band\b)+/i);

  for (const seg of segments) {
    const s = seg.trim().toLowerCase();
    if (!s) continue;

    // Pattern: remove <cmd> (from <bot> / everywhere)
    const removeMatch = s.match(/(?:remove|delete|drop)\s+([a-z0-9_-]+)/);
    if (removeMatch) {
      const cmd = normalizeSkillToCommand(removeMatch[1]);
      result[cmd] = "none";
      continue;
    }

    // Pattern: put/add/move <cmd> on/to/in <target>
    const putMatch = s.match(/(?:put|add|move|set|assign)\s+([a-z0-9_-]+)\s+(?:on|to|in|for)\s+(both|prime(?:\s+only)?|strategic(?:\s+only)?|none)/);
    if (putMatch) {
      const cmd = normalizeSkillToCommand(putMatch[1]);
      const target = putMatch[2].startsWith("prime") ? "prime" : putMatch[2].startsWith("strategic") ? "strategic" : (putMatch[2] as PersonaAllocation);
      result[cmd] = target;
      continue;
    }

    // Pattern: <target> (only) for/to/on <cmd>
    const targetFirstMatch = s.match(/(both|prime(?:\s+only)?|strategic(?:\s+only)?|none)\s+(?:for|to|on)\s+([a-z0-9_-]+)/);
    if (targetFirstMatch) {
      const target = targetFirstMatch[1].startsWith("prime") ? "prime" : targetFirstMatch[1].startsWith("strategic") ? "strategic" : (targetFirstMatch[1] as PersonaAllocation);
      const cmd = normalizeSkillToCommand(targetFirstMatch[2]);
      result[cmd] = target;
      continue;
    }

    // Pattern: <cmd> on/to/for/in <target>
    const cmdFirstMatch = s.match(/([a-z0-9_-]+)\s+(?:on|to|for|in|as)\s+(both|prime(?:\s+only)?|strategic(?:\s+only)?|none)/);
    if (cmdFirstMatch) {
      const cmd = normalizeSkillToCommand(cmdFirstMatch[1]);
      const target = cmdFirstMatch[2].startsWith("prime") ? "prime" : cmdFirstMatch[2].startsWith("strategic") ? "strategic" : (cmdFirstMatch[2] as PersonaAllocation);
      result[cmd] = target;
      continue;
    }

    // Pattern: <cmd>: <target>
    const colonMatch = s.match(/([a-z0-9_-]+)\s*:\s*(both|prime(?:\s+only)?|strategic(?:\s+only)?|none)/);
    if (colonMatch) {
      const cmd = normalizeSkillToCommand(colonMatch[1]);
      const target = colonMatch[2].startsWith("prime") ? "prime" : colonMatch[2].startsWith("strategic") ? "strategic" : (colonMatch[2] as PersonaAllocation);
      result[cmd] = target;
      continue;
    }
  }

  return result;
}

/**
 * Validates custom and composite command specifications against Telegram API constraints.
 */
export function validateCustomCommand(spec: {
  command?: string;
  description?: string;
  skill?: string;
  bareAction?: string;
}): { valid: boolean; error?: string; commandSpec?: IdaCommandSpec } {
  if (!spec.command || typeof spec.command !== "string") {
    return { valid: false, error: "Command name is required." };
  }

  const rawCmd = spec.command.trim().replace(/^\/+/, "");
  if (!rawCmd) {
    return { valid: false, error: "Command name cannot be empty." };
  }

  if (rawCmd.length > 32) {
    return { valid: false, error: "Command name exceeds Telegram limit of 32 characters." };
  }

  if (!/^[a-z0-9_]{1,32}$/.test(rawCmd)) {
    return {
      valid: false,
      error: "Command name must be 1-32 characters of lowercase alphanumeric and underscores (/^[a-z0-9_]{1,32}$/).",
    };
  }

  const reservedSet = new Set<string>(RESERVED_COMMANDS);
  if (reservedSet.has(rawCmd)) {
    return { valid: false, error: `Command '${rawCmd}' is reserved and cannot be registered.` };
  }

  if (!spec.description || typeof spec.description !== "string" || spec.description.trim().length === 0) {
    return { valid: false, error: "Command description is required (1-256 characters)." };
  }

  const desc = spec.description.trim();
  if (desc.length > 256) {
    return { valid: false, error: "Command description exceeds Telegram limit of 256 characters." };
  }

  if (!spec.bareAction || typeof spec.bareAction !== "string" || spec.bareAction.trim().length === 0) {
    return { valid: false, error: "Command bareAction execution behavior is required." };
  }

  const commandSpec: IdaCommandSpec = {
    command: rawCmd,
    description: desc,
    skill: spec.skill || `ida:${rawCmd}`,
    bareAction: spec.bareAction.trim(),
  };

  return { valid: true, commandSpec };
}

/**
 * Persists dynamic bot command configurations to disk so they survive restarts.
 */
export async function persistBotCommands(
  stateDirOrPath: string,
  commands: Record<string, TelegramBotCommand[] | IdaCommandSpec[]>
): Promise<void> {
  const filePath = stateDirOrPath.endsWith(".json") ? stateDirOrPath : join(stateDirOrPath, "commands.json");
  const dir = stateDirOrPath.endsWith(".json") ? resolve(stateDirOrPath, "..") : stateDirOrPath;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  writeFileSync(filePath, JSON.stringify(commands, null, 2), "utf-8");
}

/**
 * Loads persisted bot command configurations from disk.
 */
export async function loadPersistedBotCommands(
  stateDirOrPath: string
): Promise<Record<string, TelegramBotCommand[]> | null> {
  const filePath = stateDirOrPath.endsWith(".json") ? stateDirOrPath : join(stateDirOrPath, "commands.json");
  if (!existsSync(filePath)) {
    return null;
  }
  try {
    const raw = readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Synchronizes live menus by calling Telegram Bot API setMyCommands across authorized chats.
 */
export async function syncLiveMenus(
  botClients: TelegramBotClient | Record<string, TelegramBotClient>,
  commandsByPersona: Record<string, TelegramBotCommand[]>
): Promise<Record<string, boolean>> {
  const results: Record<string, boolean> = {};

  if ("registerCommands" in botClients) {
    // Single client instance
    const persona = "default";
    const cmds = commandsByPersona[persona] || commandsByPersona["prime"] || Object.values(commandsByPersona)[0] || [];
    results[persona] = await botClients.registerCommands(undefined, cmds);
    return results;
  }

  for (const [persona, client] of Object.entries(botClients)) {
    const cmds = commandsByPersona[persona] || [];
    if (cmds.length > 0) {
      results[persona] = await client.registerCommands(persona, cmds);
    } else {
      results[persona] = true;
    }
  }

  return results;
}
