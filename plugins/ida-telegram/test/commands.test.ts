import { describe, expect, test, mock } from "bun:test";
import {
  DEFAULT_IDA_COMMANDS,
  RESERVED_COMMANDS,
  discoverInstalledSkills,
  resolveBotCommands,
  getBareCommandBehavior,
  parseSkillMarkdown,
  normalizeCommandName,
} from "../src/telegram/commands.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { loadConfig } from "../src/config.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

describe("Native Telegram bot commands for Ida (FR-8.1)", () => {
  test("resolveBotCommands uses defaults and filters reserved commands from custom JSON override", () => {
    const defaultCommands = resolveBotCommands();
    expect(defaultCommands.length).toBeGreaterThan(0);
    expect(defaultCommands).toEqual(
      DEFAULT_IDA_COMMANDS.map(({ command, description }) => ({ command, description }))
    );

    const customJson = JSON.stringify([
      { command: "/decide", description: "Custom decide" },
      { command: "start", description: "Reserved should be filtered" },
      { command: "status", description: "Reserved status filtered" },
      { command: "q", description: "Custom capture" },
    ]);
    const resolved = resolveBotCommands(customJson);
    expect(resolved).toEqual([
      { command: "decide", description: "Custom decide" },
      { command: "q", description: "Custom capture" },
    ]);
  });

  test("registerCommands calls setMyCommands scoped to each allowFrom chat and survives restart", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-cmd-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_ALLOW_FROM: "8860530746,12345678",
      STATE_DIR: stateDir,
    });

    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    const storedCommandsByChat = new Map<number, Array<{ command: string; description: string }>>();

    const origFetch = globalThis.fetch;
    globalThis.fetch = mock(async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      const method = urlStr.split("/").pop() || "";
      const payload = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, payload });

      if (method === "setMyCommands") {
        const scope = payload.scope as { type: string; chat_id?: number };
        if (scope?.type === "chat" && scope.chat_id) {
          storedCommandsByChat.set(scope.chat_id, payload.commands as Array<{ command: string; description: string }>);
        }
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }

      if (method === "getMyCommands") {
        const scope = payload.scope as { type: string; chat_id?: number };
        const cmds = scope?.type === "chat" && scope.chat_id ? storedCommandsByChat.get(scope.chat_id) || [] : [];
        return new Response(JSON.stringify({ ok: true, result: cmds }), { status: 200 });
      }

      return new Response(JSON.stringify({ ok: true, result: [] }), { status: 200 });
    }) as unknown as typeof fetch;

    try {
      const broker = new QuestionBroker(stateDir);
      const permRelay = new PermissionRelay();

      // First instance starts and registers commands
      const bot1 = new TelegramBotClient(config, broker, permRelay, () => {});
      await bot1.registerCommands();

      expect(apiCalls.filter((c) => c.method === "setMyCommands").length).toBe(2);
      expect(apiCalls[0].payload).toEqual({
        commands: config.botCommands,
        scope: { type: "chat", chat_id: 8860530746 },
      });

      // Simulate channel restart with a fresh TelegramBotClient instance and verify via getMyCommands
      const bot2 = new TelegramBotClient(config, broker, permRelay, () => {});
      await bot2.registerCommands();
      const menuAfterRestart = await bot2.getRegisteredCommands(8860530746);

      expect(menuAfterRestart).toEqual(config.botCommands);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("tapped bare command with no argument reaches Ida with defined no-argument behavior", () => {
    const allowFrom = [8860530746];

    for (const cmdSpec of DEFAULT_IDA_COMMANDS) {
      const update: TelegramUpdate = {
        update_id: 200,
        message: {
          message_id: 301,
          date: Date.now(),
          chat: { id: 8860530746, type: "private" },
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          text: `/${cmdSpec.command}`,
        },
      };

      const event = parseInboundUpdate(update, allowFrom);
      expect(event).not.toBeNull();
      expect(event?.event).toBe("bot_command");
      expect(event?.meta.command).toBe(`/${cmdSpec.command}`);
      expect(event?.meta.args).toBe("");
      expect(event?.meta.skill).toBe(cmdSpec.skill);
      expect(event?.meta.default_action).toBe(cmdSpec.bareAction);
      expect(event?.content).toContain(`/${cmdSpec.command}`);
      expect(event?.content).toContain(cmdSpec.bareAction);
    }
  });

  test("command with arguments preserves user arguments and does not overwrite with bare fallback", () => {
    const allowFrom = [8860530746];
    const update: TelegramUpdate = {
      update_id: 201,
      message: {
        message_id: 302,
        date: Date.now(),
        chat: { id: 8860530746, type: "private" },
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        text: "/q Review ARC Discovery draft by Friday",
      },
    };

    const event = parseInboundUpdate(update, allowFrom);
    expect(event).not.toBeNull();
    expect(event?.event).toBe("bot_command");
    expect(event?.meta.command).toBe("/q");
    expect(event?.meta.args).toBe("Review ARC Discovery draft by Friday");
    expect(event?.meta.skill).toBe("ida:q");
    expect(event?.content).toBe("/q Review ARC Discovery draft by Friday");
  });

  test("command with @botname suffix is normalized cleanly", () => {
    const allowFrom = [8860530746];
    const update: TelegramUpdate = {
      update_id: 202,
      message: {
        message_id: 303,
        date: Date.now(),
        chat: { id: 8860530746, type: "private" },
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        text: "/decide@ida_bot",
      },
    };

    const event = parseInboundUpdate(update, allowFrom);
    expect(event).not.toBeNull();
    expect(event?.event).toBe("bot_command");
    expect(event?.meta.command).toBe("/decide");
    expect(event?.meta.args).toBe("");
    expect(event?.meta.skill).toBe("ida:decide");
    expect(event?.meta.default_action).toBe(getBareCommandBehavior("/decide")?.bareAction);
  });

  test("AC1: Searching the plugin for STRATEGIC_COMMANDS, resolvePersona, IDA_TELEGRAM_PERSONA and TELEGRAM_PERSONA finds nothing", () => {
    const pluginRoot = resolve(import.meta.dir, "..");
    const forbidden = ["STRATEGIC_COMMANDS", "resolvePersona", "IDA_TELEGRAM_PERSONA", "TELEGRAM_PERSONA"];

    function scanDir(dir: string): Array<{ file: string; term: string }> {
      const violations: Array<{ file: string; term: string }> = [];
      const entries = readdirSync(dir);
      for (const entry of entries) {
        if (entry === "node_modules" || entry === ".git") continue;
        const fullPath = join(dir, entry);
        const st = statSync(fullPath);
        if (st.isDirectory()) {
          violations.push(...scanDir(fullPath));
        } else if (/\.(ts|js|json|md)$/.test(entry)) {
          const content = readFileSync(fullPath, "utf-8");
          for (const term of forbidden) {
            // Exclude this test itself when checking forbidden terms
            if (entry === "commands.test.ts" && content.includes(`"${term}"`)) continue;
            if (content.includes(term)) {
              violations.push({ file: fullPath, term });
            }
          }
        }
      }
      return violations;
    }

    const matches = scanDir(pluginRoot);
    expect(matches).toEqual([]);
  });

  test("AC2: telegram-prime, telegram-actual, telegram-audre and telegram-ida folders yield the same menu", () => {
    const prime = loadConfig({ STATE_DIR: "/home/nic/.claude/channels/telegram-prime" });
    const actual = loadConfig({ STATE_DIR: "/home/nic/.claude/channels/telegram-actual" });
    const audre = loadConfig({ STATE_DIR: "/home/nic/.claude/channels/telegram-audre" });
    const ida = loadConfig({ STATE_DIR: "/home/nic/.claude/channels/telegram-ida" });

    expect(prime.botCommands.length).toBeGreaterThan(0);
    expect(actual.botCommands).toEqual(prime.botCommands);
    expect(audre.botCommands).toEqual(prime.botCommands);
    expect(ida.botCommands).toEqual(prime.botCommands);
  });

  test("AC3: registered menu matches spec_7a9caca5 FR-8.1", () => {
    const commands = discoverInstalledSkills();
    const commandNames = commands.map((c) => c.command);

    // Every installed skill is included
    expect(commandNames).toContain("decide");
    expect(commandNames).toContain("q");
    expect(commandNames).toContain("mine");
    expect(commandNames).toContain("reconcile");
    expect(commandNames).toContain("hydrate");
    expect(commandNames).toContain("up");
    expect(commandNames).toContain("reify");
    expect(commandNames).toContain("dispatch");
    expect(commandNames).toContain("strategize");
    expect(commandNames).toContain("remember");
    expect(commandNames).toContain("decompose");
    expect(commandNames).toContain("strategic_review");
    expect(commandNames).toContain("argument_map");

    // All command names match valid Telegram identifiers: [a-z0-9_]{1,32}
    for (const cmd of commands) {
      expect(/^[a-z0-9_]{1,32}$/.test(cmd.command)).toBe(true);
      expect(cmd.description.length).toBeGreaterThanOrEqual(1);
      expect(cmd.description.length).toBeLessThanOrEqual(256);
      expect(RESERVED_COMMANDS.includes(cmd.command as any)).toBe(false);
    }

    // Zero-argument commands attach their defined action
    const decideSpec = getBareCommandBehavior("decide");
    expect(decideSpec?.bareAction).toContain("decision card");

    const reconcileSpec = getBareCommandBehavior("reconcile");
    expect(reconcileSpec?.bareAction).toContain("reconcile");

    // Hyphenated skills are mapped to snake_case
    const strategicReviewSpec = getBareCommandBehavior("strategic_review");
    expect(strategicReviewSpec?.skill).toBe("ida:strategic-review");

    const argumentMapSpec = getBareCommandBehavior("argument_map");
    expect(argumentMapSpec?.skill).toBe("ida:argument-map");

    // Registered menu via resolveBotCommands matches discoverInstalledSkills
    const resolved = resolveBotCommands();
    expect(resolved).toEqual(commands.map(({ command, description }) => ({ command, description })));
  });

  test("AC5: adding, removing or renaming a skill changes the registered menu with no edit to plugin code, and every skill appears with a distinct, valid command name", () => {
    const testSkillsDir = mkdtempSync(join(tmpdir(), "aops-test-skills-"));

    try {
      // 1. Initial set of skills: skill-one and skill-two
      const skill1Dir = join(testSkillsDir, "skill-one");
      const skill2Dir = join(testSkillsDir, "skill-two");
      mkdirSync(skill1Dir, { recursive: true });
      mkdirSync(skill2Dir, { recursive: true });

      writeFileSync(
        join(skill1Dir, "SKILL.md"),
        `---\nname: skill-one\ndescription: First test skill\n---\n# Skill One\n`
      );
      writeFileSync(
        join(skill2Dir, "SKILL.md"),
        `---\nname: skill-two\ndescription: Second test skill\n---\n# Skill Two\n`
      );

      let menu = resolveBotCommands(undefined, { skillsDirs: [testSkillsDir] });
      expect(menu.map((c) => c.command)).toEqual(["skill_one", "skill_two"]);

      // 2. Add a new skill: skill-three
      const skill3Dir = join(testSkillsDir, "skill-three");
      mkdirSync(skill3Dir, { recursive: true });
      writeFileSync(
        join(skill3Dir, "SKILL.md"),
        `---\nname: skill-three\ndescription: Third test skill\n---\n# Skill Three\n`
      );

      menu = resolveBotCommands(undefined, { skillsDirs: [testSkillsDir] });
      expect(menu.map((c) => c.command)).toEqual(["skill_one", "skill_three", "skill_two"]);

      // 3. Remove a skill: skill-one
      rmSync(skill1Dir, { recursive: true, force: true });
      menu = resolveBotCommands(undefined, { skillsDirs: [testSkillsDir] });
      expect(menu.map((c) => c.command)).toEqual(["skill_three", "skill_two"]);

      // 4. Rename a skill: skill-two -> renamed-action
      const renamedDir = join(testSkillsDir, "renamed-action");
      mkdirSync(renamedDir, { recursive: true });
      writeFileSync(
        join(renamedDir, "SKILL.md"),
        `---\nname: renamed-action\ndescription: Renamed action description\n---\n# Renamed Action\n`
      );
      rmSync(skill2Dir, { recursive: true, force: true });

      menu = resolveBotCommands(undefined, { skillsDirs: [testSkillsDir] });
      expect(menu.map((c) => c.command)).toEqual(["renamed_action", "skill_three"]);

      // 5. Collision handling across two plugin roots
      const pluginADir = mkdtempSync(join(tmpdir(), "plugin-a-"));
      const pluginBDir = mkdtempSync(join(tmpdir(), "plugin-b-"));

      const pluginASkill = join(pluginADir, "skills", "audit");
      const pluginBSkill = join(pluginBDir, "skills", "audit");
      mkdirSync(pluginASkill, { recursive: true });
      mkdirSync(pluginBSkill, { recursive: true });

      writeFileSync(
        join(pluginASkill, "SKILL.md"),
        `---\nname: audit\ndescription: Plugin A audit\n---\n`
      );
      writeFileSync(
        join(pluginBSkill, "SKILL.md"),
        `---\nname: audit\ndescription: Plugin B audit\n---\n`
      );

      const collisionMenu = resolveBotCommands(undefined, { pluginRoots: [pluginADir, pluginBDir] });
      const collisionCmds = collisionMenu.map((c) => c.command);

      // Verify each gets a distinct, valid command name matching [a-z0-9_]{1,32}
      expect(collisionCmds.length).toBe(2);
      expect(new Set(collisionCmds).size).toBe(2);
      for (const cmd of collisionCmds) {
        expect(/^[a-z0-9_]{1,32}$/.test(cmd)).toBe(true);
      }

      rmSync(pluginADir, { recursive: true, force: true });
      rmSync(pluginBDir, { recursive: true, force: true });
    } finally {
      rmSync(testSkillsDir, { recursive: true, force: true });
    }
  });
});
