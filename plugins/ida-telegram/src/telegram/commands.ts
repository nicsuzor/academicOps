import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { homedir } from "node:os";

export interface TelegramBotCommand {
  command: string;
  description: string;
}

export interface IdaCommandSpec extends TelegramBotCommand {
  skill: string;
  bareAction: string;
}

export interface SkillDiscoveryOptions {
  pluginRoots?: string[];
  skillsDirs?: string[];
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

export const KNOWN_BARE_ACTIONS: Record<string, string> = {
  decide:
    "Invoke /ida:decide: read the '## With you' section of today's daily note and present the first open decision card.",
  q:
    "Invoke /ida:q: if this command replies to a message or follows an uncaptured ask in chat, capture it onto the graph; otherwise ask the user what to capture.",
  mine:
    "Invoke /ida:mine with no argument: pass through all ida-tracked tasks, advance what is due, and report items needing a decision.",
  reconcile:
    "Invoke /ida:reconcile: run wf-reconcile truth maintenance over returned work and update '## With you' in today's daily note.",
  hydrate:
    "Invoke /ida:hydrate: if replying to a message or active topic, extract ambiguous terms and return a PKB shortlist; otherwise ask which terms to hydrate.",
  up:
    "Invoke /ida:up on the user's last correction: identify the structural class, check why existing rules did not fire, and make the structural fix.",
  reify:
    "Invoke /ida:reify: turn the active objective or task into complete dispatchable tasks on the graph.",
  dispatch:
    "Invoke /ida:dispatch: start polecat workers on ready queued tasks on the graph.",
  daily:
    "Invoke /ida:daily: update today's daily note and reply with a scannable run-down of priorities, progress, and open decisions on Telegram.",
  strategize:
    "Invoke /ida:strategize: examine the current topic at strategic altitude across the graph, assess reversibility and effectuation, structure the plan as hypotheses, and interrogate the core question.",
  remember:
    "Invoke /ida:remember: summarise and persist the active discussion's durable facts, decisions, and constraints to the PKB.",
  decompose:
    "Invoke /ida:decompose: break down the current strategic objective into sub-objectives, decision forks, and prerequisites.",
  strategic_review:
    "Invoke /ida:strategic-review: coordinate modular multi-agent review across compliance, quality, and strategic congruence.",
  argument_map:
    "Invoke /ida:argument-map: reconstruct the core argument as Chained Toulmin Argdown with every gap tagged.",
};

export function normalizeCommandName(raw: string): string {
  const withoutSlash = raw.trim().replace(/^\/+/, "");
  const withoutBotMention = withoutSlash.split("@")[0] || "";
  return withoutBotMention.toLowerCase().replace(/-/g, "_").replace(/[^a-z0-9_]/g, "");
}

export function parseSkillMarkdown(
  content: string,
  fallbackName: string
): { name: string; description: string; defaultAction?: string } {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  let name = fallbackName;
  let description = "";
  let defaultAction: string | undefined;

  if (match) {
    const yaml = match[1];
    const nameMatch = yaml.match(/^name:\s*(.+)$/m);
    if (nameMatch) {
      name = nameMatch[1].trim().replace(/^['"]|['"]$/g, "");
    }
    const descMatch = yaml.match(/^description:\s*([\s\S]*?)(?=\r?\n[a-zA-Z0-9_-]+:|$)/m);
    if (descMatch) {
      description = descMatch[1]
        .replace(/^[>|]\s*\n?/, "")
        .replace(/\r?\n\s*/g, " ")
        .trim()
        .replace(/^['"]|['"]$/g, "");
    }
    const actionMatch = yaml.match(/^(?:default_action|bare_action):\s*([\s\S]*?)(?=\r?\n[a-zA-Z0-9_-]+:|$)/m);
    if (actionMatch) {
      defaultAction = actionMatch[1]
        .replace(/^[>|]\s*\n?/, "")
        .replace(/\r?\n\s*/g, " ")
        .trim()
        .replace(/^['"]|['"]$/g, "");
    }
  }

  if (!description) {
    description = `Execute /${name}`;
  }

  // Telegram allows description length 1-256 characters
  if (description.length > 256) {
    description = description.slice(0, 256).trim();
  }

  return { name, description, defaultAction };
}

function parseCustomCommands(customJson: string): TelegramBotCommand[] {
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
    console.error("[ida-telegram] Error parsing custom bot commands JSON:", err);
    return [];
  }
}

/**
 * Discovers installed skills from filesystem roots and builds command specifications.
 * Spec: Telegram functional specification FR-8.1
 */
export function discoverInstalledSkills(options?: SkillDiscoveryOptions): IdaCommandSpec[] {
  const excludedSet = new Set<string>([...RESERVED_COMMANDS, ...WORKER_COMMANDS]);
  const scannedSkillDirs: Array<{ skillDir: string; pluginName: string }> = [];
  const seenSkillPaths = new Set<string>();
  const seenPlugins = new Set<string>();

  // Determine potential search roots in priority order
  const searchRoots: string[] = [];

  if (options?.skillsDirs || options?.pluginRoots) {
    if (options.skillsDirs) searchRoots.push(...options.skillsDirs);
    if (options.pluginRoots) searchRoots.push(...options.pluginRoots);
  } else {
    const envSkillsDir = process.env.SKILLS_DIR || process.env.AOPS_SKILLS_PATH;
    if (envSkillsDir) {
      searchRoots.push(...envSkillsDir.split(/[:;]/).map((s) => s.trim()).filter(Boolean));
    }

    const envPluginRoot = process.env.CLAUDE_PLUGIN_ROOT;
    if (envPluginRoot && existsSync(envPluginRoot)) {
      searchRoots.push(envPluginRoot);
      const parentDir = resolve(envPluginRoot, "..");
      if (existsSync(parentDir)) {
        searchRoots.push(parentDir);
      }
    }

    // Repo relative root (plugins/ida-telegram/src/telegram -> plugins/)
    const repoPluginsDir = resolve(import.meta.dir, "..", "..", "..");
    if (existsSync(repoPluginsDir)) {
      searchRoots.push(repoPluginsDir);
    }
  }

  // Fallback installed seed & container locations if nothing found yet
  const seedMarketplace =
    process.env.AOPS_SEED_MARKETPLACE ||
    (process.env.CLAUDE_PLUGIN_SEED_DIR
      ? join(process.env.CLAUDE_PLUGIN_SEED_DIR, "marketplaces", "academicOps")
      : undefined);
  const userMarketplace = join(homedir(), ".claude", "plugins", "marketplaces", "academicOps");
  const fallbackMarketplaces = [seedMarketplace, userMarketplace].filter((m): m is string => Boolean(m));

  for (const root of searchRoots) {
    if (!existsSync(root)) continue;

    let stat;
    try {
      stat = statSync(root);
    } catch (err) {
      console.error(`[ida-telegram] Error inspecting directory ${root}:`, err);
      continue;
    }
    if (!stat.isDirectory()) continue;

    // Case 1: root itself is a skill directory containing SKILL.md
    if (existsSync(join(root, "SKILL.md")) || existsSync(join(root, "skill.md"))) {
      const canonical = resolve(root);
      if (!seenSkillPaths.has(canonical)) {
        seenSkillPaths.add(canonical);
        scannedSkillDirs.push({ skillDir: root, pluginName: "ida" });
      }
      continue;
    }

    // Case 2: root has a skills/ subdirectory (e.g. plugin directory)
    const directSkillsDir = join(root, "skills");
    if (existsSync(directSkillsDir) && statSync(directSkillsDir).isDirectory()) {
      const pluginName = basename(root).replace(/-(?:claude|agy)$/, "");
      if (seenPlugins.has(pluginName)) continue;
      seenPlugins.add(pluginName);

      try {
        const entries = readdirSync(directSkillsDir);
        for (const entry of entries) {
          const entryDir = join(directSkillsDir, entry);
          if (existsSync(join(entryDir, "SKILL.md")) || existsSync(join(entryDir, "skill.md"))) {
            const canonical = resolve(entryDir);
            if (!seenSkillPaths.has(canonical)) {
              seenSkillPaths.add(canonical);
              scannedSkillDirs.push({ skillDir: entryDir, pluginName });
            }
          }
        }
      } catch (err) {
        console.error(`[ida-telegram] Error reading skills directory ${directSkillsDir}:`, err);
      }
      continue;
    }

    // Case 3: root contains plugin directories (e.g. plugins/ directory) or direct skill subdirectories
    try {
      const subEntries = readdirSync(root);
      for (const sub of subEntries) {
        const subPath = join(root, sub);
        try {
          if (!statSync(subPath).isDirectory()) continue;
        } catch (err) {
          console.error(`[ida-telegram] Error inspecting path ${subPath}:`, err);
          continue;
        }

        const subSkillsDir = join(subPath, "skills");
        if (existsSync(subSkillsDir) && statSync(subSkillsDir).isDirectory()) {
          const pluginName = sub.replace(/-(?:claude|agy)$/, "");
          if (seenPlugins.has(pluginName)) continue;
          seenPlugins.add(pluginName);

          const skillEntries = readdirSync(subSkillsDir);
          for (const s of skillEntries) {
            const skillPath = join(subSkillsDir, s);
            if (existsSync(join(skillPath, "SKILL.md")) || existsSync(join(skillPath, "skill.md"))) {
              const canonical = resolve(skillPath);
              if (!seenSkillPaths.has(canonical)) {
                seenSkillPaths.add(canonical);
                scannedSkillDirs.push({ skillDir: skillPath, pluginName });
              }
            }
          }
        } else if (existsSync(join(subPath, "SKILL.md")) || existsSync(join(subPath, "skill.md"))) {
          // Direct skill subdirectory
          const canonical = resolve(subPath);
          if (!seenSkillPaths.has(canonical)) {
            seenSkillPaths.add(canonical);
            scannedSkillDirs.push({ skillDir: subPath, pluginName: "ida" });
          }
        }
      }
    } catch (err) {
      console.error(`[ida-telegram] Error reading search root ${root}:`, err);
    }
  }

  // If no skills were found from primary locations, check seed marketplaces
  if (scannedSkillDirs.length === 0) {
    for (const marketplace of fallbackMarketplaces) {
      if (!existsSync(marketplace)) continue;
      try {
        const subEntries = readdirSync(marketplace);
        for (const sub of subEntries) {
          const subPath = join(marketplace, sub);
          const subSkillsDir = join(subPath, "skills");
          if (existsSync(subSkillsDir) && statSync(subSkillsDir).isDirectory()) {
            const pluginName = sub.replace(/-(?:claude|agy)$/, "");
            if (seenPlugins.has(pluginName)) continue;
            seenPlugins.add(pluginName);

            const skillEntries = readdirSync(subSkillsDir);
            for (const s of skillEntries) {
              const skillPath = join(subSkillsDir, s);
              if (existsSync(join(skillPath, "SKILL.md")) || existsSync(join(skillPath, "skill.md"))) {
                const canonical = resolve(skillPath);
                if (!seenSkillPaths.has(canonical)) {
                  seenSkillPaths.add(canonical);
                  scannedSkillDirs.push({ skillDir: skillPath, pluginName });
                }
              }
            }
          }
        }
      } catch (err) {
        console.error(`[ida-telegram] Error reading marketplace directory ${marketplace}:`, err);
      }
    }
  }

  // Build command specifications
  const commandMap = new Map<string, IdaCommandSpec>();

  for (const { skillDir, pluginName } of scannedSkillDirs) {
    const skillFilePath = existsSync(join(skillDir, "SKILL.md"))
      ? join(skillDir, "SKILL.md")
      : join(skillDir, "skill.md");

    let content = "";
    try {
      content = readFileSync(skillFilePath, "utf-8");
    } catch (err) {
      console.error(`[ida-telegram] Error reading skill file ${skillFilePath}:`, err);
      continue;
    }

    const { name: rawName, description, defaultAction } = parseSkillMarkdown(content, basename(skillDir));
    const normalizedName = normalizeCommandName(rawName);

    if (!normalizedName || excludedSet.has(normalizedName)) {
      continue;
    }

    let commandName = normalizedName.slice(0, 32);

    // Collision handling: where two plugins ship a skill of the same name, give each a distinct command name
    if (commandMap.has(commandName)) {
      const prefix = normalizeCommandName(pluginName);
      let prefixed = `${prefix}_${commandName}`.slice(0, 32);
      let counter = 2;
      while (commandMap.has(prefixed)) {
        prefixed = `${prefix}_${commandName}`.slice(0, 29) + `_${counter}`;
        counter++;
      }
      commandName = prefixed;
    }

    const skillId = `${pluginName}:${rawName}`;
    const bareAction =
      defaultAction ||
      KNOWN_BARE_ACTIONS[normalizedName] ||
      `Invoke /${skillId}: execute skill with context or prompt user for arguments.`;

    commandMap.set(commandName, {
      command: commandName,
      description,
      skill: skillId,
      bareAction,
    });
  }

  const commands = Array.from(commandMap.values()).sort((a, b) => a.command.localeCompare(b.command));

  // Reporting constraint: Telegram allows at most 100 commands per scope; if skills exceed that, report it
  if (commands.length > 100) {
    console.error(
      `[ida-telegram] Warning: Telegram allows at most 100 commands per scope; found ${commands.length} skills. Exceeds Telegram limit.`
    );
  }

  return commands;
}

export const DEFAULT_IDA_COMMANDS: readonly IdaCommandSpec[] = discoverInstalledSkills();
export const ALL_IDA_COMMANDS: readonly IdaCommandSpec[] = DEFAULT_IDA_COMMANDS;

export function resolveBotCommands(
  customJsonOrDeprecated?: string,
  options?: SkillDiscoveryOptions
): TelegramBotCommand[] {
  if (
    customJsonOrDeprecated &&
    (customJsonOrDeprecated.trim().startsWith("[") || customJsonOrDeprecated.trim().startsWith("{"))
  ) {
    return parseCustomCommands(customJsonOrDeprecated);
  }

  const commandSpecs = discoverInstalledSkills(options);
  return commandSpecs.map(({ command, description }) => ({
    command,
    description,
  }));
}

export function getBareCommandBehavior(
  rawCommand: string,
  options?: SkillDiscoveryOptions
): IdaCommandSpec | undefined {
  const normalized = normalizeCommandName(rawCommand);
  const normalizedUnderscore = normalized.replace(/-/g, "_");

  // Search strictly in discovered skills
  const discovered = discoverInstalledSkills(options);
  return discovered.find((c) => c.command === normalized || c.command === normalizedUnderscore);
}
