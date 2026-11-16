import { describe, expect, test, mock, spyOn } from "bun:test";
import { mkdirSync, writeFileSync, symlinkSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { RESERVED_COMMANDS, WORKER_COMMANDS, resolveBotCommands, normalizeCommandName } from "../src/telegram/commands.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { loadConfig } from "../src/config.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";

const MENU_JSON = JSON.stringify([
  { command: "decide", description: "Go through open decisions" },
  { command: "q", description: "Capture an ask" },
]);

function createSkillFixture(
  skillDir: string,
  frontmatter: { name?: string; description?: string }
) {
  mkdirSync(skillDir, { recursive: true });
  const lines = ["---"];
  if (frontmatter.name !== undefined) {
    lines.push(`name: ${frontmatter.name}`);
  }
  if (frontmatter.description !== undefined) {
    lines.push(`description: ${frontmatter.description}`);
  }
  lines.push("---", "", "# Skill body");
  writeFileSync(join(skillDir, "SKILL.md"), lines.join("\n"), "utf-8");
}

function commandUpdate(text: string): TelegramUpdate {
  return {
    update_id: 200,
    message: {
      message_id: 301,
      date: Date.now(),
      chat: { id: 1111111111, type: "private" },
      from: { id: 1111111111, is_bot: false, first_name: "Alex" },
      text,
    },
  };
}

describe("Native Telegram bot commands for Ida (FR-8.1)", () => {
  test("resolveBotCommands with TELEGRAM_BOT_COMMANDS JSON override filters reserved/worker commands and normalises hyphens", () => {
    expect(resolveBotCommands("not json")).toEqual([]);

    const customJson = JSON.stringify([
      { command: "/decide", description: "Custom decide" },
      { command: "start", description: "Reserved should be filtered" },
      { command: "status", description: "Reserved status filtered" },
      { command: "pull", description: "Worker command filtered" },
      { command: "dump", description: "Worker command filtered" },
      { command: "strategic-review", description: "Hyphen normalised" },
      { command: "q", description: "Custom capture" },
    ]);
    const res = resolveBotCommands(customJson);
    expect(res).toEqual([
      { command: "decide", description: "Custom decide" },
      { command: "q", description: "Custom capture" },
      { command: "strategic_review", description: "Hyphen normalised" },
    ]);
    for (const reserved of [...RESERVED_COMMANDS, ...WORKER_COMMANDS]) {
      expect(res.map((c) => c.command)).not.toContain(reserved);
    }
  });

  test("AC1 & AC2: With TELEGRAM_BOT_COMMANDS unset, discovers skills from project, user, and plugin locations, normalises hyphens, and excludes reserved/worker commands", () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-discovery-"));
    const projectDir = join(fixtureDir, "project");
    const claudeConfigDir = join(fixtureDir, "claude-config");

    // 1. Project-local Ida skill: nudge
    createSkillFixture(join(projectDir, ".agents", "skills", "nudge"), {
      name: "nudge",
      description: "Ida's own learn-and-unlearn loop",
    });

    // 2. Project-local skill with hyphen: local-tool
    createSkillFixture(join(projectDir, ".claude", "skills", "local-tool"), {
      name: "local-tool",
      description: "Project local tool",
    });

    // 3. User skill: daily
    createSkillFixture(join(claudeConfigDir, "skills", "daily"), {
      name: "daily",
      description: "Generate or update daily note",
    });

    // 4. Repo plugin skill: reconcile
    createSkillFixture(join(projectDir, "plugins", "ida", "skills", "reconcile"), {
      name: "reconcile",
      description: "Truth maintenance over the task graph",
    });

    // 5. Excluded reserved commands and worker commands
    createSkillFixture(join(projectDir, ".agents", "skills", "start"), {
      name: "start",
      description: "Start command",
    });
    createSkillFixture(join(projectDir, ".agents", "skills", "help"), {
      name: "help",
      description: "Help command",
    });
    createSkillFixture(join(projectDir, ".agents", "skills", "status"), {
      name: "status",
      description: "Status command",
    });
    createSkillFixture(join(projectDir, ".agents", "skills", "pull"), {
      name: "pull",
      description: "Headless pull worker",
    });
    createSkillFixture(join(projectDir, ".agents", "skills", "dump"), {
      name: "dump",
      description: "Headless dump worker",
    });

    // 6. Skill with missing description (must be skipped)
    createSkillFixture(join(projectDir, ".agents", "skills", "nodesc"), {
      name: "nodesc",
      description: "",
    });

    // 7. Symlinked skill (must be deduplicated by canonical real path)
    const symlinkTarget = join(projectDir, ".agents", "skills", "nudge");
    const symlinkPath = join(projectDir, ".claude", "skills", "nudge-link");
    mkdirSync(join(projectDir, ".claude", "skills"), { recursive: true });
    symlinkSync(symlinkTarget, symlinkPath, "dir");

    const commands = resolveBotCommands(undefined, {
      projectDir,
      claudeConfigDir,
      pluginRoot: join(projectDir, "plugins", "ida"),
    });

    const commandNames = commands.map((c) => c.command);

    // AC1: Lists every available skill, including Ida's own nudge
    expect(commandNames).toContain("nudge");
    expect(commandNames).toContain("daily");
    expect(commandNames).toContain("reconcile");

    // AC2: Hyphens in skill names become underscores
    expect(commandNames).toContain("local_tool");
    expect(commandNames).not.toContain("local-tool");

    // AC2: Reserved and worker commands excluded
    expect(commandNames).not.toContain("start");
    expect(commandNames).not.toContain("help");
    expect(commandNames).not.toContain("status");
    expect(commandNames).not.toContain("pull");
    expect(commandNames).not.toContain("dump");

    // Missing description skipped
    expect(commandNames).not.toContain("nodesc");

    // Symlink deduplicated: only one nudge entry
    expect(commands.filter((c) => c.command === "nudge").length).toBe(1);

    // Commands are sorted lexicographically
    const sorted = [...commands].sort((a, b) => a.command.localeCompare(b.command));
    expect(commands).toEqual(sorted);
  });

  test("disambiguates colliding skill names across sources", () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-collision-"));
    const projectDir = join(fixtureDir, "project");

    // Skill 'review' in plugin tools
    createSkillFixture(join(projectDir, "plugins", "tools", "skills", "review"), {
      name: "review",
      description: "Tools review skill",
    });

    // Skill 'review' in plugin rbg
    createSkillFixture(join(projectDir, "plugins", "rbg", "skills", "review"), {
      name: "review",
      description: "RBG compliance review skill",
    });

    const commands = resolveBotCommands(undefined, {
      projectDir,
      claudeConfigDir: join(fixtureDir, "claude-config"),
    });

    const names = commands.map((c) => c.command);
    expect(names.length).toBe(2);
    expect(names).toContain("review");
    // The second source is disambiguated with a prefix
    const disambiguated = names.find((n) => n !== "review");
    expect(disambiguated).toBeDefined();
    expect(disambiguated).toMatch(/_review$/);
  });

  test("AC3: more than 100 skills is reported via console.error and not silently truncated", () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-limit-"));
    const projectDir = join(fixtureDir, "project");

    // Create 105 distinct skills
    for (let i = 1; i <= 105; i++) {
      createSkillFixture(join(projectDir, ".agents", "skills", `skill-${i}`), {
        name: `skill-${i}`,
        description: `Description for skill ${i}`,
      });
    }

    const errors: string[] = [];
    const origError = console.error;
    console.error = (...args: unknown[]) => {
      errors.push(args.map(String).join(" "));
      origError(...args);
    };

    try {
      const commands = resolveBotCommands(undefined, {
        projectDir,
        claudeConfigDir: join(fixtureDir, "claude-config"),
      });

      // Must NOT be silently truncated to 100
      expect(commands.length).toBe(105);

      // Must log an explicit error reporting total count and 100-command limit
      const limitError = errors.find((e) => e.includes("105") && e.includes("100"));
      expect(limitError).toBeDefined();
    } finally {
      console.error = origError;
    }
  });

  test("AC3: more than 100 commands in TELEGRAM_BOT_COMMANDS override is reported and not truncated", () => {
    const customList = Array.from({ length: 105 }, (_, i) => ({
      command: `cmd_${i + 1}`,
      description: `Description ${i + 1}`,
    }));

    const errors: string[] = [];
    const origError = console.error;
    console.error = (...args: unknown[]) => {
      errors.push(args.map(String).join(" "));
      origError(...args);
    };

    try {
      const commands = resolveBotCommands(JSON.stringify(customList));
      expect(commands.length).toBe(105);
      const limitError = errors.find((e) => e.includes("105") && e.includes("100"));
      expect(limitError).toBeDefined();
    } finally {
      console.error = origError;
    }
  });

  test("loadConfig with TELEGRAM_BOT_COMMANDS unset discovers available skills including nudge", () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-cfg-discovery-"));
    const projectDir = join(fixtureDir, "project");
    const stateDir = join(fixtureDir, "state");

    createSkillFixture(join(projectDir, ".agents", "skills", "nudge"), {
      name: "nudge",
      description: "Ida's own learn-and-unlearn loop",
    });

    const cfg = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      STATE_DIR: stateDir,
      CLAUDE_PROJECT_DIR: projectDir,
      CLAUDE_CONFIG_DIR: join(fixtureDir, "claude-config"),
    });

    expect(cfg.botCommands.map((c) => c.command)).toContain("nudge");
  });

  test("registerCommands calls setMyCommands scoped to each allowFrom chat and survives restart", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-cmd-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_ALLOW_FROM: "1111111111,12345678",
      TELEGRAM_BOT_COMMANDS: MENU_JSON,
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

      expect(config.botCommands.length).toBe(2);
      expect(apiCalls.filter((c) => c.method === "setMyCommands").length).toBe(2);
      expect(apiCalls[0].payload).toEqual({
        commands: config.botCommands,
        scope: { type: "chat", chat_id: 1111111111 },
      });

      // Simulate channel restart with a fresh TelegramBotClient instance and verify via getMyCommands
      const bot2 = new TelegramBotClient(config, broker, permRelay, () => {});
      await bot2.registerCommands();
      const menuAfterRestart = await bot2.getRegisteredCommands(1111111111);

      expect(menuAfterRestart).toEqual(config.botCommands);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("registerCommands resolves skills dynamically at poller start when TELEGRAM_BOT_COMMANDS is unset", async () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-poller-dyn-"));
    const projectDir = join(fixtureDir, "project");
    const claudeConfigDir = join(fixtureDir, "claude-config");
    const stateDir = join(fixtureDir, "state");

    createSkillFixture(join(projectDir, ".agents", "skills", "nudge"), {
      name: "nudge",
      description: "Ida's own learn-and-unlearn loop",
    });

    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_ALLOW_FROM: "1111111111",
      STATE_DIR: stateDir,
      CLAUDE_PROJECT_DIR: projectDir,
      CLAUDE_CONFIG_DIR: claudeConfigDir,
    });

    const registeredMenus: Array<Array<{ command: string; description: string }>> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = mock(async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const payload = init?.body ? JSON.parse(String(init.body)) : {};
      if (method === "setMyCommands") {
        registeredMenus.push(payload.commands as Array<{ command: string; description: string }>);
      }
      return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
    }) as unknown as typeof fetch;

    try {
      const broker = new QuestionBroker(stateDir);
      const permRelay = new PermissionRelay();
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      await bot.registerCommands();

      expect(registeredMenus[0]?.map((c) => c.command)).toEqual(["nudge"]);

      // Add a new skill before next poller start
      createSkillFixture(join(projectDir, ".agents", "skills", "strategic-review"), {
        name: "strategic-review",
        description: "Dialectical review",
      });
      await bot.registerCommands();

      expect(registeredMenus[1]?.map((c) => c.command)).toEqual(["nudge", "strategic_review"]);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("bare command reaches Ida as the command alone, with no plugin-defined action", () => {
    const event = parseInboundUpdate(commandUpdate("/decide"), [1111111111]);
    expect(event).not.toBeNull();
    expect(event?.event).toBe("bot_command");
    expect(event?.meta.command).toBe("/decide");
    expect(event?.meta.args).toBe("");
    expect(event?.meta.skill).toBeUndefined();
    expect(event?.meta.default_action).toBeUndefined();
    expect(event?.content).toBe("/decide");
  });

  test("command with arguments preserves user arguments", () => {
    const event = parseInboundUpdate(commandUpdate("/q Review ARC Discovery draft by Friday"), [1111111111]);
    expect(event?.event).toBe("bot_command");
    expect(event?.meta.command).toBe("/q");
    expect(event?.meta.args).toBe("Review ARC Discovery draft by Friday");
    expect(event?.content).toBe("/q Review ARC Discovery draft by Friday");
  });

  test("command with @botname suffix is normalized cleanly", () => {
    expect(normalizeCommandName("/decide@ida_bot")).toBe("decide");
    const event = parseInboundUpdate(commandUpdate("/decide@ida_bot"), [1111111111]);
    expect(event?.meta.command).toBe("/decide");
    expect(event?.meta.args).toBe("");
  });

  test("every persona and state folder gets the same menu (generated and configured)", () => {
    const fixtureDir = mkdtempSync(join(tmpdir(), "ida-tg-test-channels-"));
    const projectDir = join(fixtureDir, "project");
    const claudeConfigDir = join(fixtureDir, "claude-config");

    createSkillFixture(join(projectDir, ".agents", "skills", "nudge"), {
      name: "nudge",
      description: "Ida's own learn-and-unlearn loop",
    });
    createSkillFixture(join(projectDir, "plugins", "ida", "skills", "decide"), {
      name: "decide",
      description: "Go through open decisions",
    });

    const generatedCfgs = [
      loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        IDA_TELEGRAM_PERSONA: "strategic",
        STATE_DIR: join(fixtureDir, "telegram-prime"),
        CLAUDE_PROJECT_DIR: projectDir,
        CLAUDE_CONFIG_DIR: claudeConfigDir,
      }),
      loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_PERSONA: "prime",
        STATE_DIR: join(fixtureDir, "telegram-ida"),
        CLAUDE_PROJECT_DIR: projectDir,
        CLAUDE_CONFIG_DIR: claudeConfigDir,
      }),
      loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        STATE_DIR: join(fixtureDir, "telegram-secondary"),
        CLAUDE_PROJECT_DIR: projectDir,
        CLAUDE_CONFIG_DIR: claudeConfigDir,
      }),
    ];
    for (const cfg of generatedCfgs) {
      expect(cfg.botCommands.map((c) => c.command)).toEqual(["decide", "nudge"]);
      expect(cfg.botCommands).toEqual(generatedCfgs[0].botCommands);
    }

    const cfgs = [
      loadConfig({ MINI_APP_URL: "https://ida.example.test", TELEGRAM_BOT_COMMANDS: MENU_JSON, IDA_TELEGRAM_PERSONA: "strategic", STATE_DIR: join(fixtureDir, "telegram-a") }),
      loadConfig({ MINI_APP_URL: "https://ida.example.test", TELEGRAM_BOT_COMMANDS: MENU_JSON, TELEGRAM_PERSONA: "prime", STATE_DIR: join(fixtureDir, "telegram-b") }),
    ];
    for (const cfg of cfgs) {
      expect(cfg.botCommands).toEqual(resolveBotCommands(MENU_JSON));
    }
  });
});

describe("Mini App URL configuration", () => {
  test("loadConfig fails when no Mini App URL is configured, rather than falling back to a default", () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-no-url-"));
    expect(() => loadConfig({ STATE_DIR: stateDir })).toThrow(/MINI_APP_URL/);
  });

  test("loadConfig takes the Mini App URL from config and strips trailing slashes", () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-url-"));
    expect(loadConfig({ STATE_DIR: stateDir, MINI_APP_URL: "https://ida.example.test/" }).miniAppUrl).toBe("https://ida.example.test");
    expect(loadConfig({ STATE_DIR: stateDir, IDA_WEB_URL: "https://web.example.test" }).miniAppUrl).toBe("https://web.example.test");
  });
});
