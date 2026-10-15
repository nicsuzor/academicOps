import { describe, expect, test, afterEach } from "bun:test";
import { FeedbackManager } from "../src/telegram/feedback.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Feedback: Upvote/downvote and learning loop", () => {
  const testStateDir = join(tmpdir(), "ida-telegram-fb-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("upvote records to feedback store and emits no channel event", async () => {
    const manager = new FeedbackManager(testStateDir);

    const result = await manager.handleUpvote({
      turnId: "turn_up_1",
      messageId: 201,
      messageExcerpt: "A crisp briefing with key metrics.",
    });

    expect(result.buttonText).toBe("👍 saved");
    expect(result.emitsChannelEvent).toBe(false);

    // Verify written to trace sink
    const traces = manager.getTraces();
    expect(traces.length).toBe(1);
    expect(traces[0].rating).toBe("up");
    expect(traces[0].turnId).toBe("turn_up_1");
  });

  test("downvote swaps keyboard to critique options", () => {
    const manager = new FeedbackManager(testStateDir);
    const keyboard = manager.getDownvoteCritiqueKeyboard(202);

    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Too verbose")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Wrong premise")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Poor logic")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Say why")))).toBe(true);
  });

  test("critique selection emits exactly one feedback_down channel event to Ida", async () => {
    const manager = new FeedbackManager(testStateDir);

    const result = await manager.handleCritique({
      turnId: "turn_down_1",
      messageId: 203,
      messageExcerpt: "A verbose explanation exceeding budget.",
      critique: "Too verbose",
    });

    expect(result.emitsChannelEvent).toBe(true);
    expect(result.channelEvent).toBeDefined();
    expect(result.channelEvent?.event).toBe("feedback_down");
    expect(result.channelEvent?.critique).toBe("Too verbose");
    expect(result.channelEvent?.turn_id).toBe("turn_down_1");
    expect(result.channelEvent?.message_excerpt).toContain("verbose explanation");
  });

  test("FR-3.2: tapping fb:up answers callback query with 'Noted 👍', replaces [👍, 👎] with '👍 saved' while preserving Details and Review diff buttons, writes upvote trace, and emits no channel event", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const manager = new FeedbackManager(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 8093,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, manager, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const initialKeyboard = [
      [
        { text: "👍", callback_data: "fb:up" },
        { text: "👎", callback_data: "fb:down" },
        { text: "🔍 Details", web_app: { url: "https://ida.example.ts.net/app/index.html?d=det_1" } },
      ],
      [
        { text: "🔍 Review diff (nicsuzor/academicOps#2928)", web_app: { url: "https://ida.example.ts.net/app/index.html?tab=review" } },
      ],
    ];

    await (bot as any).handleUpdate({
      update_id: 100,
      callback_query: {
        id: "cb_up_1",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 501,
          date: 1700000000,
          chat: { id: 8860530746, type: "private" },
          text: "Briefing card with details and review",
          reply_markup: { inline_keyboard: initialKeyboard },
        },
        data: "fb:up",
      },
    });

    const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
    expect(answerCall).toBeDefined();
    expect(answerCall?.payload).toEqual({
      callback_query_id: "cb_up_1",
      text: "Noted 👍",
    });

    const editMarkupCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(editMarkupCall).toBeDefined();
    expect(editMarkupCall?.payload).toEqual({
      chat_id: 8860530746,
      message_id: 501,
      reply_markup: {
        inline_keyboard: [
          [
            { text: "👍 saved", callback_data: "noop" },
            { text: "🔍 Details", web_app: { url: "https://ida.example.ts.net/app/index.html?d=det_1" } },
          ],
          [
            { text: "🔍 Review diff (nicsuzor/academicOps#2928)", web_app: { url: "https://ida.example.ts.net/app/index.html?tab=review" } },
          ],
        ],
      },
    });

    const traces = manager.getTraces();
    expect(traces.length).toBe(1);
    expect(traces[0].rating).toBe("up");
    expect(traces[0].messageId).toBe(501);
    expect(emittedEvents.length).toBe(0);
  });

  test("FR-3.3: tapping fb:down swaps feedback buttons to critique rows while keeping Details and Review diff; tapping fb:critique replaces critique rows with 'Critique saved: ...' while keeping Details and Review diff and emits one feedback_down event", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const manager = new FeedbackManager(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 8093,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, manager, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const detailsBtn = { text: "🔍 Details", web_app: { url: "https://ida.example.ts.net/app/index.html?d=det_2" } };
    const reviewBtn = { text: "🔍 Review diff (nicsuzor/academicOps#2928)", web_app: { url: "https://ida.example.ts.net/app/index.html?tab=review" } };

    const initialKeyboard = [
      [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }, detailsBtn],
      [reviewBtn],
    ];

    // 1. Tap fb:down
    await (bot as any).handleUpdate({
      update_id: 101,
      callback_query: {
        id: "cb_down_1",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 502,
          date: 1700000010,
          chat: { id: 8860530746, type: "private" },
          text: "A verbose reply card",
          reply_markup: { inline_keyboard: initialKeyboard },
        },
        data: "fb:down",
      },
    });

    const downEditCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(downEditCall).toBeDefined();
    const downKeyboard = downEditCall?.payload.reply_markup.inline_keyboard as Array<Array<Record<string, unknown>>>;
    const downFlat = downKeyboard.flat();
    expect(downFlat.some((b) => b.text === "💨 Too verbose" && b.callback_data === "fb:critique:502:Too verbose")).toBe(true);
    expect(downFlat.some((b) => b.text === "❌ Wrong premise")).toBe(true);
    expect(downFlat.some((b) => b.text === "📉 Poor logic")).toBe(true);
    expect(downFlat.some((b) => b.text === "🎙 Say why")).toBe(true);
    expect(downFlat.some((b) => b.text === "↩ Cancel" && b.callback_data === "fb:cancel:502")).toBe(true);
    expect(downFlat).toContainEqual(detailsBtn);
    expect(downFlat).toContainEqual(reviewBtn);
    expect(emittedEvents.length).toBe(0);

    apiCalls.length = 0;

    // 2. Tap fb:critique:502:Too verbose on the expanded keyboard
    await (bot as any).handleUpdate({
      update_id: 102,
      callback_query: {
        id: "cb_critique_1",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 502,
          date: 1700000010,
          chat: { id: 8860530746, type: "private" },
          text: "A verbose reply card",
          reply_markup: { inline_keyboard: downKeyboard },
        },
        data: "fb:critique:502:Too verbose",
      },
    });

    const critiqueEditCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(critiqueEditCall).toBeDefined();
    expect(critiqueEditCall?.payload).toEqual({
      chat_id: 8860530746,
      message_id: 502,
      reply_markup: {
        inline_keyboard: [
          [{ text: "Critique saved: Too verbose", callback_data: "noop" }, detailsBtn],
          [reviewBtn],
        ],
      },
    });

    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].meta.event).toBe("feedback_down");
    expect(emittedEvents[0].meta.critique).toBe("Too verbose");
  });

  test("FR-3.3: tapping fb:cancel:<id> restores [👍, 👎] alongside Details and Review diff, writes 0 traces, emits 0 channel events, and does not call editMessageText; tapping noop is ignored", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const manager = new FeedbackManager(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 8093,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, manager, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const detailsBtn = { text: "🔍 Details", web_app: { url: "https://ida.example.ts.net/app/index.html?d=det_3" } };
    const reviewBtn = { text: "🔍 Review diff (nicsuzor/academicOps#2928)", web_app: { url: "https://ida.example.ts.net/app/index.html?tab=review" } };

    // Simulate the keyboard after fb:down
    await (bot as any).handleUpdate({
      update_id: 103,
      callback_query: {
        id: "cb_down_2",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 503,
          date: 1700000020,
          chat: { id: 8860530746, type: "private" },
          text: "Reply card to cancel downvote",
          reply_markup: {
            inline_keyboard: [
              [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }, detailsBtn],
              [reviewBtn],
            ],
          },
        },
        data: "fb:down",
      },
    });

    const expandedKeyboard = apiCalls.find((c) => c.method === "editMessageReplyMarkup")?.payload.reply_markup.inline_keyboard || [];
    apiCalls.length = 0;

    // Now tap fb:cancel:503
    await (bot as any).handleUpdate({
      update_id: 104,
      callback_query: {
        id: "cb_cancel_1",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 503,
          date: 1700000020,
          chat: { id: 8860530746, type: "private" },
          text: "Reply card to cancel downvote",
          reply_markup: { inline_keyboard: expandedKeyboard },
        },
        data: "fb:cancel:503",
      },
    });

    // Must not call editMessageText with "Selected: ↩ Cancel ✅"
    expect(apiCalls.some((c) => c.method === "editMessageText")).toBe(false);

    const cancelEditCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(cancelEditCall).toBeDefined();
    expect(cancelEditCall?.payload).toEqual({
      chat_id: 8860530746,
      message_id: 503,
      reply_markup: {
        inline_keyboard: [
          [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }, detailsBtn],
          [reviewBtn],
        ],
      },
    });

    expect(manager.getTraces().length).toBe(0);
    expect(emittedEvents.length).toBe(0);

    // Also verify tapping "noop" is ignored cleanly
    apiCalls.length = 0;
    await (bot as any).handleUpdate({
      update_id: 105,
      callback_query: {
        id: "cb_noop_1",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 503,
          date: 1700000020,
          chat: { id: 8860530746, type: "private" },
          text: "Reply card",
          reply_markup: {
            inline_keyboard: [[{ text: "👍 saved", callback_data: "noop" }, detailsBtn]],
          },
        },
        data: "noop",
      },
    });

    expect(apiCalls.some((c) => c.method === "editMessageText")).toBe(false);
    expect(apiCalls.some((c) => c.method === "editMessageReplyMarkup")).toBe(false);
    expect(emittedEvents.length).toBe(0);
  });
});

