import { describe, expect, test, mock } from "bun:test";
import { readFileSync } from "node:fs";
import { RESERVED_COMMANDS, resolveBotCommands, normalizeCommandName } from "../src/telegram/commands.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { loadConfig } from "../src/config.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const MENU_JSON = JSON.stringify([
  { command: "decide", description: "Go through open decisions" },
  { command: "q", description: "Capture an ask" },
]);

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
  test("resolveBotCommands returns only the configured menu, filtering reserved and worker commands", () => {
    expect(resolveBotCommands()).toEqual([]);
    expect(resolveBotCommands("")).toEqual([]);
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
    expect(resolveBotCommands(customJson)).toEqual([
      { command: "decide", description: "Custom decide" },
      { command: "strategic_review", description: "Hyphen normalised" },
      { command: "q", description: "Custom capture" },
    ]);
    for (const reserved of RESERVED_COMMANDS) {
      expect(resolveBotCommands(customJson).map((c) => c.command)).not.toContain(reserved);
    }
  });

  test("the plugin builds no menu from other plugins' files: no config means an empty menu", () => {
    const cfg = loadConfig({ MINI_APP_URL: "https://ida.example.test", STATE_DIR: mkdtempSync(join(tmpdir(), "ida-tg-cmd-empty-")) });
    expect(cfg.botCommands).toEqual([]);

    const source = readFileSync(join(import.meta.dir, "..", "src", "telegram", "commands.ts"), "utf-8");
    expect(source).not.toMatch(/node:fs|SKILL\.md|readdirSync/);
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

  test("every persona and state folder gets the same configured menu", () => {
    const baseDir = join(tmpdir(), "ida-tg-test-channels");
    const cfgs = [
      loadConfig({ MINI_APP_URL: "https://ida.example.test", TELEGRAM_BOT_COMMANDS: MENU_JSON, IDA_TELEGRAM_PERSONA: "strategic", STATE_DIR: join(baseDir, "telegram-a") }),
      loadConfig({ MINI_APP_URL: "https://ida.example.test", TELEGRAM_BOT_COMMANDS: MENU_JSON, TELEGRAM_PERSONA: "prime", STATE_DIR: join(baseDir, "telegram-b") }),
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
