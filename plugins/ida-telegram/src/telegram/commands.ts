import { existsSync, readdirSync, readFileSync, realpathSync } from "node:fs";
import { join, basename, dirname, resolve } from "node:path";
import { homedir } from "node:os";

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
  return withoutBotMention
    .toLowerCase()
    .replace(/-/g, "_")
    .replace(/[^a-z0-9_]/g, "")
    .slice(0, 32);
}

export interface SkillDiscoveryOptions {
  projectDir?: string;
  claudeConfigDir?: string;
  pluginRoot?: string;
  homeDir?: string;
  env?: NodeJS.ProcessEnv;
}

interface DiscoveredSkillCandidate {
  skillDir: string;
  skillFile: string;
  sourcePrefix: string;
}

export function parseSkillFrontmatter(content: string): { name?: string; description?: string } | null {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const yaml = match[1];

  let name: string | undefined;
  let description: string | undefined;

  const lines = yaml.split(/\r?\n/);
  let currentKey: string | null = null;
  let currentValLines: string[] = [];

  const flushKey = () => {
    if (!currentKey) return;
    let val = currentValLines.join("\n").trim();
    if (
      (val.startsWith('"') && val.endsWith('"') && val.length >= 2) ||
      (val.startsWith("'") && val.endsWith("'") && val.length >= 2)
    ) {
      val = val.slice(1, -1);
    }
    if (currentKey === "name") {
      name = val;
    } else if (currentKey === "description") {
      description = val;
    }
  };

  for (const line of lines) {
    const keyMatch = line.match(/^([a-zA-Z0-9_-]+)\s*:\s*(.*)$/);
    if (keyMatch) {
      flushKey();
      currentKey = keyMatch[1];
      const val = keyMatch[2].trim();
      if (val === "|" || val === ">") {
        currentValLines = [];
      } else {
        currentValLines = [val];
      }
    } else if (currentKey && (line.startsWith("  ") || line.startsWith("\t"))) {
      currentValLines.push(line.trim());
    }
  }
  flushKey();

  return { name, description };
}

function scanSkillsSubdirs(parentSkillsDir: string, sourcePrefix: string): DiscoveredSkillCandidate[] {
  const results: DiscoveredSkillCandidate[] = [];
  if (!existsSync(parentSkillsDir)) return results;
  try {
    const entries = readdirSync(parentSkillsDir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory() || entry.isSymbolicLink()) {
        const skillDir = join(parentSkillsDir, entry.name);
        const skillFile = join(skillDir, "SKILL.md");
        if (existsSync(skillFile)) {
          results.push({ skillDir, skillFile, sourcePrefix });
        }
      }
    }
  } catch (err) {
    console.error(`[ida-telegram] Error reading skills directory ${parentSkillsDir}:`, err);
  }
  return results;
}

function scanPluginCacheDir(cacheDir: string): DiscoveredSkillCandidate[] {
  const results: DiscoveredSkillCandidate[] = [];
  if (!existsSync(cacheDir)) return results;
  try {
    const marketplaces = readdirSync(cacheDir, { withFileTypes: true });
    for (const mp of marketplaces) {
      if (!mp.isDirectory()) continue;
      const mpDir = join(cacheDir, mp.name);
      const plugins = readdirSync(mpDir, { withFileTypes: true });
      for (const p of plugins) {
        if (!p.isDirectory()) continue;
        const pDir = join(mpDir, p.name);
        const versions = readdirSync(pDir, { withFileTypes: true });
        for (const v of versions) {
          if (!v.isDirectory()) continue;
          const skillsDir = join(pDir, v.name, "skills");
          results.push(...scanSkillsSubdirs(skillsDir, p.name));
        }
      }
    }
  } catch (err) {
    console.error(`[ida-telegram] Error reading plugin cache directory ${cacheDir}:`, err);
  }
  return results;
}

function scanInstalledPluginsFile(jsonPath: string): DiscoveredSkillCandidate[] {
  const results: DiscoveredSkillCandidate[] = [];
  if (!existsSync(jsonPath)) return results;
  try {
    const raw = readFileSync(jsonPath, "utf-8");
    const data = JSON.parse(raw);
    const plugins = data.plugins || {};
    for (const [key, entries] of Object.entries(plugins)) {
      const prefix = key.split("@")[0] || key;
      if (Array.isArray(entries)) {
        for (const entry of entries) {
          if (entry && typeof entry === "object" && (entry as { installPath?: string }).installPath) {
            results.push(...scanSkillsSubdirs(join((entry as { installPath: string }).installPath, "skills"), prefix));
          }
        }
      } else if (entries && typeof entries === "object" && (entries as { installPath?: string }).installPath) {
        results.push(...scanSkillsSubdirs(join((entries as { installPath: string }).installPath, "skills"), prefix));
      }
    }
  } catch (err) {
    console.error(`[ida-telegram] Error reading installed plugins file ${jsonPath}:`, err);
  }
  return results;
}

function scanKnownMarketplacesFile(jsonPath: string): DiscoveredSkillCandidate[] {
  const results: DiscoveredSkillCandidate[] = [];
  if (!existsSync(jsonPath)) return results;
  try {
    const raw = readFileSync(jsonPath, "utf-8");
    const data = JSON.parse(raw);
    for (const [, mpVal] of Object.entries<any>(data)) {
      const loc = mpVal?.installLocation || mpVal?.source?.path;
      if (loc && existsSync(loc)) {
        const pluginsSubdir = join(loc, "plugins");
        if (existsSync(pluginsSubdir)) {
          const pEntries = readdirSync(pluginsSubdir, { withFileTypes: true });
          for (const pe of pEntries) {
            if (pe.isDirectory()) {
              const prefix = pe.name.replace(/-(?:claude|agy)$/, "");
              results.push(...scanSkillsSubdirs(join(pluginsSubdir, pe.name, "skills"), prefix));
            }
          }
        }
        const topEntries = readdirSync(loc, { withFileTypes: true });
        for (const te of topEntries) {
          if (te.isDirectory() && te.name !== "plugins") {
            const prefix = te.name.replace(/-(?:claude|agy)$/, "");
            results.push(...scanSkillsSubdirs(join(loc, te.name, "skills"), prefix));
          }
        }
      }
    }
  } catch (err) {
    console.error(`[ida-telegram] Error reading known marketplaces file ${jsonPath}:`, err);
  }
  return results;
}

export function discoverSkills(options?: SkillDiscoveryOptions): TelegramBotCommand[] {
  const home = options?.homeDir || (options?.claudeConfigDir ? dirname(options.claudeConfigDir) : homedir());
  const projectDir = options?.projectDir || options?.env?.CLAUDE_PROJECT_DIR || process.cwd();
  const claudeConfigDir = options?.claudeConfigDir || options?.env?.CLAUDE_CONFIG_DIR || join(home, ".claude");
  const defaultPluginRoot = !options?.projectDir && !options?.claudeConfigDir ? resolve(import.meta.dir, "..", "..") : undefined;
  const pluginRoot = options?.pluginRoot || options?.env?.CLAUDE_PLUGIN_ROOT || defaultPluginRoot;

  const candidates: DiscoveredSkillCandidate[] = [];

  // 1. Project-local and Ida skills: <projectDir>/.agents/skills and <projectDir>/.claude/skills
  candidates.push(...scanSkillsSubdirs(join(projectDir, ".agents", "skills"), "project"));
  candidates.push(...scanSkillsSubdirs(join(projectDir, ".claude", "skills"), "project"));

  // 2. User skills: <claudeConfigDir>/skills and ~/.agents/skills
  candidates.push(...scanSkillsSubdirs(join(claudeConfigDir, "skills"), "user"));
  candidates.push(...scanSkillsSubdirs(join(home, ".agents", "skills"), "user"));

  // 3. Installed plugin skills
  if (pluginRoot && existsSync(pluginRoot)) {
    const selfPrefix = basename(pluginRoot).replace(/-(?:claude|agy)$/, "");
    candidates.push(...scanSkillsSubdirs(join(pluginRoot, "skills"), selfPrefix));
    const parent = dirname(pluginRoot);
    if (existsSync(parent)) {
      try {
        const siblings = readdirSync(parent, { withFileTypes: true });
        for (const sib of siblings) {
          if (sib.isDirectory() && join(parent, sib.name) !== pluginRoot && sib.name !== "cache") {
            const sibPrefix = sib.name.replace(/-(?:claude|agy)$/, "");
            candidates.push(...scanSkillsSubdirs(join(parent, sib.name, "skills"), sibPrefix));
          }
        }
      } catch (err) {
        console.error(`[ida-telegram] Error reading sibling plugin directory ${parent}:`, err);
      }
    }
  }

  // Versioned plugin cache
  candidates.push(...scanPluginCacheDir(join(claudeConfigDir, "plugins", "cache")));
  if (pluginRoot) {
    const parent = dirname(pluginRoot);
    candidates.push(...scanPluginCacheDir(join(parent, "cache")));
    const grandParent = dirname(dirname(parent));
    if (basename(grandParent) === "cache") {
      candidates.push(...scanPluginCacheDir(grandParent));
    }
  }

  // Plugins in installed_plugins.json and known_marketplaces.json
  candidates.push(...scanInstalledPluginsFile(join(claudeConfigDir, "plugins", "installed_plugins.json")));
  candidates.push(...scanKnownMarketplacesFile(join(claudeConfigDir, "plugins", "known_marketplaces.json")));

  // Repository plugins: <projectDir>/plugins/*/skills
  const repoPluginsDir = join(projectDir, "plugins");
  if (existsSync(repoPluginsDir)) {
    try {
      const pEntries = readdirSync(repoPluginsDir, { withFileTypes: true });
      for (const pe of pEntries) {
        if (pe.isDirectory()) {
          const prefix = pe.name.replace(/-(?:claude|agy)$/, "");
          candidates.push(...scanSkillsSubdirs(join(repoPluginsDir, pe.name, "skills"), prefix));
        }
      }
    } catch (err) {
      console.error(`[ida-telegram] Error reading repository plugins directory ${repoPluginsDir}:`, err);
    }
  }

  const excludedSet = new Set<string>([...RESERVED_COMMANDS, ...WORKER_COMMANDS]);
  const seenPaths = new Set<string>();
  const registeredCommands = new Map<string, TelegramBotCommand>();

  for (const candidate of candidates) {
    const realSkillDir = realpathSync(candidate.skillDir);
    if (seenPaths.has(realSkillDir)) {
      continue;
    }
    seenPaths.add(realSkillDir);

    const content = readFileSync(candidate.skillFile, "utf-8");

    const parsed = parseSkillFrontmatter(content);
    if (!parsed) continue;

    const rawDesc = parsed.description?.trim();
    if (!rawDesc) {
      console.warn(`[ida-telegram] Skill in ${candidate.skillDir} is missing a non-empty description, skipping.`);
      continue;
    }

    const description = rawDesc.slice(0, 256);
    const skillName = parsed.name?.trim() || basename(candidate.skillDir);
    let command = normalizeCommandName(skillName);

    if (!command || !/^[a-z0-9_]{1,32}$/.test(command)) {
      continue;
    }

    if (excludedSet.has(command)) {
      continue;
    }

    // Disambiguation
    if (registeredCommands.has(command)) {
      const prefix = normalizeCommandName(candidate.sourcePrefix || "ext");
      let disambiguated = `${prefix}_${command}`.slice(0, 32);
      if (disambiguated === command || registeredCommands.has(disambiguated)) {
        let n = 2;
        while (true) {
          const suffix = `_${n}`;
          disambiguated = `${prefix}_${command}`.slice(0, 32 - suffix.length) + suffix;
          if (!registeredCommands.has(disambiguated)) {
            break;
          }
          n++;
        }
      }
      command = disambiguated;
    }

    registeredCommands.set(command, { command, description });
  }

  const commands = Array.from(registeredCommands.values());
  commands.sort((a, b) => a.command.localeCompare(b.command));

  if (commands.length > 100) {
    console.error(
      `[ida-telegram] Discovered ${commands.length} commands, exceeding Telegram's 100-command limit. Platform limit is 100.`
    );
  }

  return commands;
}

/**
 * Resolves the native command menu. If `customJson` is non-empty, parses it as
 * an explicit JSON override list (`TELEGRAM_BOT_COMMANDS`). Otherwise, scans
 * all available skill directories across project-local skills, user skills,
 * and installed plugin skills.
 */
export function resolveBotCommands(
  customJson?: string,
  options?: SkillDiscoveryOptions
): TelegramBotCommand[] {
  if (customJson && customJson.trim()) {
    const excludedSet = new Set<string>([...RESERVED_COMMANDS, ...WORKER_COMMANDS]);
    try {
      const parsed = JSON.parse(customJson) as Array<{ command: string; description: string }>;
      if (!Array.isArray(parsed)) return [];
      const commands: TelegramBotCommand[] = [];
      const seen = new Set<string>();
      for (const entry of parsed) {
        const command = normalizeCommandName(entry.command || "");
        const description = String(entry.description || "").trim().slice(0, 256);
        if (
          /^[a-z0-9_]{1,32}$/.test(command) &&
          !excludedSet.has(command) &&
          description.length >= 1 &&
          !seen.has(command)
        ) {
          seen.add(command);
          commands.push({ command, description });
        }
      }
      commands.sort((a, b) => a.command.localeCompare(b.command));
      if (commands.length > 100) {
        console.error(
          `[ida-telegram] Configured ${commands.length} commands in TELEGRAM_BOT_COMMANDS, exceeding Telegram's 100-command limit. Platform limit is 100.`
        );
      }
      return commands;
    } catch (err) {
      console.error("[ida-telegram] Error parsing TELEGRAM_BOT_COMMANDS JSON:", err);
      return [];
    }
  }

  return discoverSkills(options);
}
