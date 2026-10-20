import { describe, expect, test, mock } from "bun:test";
import {
  DEFAULT_IDA_COMMANDS,
  resolveBotCommands,
  getBareCommandBehavior,
} from "../src/telegram/commands.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { loadConfig } from "../src/config.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Native Telegram bot commands for Ida (FR-8.1)", () => {
  test("resolveBotCommands uses defaults and filters reserved commands from custom JSON override", () => {
    expect(resolveBotCommands(undefined)).toEqual(
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
        commands: DEFAULT_IDA_COMMANDS.map(({ command, description }) => ({ command, description })),
        scope: { type: "chat", chat_id: 8860530746 },
      });

      // Simulate channel restart with a fresh TelegramBotClient instance and verify via getMyCommands
      const bot2 = new TelegramBotClient(config, broker, permRelay, () => {});
      await bot2.registerCommands();
      const menuAfterRestart = await bot2.getRegisteredCommands(8860530746);

      expect(menuAfterRestart).toEqual(
        DEFAULT_IDA_COMMANDS.map(({ command, description }) => ({ command, description }))
      );
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
});
