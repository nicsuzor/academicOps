import { describe, expect, test } from "bun:test";
import { startWebServer } from "../src/web/server.js";
import { loadConfig } from "../src/config.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PluginStore } from "../src/store.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

describe("Dashboard Cutover and Standalone Retirement (§5 of mini-app-dashboard-integration.md)", () => {
  test("AC-5.2: The plugin web server binds only internal API routes and returns 404 for decommissioned static /app/* endpoints", async () => {
    const tmp = mkdtempSync(join(tmpdir(), "cutover-test-"));
    try {
      const server = startWebServer({ config: { port: 0 } } as any);
      const base = `http://127.0.0.1:${server.port}`;

      // Static routes must return 404
      const appRes = await fetch(`${base}/app`);
      expect(appRes.status).toBe(404);

      const appSlashRes = await fetch(`${base}/app/`);
      expect(appSlashRes.status).toBe(404);

      const indexRes = await fetch(`${base}/app/index.html`);
      expect(indexRes.status).toBe(404);

      const jsRes = await fetch(`${base}/app/app.js`);
      expect(jsRes.status).toBe(404);

      server.stop(true);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  test("AC2: Details button on fresh reply from each Ida with a bot carries a dash.suzor.com URL with instance parameter", async () => {
    const tmp = mkdtempSync(join(tmpdir(), "cutover-reply-"));
    try {
      for (const instance of ["prime", "actual", "audre"]) {
        const config = loadConfig({
          STATE_DIR: tmp,
          TELEGRAM_BOT_TOKEN: "mock-token",
          MINI_APP_URL: "https://dash.suzor.com",
          IDA_NAME: instance,
          ALLOWED_USER_IDS: "12345",
        });

        expect(config.instance).toBe(instance);

        const store = new PluginStore(tmp);
        const broker = new QuestionBroker(tmp);
        const permRelay = new PermissionRelay(tmp);

        let sentPayload: any = null;
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        bot.callApi = async (method: string, payload: any) => {
          if (method === "sendMessage") {
            sentPayload = payload;
            return { ok: true, result: { message_id: 100 } };
          }
          return { ok: true, result: {} };
        };

        const longText = "Summary of work.\n\n" + "x".repeat(1500);
        await bot.sendReply({
          chatId: 12345,
          formatted: { plainText: longText, entities: [] },
          detailsId: `d_${instance}_123`,
        });

        expect(sentPayload).not.toBeNull();
        const inlineKeyboard = sentPayload.reply_markup.inline_keyboard;
        const detailsBtn = inlineKeyboard.flat().find((b: any) => b.text === "🔍" || b.text.includes("Details"));

        expect(detailsBtn).toBeDefined();
        expect(detailsBtn.web_app).toBeDefined();
        const url = detailsBtn.web_app.url;

        // Must point to dash.suzor.com and include instance and details id
        expect(url).toStartWith("https://dash.suzor.com/app/index.html");
        expect(url).toContain(`instance=${instance}`);
        expect(url).toMatch(/[?&]d=/);
      }
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  test("AC1 & AC-5.4: Review diff button carries dash.suzor.com URL with instance parameter", async () => {
    const tmp = mkdtempSync(join(tmpdir(), "cutover-review-"));
    try {
      const config = loadConfig({
        STATE_DIR: tmp,
        TELEGRAM_BOT_TOKEN: "mock-token",
        MINI_APP_URL: "https://dash.suzor.com",
        IDA_NAME: "prime",
        ALLOWED_USER_IDS: "12345",
      });

      const store = new PluginStore(tmp);
      const broker = new QuestionBroker(tmp);
      const permRelay = new PermissionRelay(tmp);

      let sentPayload: any = null;
      const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
      bot.callApi = async (method: string, payload: any) => {
        if (method === "sendMessage") {
          sentPayload = payload;
          return { ok: true, result: { message_id: 101 } };
        }
        return { ok: true, result: {} };
      };

      await bot.sendReply({
        chatId: 12345,
        formatted: { plainText: "Check this PR", entities: [] },
        review: { repo: "nicsuzor/academicOps", pr: 3348 },
      });

      const inlineKeyboard = sentPayload.reply_markup.inline_keyboard;
      const reviewBtn = inlineKeyboard.flat().find((b: any) => b.text.includes("Review diff"));
      expect(reviewBtn).toBeDefined();
      expect(reviewBtn.web_app.url).toBe("https://dash.suzor.com/app/index.html?instance=prime&tab=review");
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });
});
