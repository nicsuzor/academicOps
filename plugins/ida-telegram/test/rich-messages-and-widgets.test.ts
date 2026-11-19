import { describe, expect, test, afterEach } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import zlib from "node:zlib";
import { loadConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { withToolDeadline, ToolTimeoutError } from "../src/mcp/timeout.js";
import { parseInboundUpdate } from "../src/telegram/inbound.js";

describe("Bot API 10.1-10.4 Rich Messages and HTML Widgets", () => {
  const dirs: string[] = [];

  function makeEnv(overrides: Record<string, string> = {}) {
    const dir = mkdtempSync(join(tmpdir(), "ida-rich-widget-"));
    dirs.push(dir);
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: dir,
      MINI_APP_URL: "https://dash.example.test",
      VOICE_REPLIES: "off",
      ...overrides,
    });
    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay(config.stateDir);
    return { dir, config, store, broker, permRelay };
  }

    afterEach(() => {
    while (dirs.length > 0) {
      const dir = dirs.pop()!;
      rmSync(dir, { recursive: true, force: true });
    }
  });

  function runWidgetScript(
    html: string,
    chatDataObj: Record<string, unknown> | null,
    requestImpl: (payload: string) => Promise<unknown> = async () => ""
  ) {
    const match = html.match(/<script>([\s\S]*?)<\/script>/);
    if (!match) throw new Error("Missing widget script");
    const ids = ["er", "sg", "os", "pg", "pv", "nx", "pl", "ft", "go", "df", "ot", "dc", "dm", "dt", "dn"];
    const elements: Record<string, any> = {};
    for (const id of ids) {
      const listeners: Record<string, Array<(e: any) => unknown>> = {};
      elements[id] = {
        id,
        style: {} as Record<string, string>,
        className: "",
        textContent: "",
        innerHTML: "",
        disabled: false,
        listeners,
        addEventListener(ev: string, fn: (e: any) => unknown) {
          (listeners[ev] ||= []).push(fn);
        },
        click() {
          for (const fn of listeners.click || []) fn({ target: { closest: () => null }, stopPropagation() {} });
        },
      };
    }
    const widgetApi = {
      chatData: chatDataObj ? JSON.stringify(chatDataObj) : "",
      HapticFeedback: { selectionChanged() {}, notificationOccurred() {} },
      onEvent() {},
      ready() {},
      setResizeAnchor() {},
      request: requestImpl,
    };
    const fakeDocument = { getElementById: (id: string) => elements[id] || null };
    const fakeWindow = { TelegramWidget: widgetApi };
    const runner = new Function("window", "document", match[1]);
    runner(fakeWindow, fakeDocument);
    return { elements, widgetApi };
  }

  test("send_rich_message dispatches markdown/html/blocks, quote_rich_texts, feedback_buttons, and thread routing cleanly", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    store.updateChatState(1111111111, { activeThreadId: 55, topicsEnabled: true });
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return {
        ok: true,
        result: {
          message_id: 701,
          chat: { id: payload.chat_id, type: "private" },
          message_thread_id: payload.message_thread_id,
          rich_message: payload.rich_message,
        },
      };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "send_rich_message",
        arguments: {
          markdown: "**Summary:** Ready.\n\n<details><summary>Proof</summary>\nVerified live.\n</details>",
          quote_rich_texts: ["original quote"],
          reply_to: 99,
          feedback_buttons: true,
          buttons: [{ label: "Reasons", callback_data: "reasons:701" }],
        },
      },
    });

    expect((res?.result as any)?.isError).toBeUndefined();
    const call = apiCalls.find((c) => c.method === "sendRichMessage");
    expect(call).toBeDefined();
    expect(call!.payload.chat_id).toBe(1111111111);
    expect(call!.payload.message_thread_id).toBe(55);
    expect(call!.payload.rich_message.markdown).toContain("<details>");
    expect(call!.payload.reply_parameters.message_id).toBe(99);
    expect(call!.payload.reply_parameters.quote_rich_texts).toEqual(["original quote"]);
    const flatButtons = call!.payload.reply_markup.inline_keyboard.flat();
    expect(flatButtons.some((b: any) => b.callback_data === "reasons:701")).toBe(true);
    expect(flatButtons.some((b: any) => b.callback_data === "fb:up")).toBe(true);
  });

  test("send_rich_message uploads local media files as multipart FormData using typed InputMedia* and normalizes voice_note", async () => {
    const { dir, config, store, broker, permRelay } = makeEnv();
    const imgPath = join(dir, "chart.png");
    const voicePath = join(dir, "note.ogg");
    writeFileSync(imgPath, Buffer.from("fake-png-bytes"));
    writeFileSync(voicePath, Buffer.from("fake-ogg-bytes"));

    const fetches: Array<{ url: string; init: RequestInit | undefined }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      fetches.push({ url: String(url), init });
      return new Response(
        JSON.stringify({ ok: true, result: { message_id: 702, chat: { id: 1111111111, type: "private" } } }),
        { status: 200 }
      );
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const res = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            html: "<p>Chart &amp; voice note:</p><img src=\"tg://photo?id=chart_1\"/>",
            media: [
              { id: "chart_1", type: "photo", file: imgPath },
              { id: "aud_1", type: "voice", file: voicePath },
            ],
          },
        },
      });

      expect((res?.result as any)?.isError).toBeUndefined();
      expect(fetches.length).toBe(1);
      expect(fetches[0].url).toContain("/sendRichMessage");
      expect(fetches[0].init?.body).toBeInstanceOf(FormData);
      expect(fetches[0].init?.signal).toBeDefined();

      const fd = fetches[0].init!.body as FormData;
      const richMsg = JSON.parse(String(fd.get("rich_message")));
      expect(richMsg.media).toHaveLength(2);
      expect(richMsg.media[0]).toEqual({ id: "chart_1", media: { type: "photo", media: "attach://rich_media_0" } });
      expect(richMsg.media[1]).toEqual({ id: "aud_1", media: { type: "voice_note", media: "attach://rich_media_1" } });
      expect(fd.get("rich_media_0")).toBeInstanceOf(Blob);
      expect(fd.get("rich_media_1")).toBeInstanceOf(Blob);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("send_rich_message rejects invalid or conflicting inputs locally before calling Telegram", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    let apiCount = 0;
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    (bot as any).callApi = async () => {
      apiCount++;
      return { ok: true, result: { message_id: 1 } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    for (const [idx, [args, expectedText]] of ([
      [{ markdown: "a", html: "<b>a</b>" }, "exactly one"],
      [{ markdown: "a", html: "" }, "exactly one"],
      [{}, "exactly one"],
      [{ markdown: "x".repeat(32_769) }, "32768"],
      [{ blocks: Array.from({ length: 501 }, () => ({ type: "paragraph", text: [] })) }, "500"],
      [{ markdown: "ok", media: [{ id: "bad id!", type: "photo", file: "123" }] }, "id"],
      [
        {
          markdown: "ok",
          media: [
            { id: "dup_1", type: "photo", file: "a" },
            { id: "dup_1", type: "photo", file: "b" },
          ],
        },
        "Duplicate",
      ],
      [
        {
          markdown: "ok",
          media: Array.from({ length: 51 }, (_, i) => ({ id: `m_${i}`, type: "photo", file: `f_${i}` })),
        },
        "50",
      ],
    ] as Array<[Record<string, unknown>, string]>).entries()) {
      const res = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 100 + Math.random(),
        method: "tools/call",
        params: { name: "send_rich_message", arguments: args },
      });
      expect((res?.result as any)?.isError).toBe(true);
      expect(String((res?.result as any)?.content?.[0]?.text)).toContain(expectedText);
    }
    expect(apiCount).toBe(0);
  });

  test("send_rich_message preserves voice mirroring when voice: true or inbound turn was voice", async () => {
    const { dir, config, store, broker, permRelay } = makeEnv({ VOICE_REPLIES: "mirror" });
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    const apiCalls: Array<{ method: string; payload: any }> = [];
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 710, chat: { id: 1111111111 } } };
    };
    const voiceOut = join(dir, "spoken.ogg");
    writeFileSync(voiceOut, Buffer.from("ogg-data"));
    let spokenText = "";
    (bot as any).sendVoiceReply = async (_chatId: number, text: string) => {
      spokenText = text;
      return { ok: true, result: { message_id: 711 } };
    };

    store.updateChatState(1111111111, { lastInboundVoice: true });
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);
    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "send_rich_message",
        arguments: {
          markdown: "**Key takeaway:** Tests pass.\n\n<details><summary>Details</summary>Hidden detail</details>",
        },
      },
    });
    const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text);
    expect(parsed.voice_message_id).toBe(711);
    expect(spokenText).toContain("Key takeaway: Tests pass.");
    expect(spokenText).not.toContain("Hidden detail");
  });

  test("callback_query on RichMessage mutates reply_markup cleanly via editMessageReplyMarkup without overwriting body", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    await (bot as any).handleUpdate({
      update_id: 901,
      callback_query: {
        id: "cb_rich_1",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        data: "reasons:701",
        message: {
          message_id: 701,
          chat: { id: 1111111111, type: "private" },
          rich_message: {
            blocks: [{ type: "paragraph", text: [{ type: "plain", text: "Rich conclusion body" }] }],
          },
          reply_markup: {
            inline_keyboard: [
              [
                { text: "Reasons", callback_data: "reasons:701" },
                { text: "🔍 Details", web_app: { url: "https://dash.example.test/?d=1" } },
              ],
            ],
          },
        },
      },
    });

    expect(apiCalls.some((c) => c.method === "editMessageText")).toBe(false);
    const markupEdit = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(markupEdit).toBeDefined();
    expect(markupEdit!.payload.reply_markup.inline_keyboard.flat().map((b: any) => b.text)).toEqual(["🔍 Details"]);
    expect(events[0].meta.event).toBe("reasons");
    expect(events[0].meta.target_excerpt).toContain("Rich conclusion body");
  });

  test("send_message_draft supports private-chat rich drafts and handleUpdate handles stopped_message_generation", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const draftRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "send_message_draft",
        arguments: {
          draft_id: 42,
          markdown: "<tg-thinking>Evaluating options…</tg-thinking>\nStreaming answer…",
          can_stop: true,
          keep_on_stop: false,
        },
      },
    });
    expect((draftRes?.result as any)?.isError).toBeUndefined();
    const call = apiCalls.find((c) => c.method === "sendRichMessageDraft");
    expect(call).toBeDefined();
    expect(call!.payload.rich_message.markdown).toContain("<tg-thinking>");
    expect(call!.payload.can_stop).toBe(true);
    expect(call!.payload.keep_on_stop).toBe(false);

    // Group chat rich draft must reject cleanly (private chats only)
    const groupErr = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: {
        name: "send_message_draft",
        arguments: { chat_id: -100123456, draft_id: 43, markdown: "Hello group" },
      },
    });
    expect((groupErr?.result as any)?.isError).toBe(true);

    // Authorized stopped_message_generation emits inbound event; unauthorized drops
    const unauth = parseInboundUpdate(
      { update_id: 910, stopped_message_generation: { chat: { id: 99999999, type: "private" }, draft_id: 42 } },
      [1111111111]
    );
    expect(unauth).toBeNull();

    await (bot as any).handleUpdate({
      update_id: 911,
      stopped_message_generation: { chat: { id: 1111111111, type: "private" }, message_thread_id: 7, draft_id: 42 },
    });
    const stopEv = events.find((e) => e.meta.event === "stopped_message_generation");
    expect(stopEv).toBeDefined();
    expect(stopEv!.meta.draft_id).toBe("42");
    expect(stopEv!.meta.message_thread_id).toBe("7");
  });

  test("edit_message supports optional rich_message upgrade and rejects conflicting inputs", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: payload.message_id } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const ok = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 6,
      method: "tools/call",
      params: { name: "edit_message", arguments: { message_id: 55, html: "<p><b>Updated</b></p>" } },
    });
    expect((ok?.result as any)?.isError).toBeUndefined();
    const editCall = apiCalls.find((c) => c.method === "editMessageText");
    expect(editCall!.payload.rich_message).toEqual({ html: "<p><b>Updated</b></p>" });

    const conflict = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 7,
      method: "tools/call",
      params: { name: "edit_message", arguments: { message_id: 55, text: "hi", markdown: "**hi**" } },
    });
    expect((conflict?.result as any)?.isError).toBe(true);
  });

  test("send_widget, edit_message_widget_data, answer_widget_query enforce Profile 1 size limits, allow_queries=false default, and honest widget_query routing", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      if (method === "editMessageWidgetData" && payload.chat_data === "same") {
        return { ok: false, error_code: 400, description: "Bad Request: message is not modified" };
      }
      return { ok: true, result: { message_id: 801, chat: { id: payload.chat_id } } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // NUL byte rejected
    const nulRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 8,
      method: "tools/call",
      params: { name: "send_widget", arguments: { html: "<div>hi\0</div>" } },
    });
    expect((nulRes?.result as any)?.isError).toBe(true);

    // Incompressible HTML > 4096B zlib-9 rejected locally before network call
    let state = 1337;
    const highEntropy = Array.from({ length: 6500 }, () => {
      state = (state * 1664525 + 1013904223) >>> 0;
      const code = 65 + (state % 58);
      return code === 92 ? "_" : String.fromCharCode(code);
    }).join("");
    expect(zlib.deflateSync(Buffer.from(`<div>${highEntropy}</div>`), { level: 9 }).length).toBeGreaterThan(4096);
    const overRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 9,
      method: "tools/call",
      params: { name: "send_widget", arguments: { html: `<div>${highEntropy}</div>` } },
    });
    expect((overRes?.result as any)?.isError).toBe(true);
    expect(apiCalls.filter((c) => c.method === "sendWidget")).toHaveLength(0);

    // Valid compact send_widget defaults allow_queries=false
    const validRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 10,
      method: "tools/call",
      params: {
        name: "send_widget",
        arguments: { html: "<p>Live</p>", caption: "Status Card", chat_data: '{"step":1}' },
      },
    });
    expect((validRes?.result as any)?.isError).toBeUndefined();
    const wCall = apiCalls.find((c) => c.method === "sendWidget");
    expect(wCall!.payload.allow_queries).toBe(false);
    expect(wCall!.payload.caption).toBe("Status Card");

    // edit_message_widget_data handles message is not modified cleanly
    const notMod = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 11,
      method: "tools/call",
      params: { name: "edit_message_widget_data", arguments: { message_id: 801, chat_data: "same" } },
    });
    const parsedNotMod = JSON.parse((notMod?.result as any).content[0].text);
    expect(parsedNotMod.success).toBe(true);
    expect(parsedNotMod.not_modified).toBe(true);

    // Unauthorized widget_query drops silently; authorized custom widget_query emits without silent auto-ack
    await (bot as any).handleUpdate({
      update_id: 920,
      widget_query: { id: "wq_unauth", from: { id: 999, is_bot: false, first_name: "Intruder" }, chat_instance: "c", data: "x" },
    });
    await (bot as any).handleUpdate({
      update_id: 921,
      widget_query: {
        id: "wq_custom",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        chat_instance: "c",
        data: "st:refresh",
        message: { message_id: 801, message_thread_id: 9, chat: { id: 1111111111, type: "private" }, date: 1 },
      },
    });

    expect(events.some((e) => e.meta.widget_query_id === "wq_unauth")).toBe(false);
    const customEv = events.find((e) => e.meta.widget_query_id === "wq_custom");
    expect(customEv).toBeDefined();
    expect(apiCalls.some((c) => c.method === "answerWidgetQuery" && c.payload.widget_query_id === "wq_custom")).toBe(false);

    // Explicit answer_widget_query call
    const ansRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 12,
      method: "tools/call",
      params: { name: "answer_widget_query", arguments: { widget_query_id: "wq_custom", data: '{"ok":true}' } },
    });
    expect((ansRes?.result as any)?.isError).toBeUndefined();
    expect(apiCalls.some((c) => c.method === "answerWidgetQuery" && c.payload.data === '{"ok":true}')).toBe(true);
  });

  test("Unified ask_user decision/question widget fits Profile 1 & <= 3696B zlib budget and settles defer & multi-select bitmask cleanly", async () => {
    const { buildQuestionWidget } = await import("../src/telegram/widgets.js");
    const built = buildQuestionWidget({
      id: "q_dec99",
      kind: "decision",
      header: "ARCHITECTURE",
      stakes: "PR scope",
      question: "How should Decisions and Questions share state?",
      options: [
        { label: "Unified broker + Widget default", description: "Single QuestionBroker store", recommended: true, pros: ["One store", "Mini App synced"], cons: ["Updates mock assertions"] },
        { label: "Separate tool", description: "Parallel store", pros: ["Isolated"], cons: ["Split state"] },
        { label: "Keyboard only", description: "Legacy sendMessage", pros: ["Minimal"], cons: ["Fails goal"] },
        { label: "Custom HTML wrapper", description: "Fixed JSON compiler", pros: ["Rigid"], cons: ["Overbuilt"] },
      ],
      multiSelect: false,
      allowOther: true,
      allowDefer: true,
    });

    expect(built.compressedBytes).toBeLessThanOrEqual(3696);
    expect(zlib.deflateSync(Buffer.from(built.html, "utf8"), { level: 9 }).length).toBe(built.compressedBytes);
    expect(built.html).toContain("font-family:system-ui,sans-serif");
    expect(built.html).not.toMatch(/BlinkMacSystemFont|Segoe UI|Roboto|<input|<select|<textarea|<progress|<meter|overflow:\s*(auto|scroll)|https?:\/\//);
    expect(built.caption.length).toBeGreaterThan(0);

    // Behavioral script verification: in-flight Sending… state and inline TIMEOUT error banner
    let rejectReq!: (err: Error) => void;
    const { elements: decEls } = runWidgetScript(
      built.html,
      { s: "open" },
      () => new Promise((_, reject) => {
        rejectReq = reject;
      })
    );
    decEls.go.click();
    expect(Boolean(decEls.go.disabled)).toBe(true);
    expect(decEls.go.textContent).toBe("Sending…");
    rejectReq(Object.assign(new Error("timeout"), { name: "WidgetRequestError", code: "TIMEOUT" }));
    await new Promise((r) => setTimeout(r, 0));
    expect(Boolean(decEls.go.disabled)).toBe(false);
    expect(decEls.er.className).toContain("sh");
    expect(decEls.er.textContent).toContain("Timed out (15s)");

    // End-to-end Defer via widget_query settles broker & locks widget cleanly via editMessageWidgetData
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 901, chat: { id: payload.chat_id } } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const askRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 13,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              kind: "decision",
              header: "Architecture",
              stakes: "Irreversible",
              question: "Unify broker?",
              allow_defer: true,
              options: [
                { label: "Yes", description: "Single store", recommended: true, pros: ["Simple"], cons: ["Edits tests"] },
                { label: "No", description: "Two stores" },
              ],
            },
          ],
        },
      },
    });
    const parsedAsk = JSON.parse((askRes?.result as any).content[0].text);
    const qid = parsedAsk.question_ids[0];
    expect(apiCalls.some((c) => c.method === "sendWidget")).toBe(true);

    await (bot as any).handleUpdate({
      update_id: 930,
      widget_query: {
        id: "wq_def1",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        chat_instance: "c",
        data: `q:${qid}:defer`,
        message: { message_id: 901, chat: { id: 1111111111, type: "private" }, date: 1 },
      },
    });

    expect(apiCalls.some((c) => c.method === "answerWidgetQuery" && c.payload.widget_query_id === "wq_def1")).toBe(true);
    const editData = apiCalls.find((c) => c.method === "editMessageWidgetData" && c.payload.message_id === 901);
    expect(editData).toBeDefined();
    expect(JSON.parse(editData!.payload.chat_data).s).toBe("deferred");
    expect(events.some((e) => e.meta.question_id === qid && e.meta.event === "question_deferred")).toBe(true);
  });

  test("ask_user multi-select widget bitmask q:<qid>:m:<base36> settles QuestionBroker, and explicit presentation='rich' uses sendRichMessage cleanly without silent group fallback", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      if (method === "sendWidget" && payload.chat_id < 0) {
        return { ok: false, error_code: 400, description: "Bad Request: widgets are available only in private chats" };
      }
      return { ok: true, result: { message_id: 950 + apiCalls.length, chat: { id: payload.chat_id } } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // Multi-select default widget
    const msRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 21,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Pick layers",
              multiSelect: true,
              options: [{ label: "Spec" }, { label: "Runtime" }, { label: "Tests" }],
            },
          ],
        },
      },
    });
    const qMultiId = JSON.parse((msRes?.result as any).content[0].text).question_ids[0];
    // Bitmask 1 (index 0) + 4 (index 2) = 5 in base36 = "5"
    await (bot as any).handleUpdate({
      update_id: 931,
      widget_query: {
        id: "wq_ms1",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        chat_instance: "c",
        data: `q:${qMultiId}:m:5`,
        message: { message_id: 951, chat: { id: 1111111111, type: "private" }, date: 1 },
      },
    });
    expect(events.some((e) => e.meta.question_id === qMultiId && e.meta.choice === "Spec, Tests")).toBe(true);

    // Group chat default ask_user fails loudly (no silent downgrade)
    const grpFail = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 22,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: { chat_id: -100999, questions: [{ question: "Proceed?", options: [{ label: "Yes" }] }] },
      },
    });
    expect((grpFail?.result as any)?.isError).toBe(true);
    expect(String((grpFail?.result as any)?.content?.[0]?.text)).toContain("private chats");

    // Explicit presentation: "rich" succeeds via sendRichMessage in group
    const grpRich = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 23,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          chat_id: -100999,
          presentation: "rich",
          questions: [{ question: "Proceed in group?", options: [{ label: "Yes" }, { label: "No" }] }],
        },
      },
    });
    expect((grpRich?.result as any)?.isError).toBeUndefined();
    expect(apiCalls.some((c) => c.method === "sendRichMessage" && c.payload.chat_id === -100999)).toBe(true);
  });

  test("send_rich_message only bypasses 30s MCP deadline when media has local files", async () => {
    const { dir } = makeEnv();
    const imgPath = join(dir, "pic.png");
    writeFileSync(imgPath, Buffer.from("png"));

    await expect(
      withToolDeadline("send_rich_message", () => new Promise(() => {}), 40, { markdown: "Plain json" })
    ).rejects.toBeInstanceOf(ToolTimeoutError);

    const uploadResult = await withToolDeadline(
      "send_rich_message",
      () => new Promise((resolve) => setTimeout(() => resolve("uploaded"), 80)),
      30,
      { html: "<img src='tg://photo?id=p1'/>", media: [{ id: "p1", type: "photo", file: imgPath }] }
    );
    expect(uploadResult).toBe("uploaded");
  });

  test("Mini App routes settle widget questions cleanly via editTelegramWidgetData without editTelegramCard", async () => {
    const { config, store, broker } = makeEnv();
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");
    const widgetEdits: Array<{ chatId: number; messageId: number; chatData: string }> = [];
    const cardEdits: number[] = [];

    const q1 = await broker.askUser({
      question: "Deploy canary?",
      presentation: "widget",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 1111111111,
    });
    broker.setMessageId(q1.questionId, 981);

    const q2 = await broker.askUser({
      question: "Close widget?",
      presentation: "widget",
      options: [{ label: "Yes" }],
      chatId: 1111111111,
    });
    broker.setMessageId(q2.questionId, 982);

    const secret = "widget-route-secret-32-bytes-long";
    const token = createSessionToken(1111111111, secret, 3600);
    const ctx = {
      store,
      broker,
      config,
      sessionSecret: secret,
      emitChannelEvent: () => {},
      editTelegramCard: async (_c: number, m: number) => {
        cardEdits.push(m);
      },
      editTelegramWidgetData: async (chatId: number, messageId: number, chatData: string) => {
        widgetEdits.push({ chatId, messageId, chatData });
      },
    };

    const ansResp = await handleApiRequest(
      new Request("http://127.0.0.1/api/app/questions/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json", Cookie: `ida_session=${token}` },
        body: JSON.stringify({ question_id: q1.questionId, option_index: 0 }),
      }),
      ctx
    );
    expect(ansResp?.status).toBe(200);

    const closeResp = await handleApiRequest(
      new Request(`http://127.0.0.1/api/app/questions/${q2.questionId}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Cookie: `ida_session=${token}` },
        body: JSON.stringify({ reason: "Superseded" }),
      }),
      ctx
    );
    expect(closeResp?.status).toBe(200);

    expect(cardEdits).toHaveLength(0);
    expect(widgetEdits).toHaveLength(2);
    expect(JSON.parse(widgetEdits[0].chatData)).toMatchObject({ s: "answered", lbl: "Yes" });
    expect(JSON.parse(widgetEdits[1].chatData)).toMatchObject({ s: "closed", lbl: "Superseded" });
  });

  test("fail-fast guards: topics missing thread abort sendRichMessage/sendWidget, widget closed renders s.lbl, force_reply failure surfaces inline err, and draft forbids media", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    store.updateChatState(1111111111, { topicsEnabled: true });
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      if (method === "sendMessage" && (payload.reply_markup as any)?.force_reply) {
        return { ok: false, description: "Bad Request: message to reply not found" };
      }
      return { ok: true, result: { message_id: 990 + apiCalls.length, chat: { id: payload.chat_id } } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // 1. send_rich_message & send_widget respect topicsEnabled routing.error before callApi
    const richNoThread = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 301,
      method: "tools/call",
      params: { name: "send_rich_message", arguments: { markdown: "Missing thread" } },
    });
    expect((richNoThread?.result as any)?.isError).toBe(true);

    const widgetNoThread = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 302,
      method: "tools/call",
      params: { name: "send_widget", arguments: { html: "<p>Missing thread</p>" } },
    });
    expect((widgetNoThread?.result as any)?.isError).toBe(true);
    expect(apiCalls.some((c) => c.method === "sendRichMessage" || c.method === "sendWidget")).toBe(false);

    // 2. send_message_draft rejects undeclared media
    const draftMedia = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 303,
      method: "tools/call",
      params: { name: "send_message_draft", arguments: { draft_id: 9, markdown: "hi", media: [] } },
    });
    expect((draftMedia?.result as any)?.isError).toBe(true);
    expect(String((draftMedia?.result as any)?.content?.[0]?.text)).toContain("media");

    // 3. widget closed state renders close reason (s.lbl) and hides interactive chrome
    const { buildQuestionWidget } = await import("../src/telegram/widgets.js");
    const built = buildQuestionWidget({
      id: "q_close_lbl",
      question: "Proceed?",
      options: [{ label: "Yes" }],
    });
    const { elements: closedEls } = runWidgetScript(built.html, { s: "closed", lbl: "Superseded" });
    expect(closedEls.dt.textContent).toBe("Closed: Superseded");
    expect(closedEls.dc.className).toContain("sh");
    expect(closedEls.os.style.display).toBe("none");
    expect(closedEls.ft.style.display).toBe("none");

    // 4. widget_query `other` when force_reply fails does not claim awaiting_reply; surfaces inline err
    store.updateChatState(1111111111, { activeThreadId: 77, topicsEnabled: true });
    bot.setTopicsEnabled(1111111111, true);
    const qOther = await broker.askUser({
      question: "Other fail test?",
      presentation: "widget",
      options: [{ label: "A" }],
      chatId: 1111111111,
      messageThreadId: 77,
    });
    broker.setMessageId(qOther.questionId, 995);

    await (bot as any).handleUpdate({
      update_id: 999,
      widget_query: {
        id: "wq_other_fail",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        chat_instance: "c",
        data: `q:${qOther.questionId}:other`,
        message: { message_id: 995, message_thread_id: 77, chat: { id: 1111111111, type: "private" }, date: 1 },
      },
    });

    const ansFail = apiCalls.find((c) => c.method === "answerWidgetQuery" && c.payload.widget_query_id === "wq_other_fail");
    expect(JSON.parse(ansFail!.payload.data)).toMatchObject({ ok: false });
    const editErr = apiCalls.find((c) => c.method === "editMessageWidgetData" && c.payload.message_id === 995);
    expect(JSON.parse(editErr!.payload.chat_data)).toMatchObject({ err: "Bad Request: message to reply not found" });
    expect(events.some((e) => e.meta.event === "question_delivery_failed" && e.meta.question_id === qOther.questionId)).toBe(true);
  });

  test("presentation='rich' supports allow_defer callback settlement, parseInboundUpdate reads rich_message excerpts, and Status Tracker starter hides Refresh on done", async () => {
    const { config, store, broker, permRelay } = makeEnv();
    const apiCalls: Array<{ method: string; payload: any }> = [];
    const events: Array<{ content: string; meta: Record<string, string> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (c, m) => events.push({ content: c, meta: m }), store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 998, chat: { id: payload.chat_id } } };
    };
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const askRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 401,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          chat_id: -100888,
          presentation: "rich",
          questions: [
            {
              kind: "decision",
              question: "Proceed in group?",
              allow_defer: true,
              options: [{ label: "Ship" }, { label: "Hold" }],
            },
          ],
        },
      },
    });
    const qid = JSON.parse((askRes?.result as any).content[0].text).question_ids[0];
    const richSend = apiCalls.find((c) => c.method === "sendRichMessage");
    expect(richSend).toBeDefined();
    expect(richSend!.payload.reply_markup.inline_keyboard.flat().some((b: any) => b.callback_data === `q:${qid}:0:defer`)).toBe(true);

    await (bot as any).handleUpdate({
      update_id: 940,
      callback_query: {
        id: "cb_rich_defer",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        data: `q:${qid}:0:defer`,
        message: {
          message_id: 998,
          date: 1,
          chat: { id: -100888, type: "supergroup" },
          rich_message: { markdown: "**Proceed in group?**" },
        },
      },
    });
    expect(apiCalls.some((c) => c.method === "editMessageReplyMarkup" && c.payload.message_id === 998)).toBe(true);
    expect(apiCalls.some((c) => c.method === "editMessageText" && c.payload.message_id === 998)).toBe(false);
    expect(events.some((e) => e.meta.event === "question_deferred" && e.meta.question_id === qid)).toBe(true);

    // parseInboundUpdate reads rich_message excerpts directly
    const parsedReasons = parseInboundUpdate(
      {
        update_id: 941,
        callback_query: {
          id: "cb_r_rich",
          from: { id: 1111111111, is_bot: false, first_name: "Alex" },
          data: "reasons:998",
          message: {
            message_id: 998,
            date: 1,
            chat: { id: 1111111111, type: "private" },
            rich_message: { markdown: "**Headline:** Direct rich excerpt" },
          },
        },
      },
      [1111111111]
    );
    expect(parsedReasons?.meta.target_excerpt).toBe("Headline: Direct rich excerpt");

    // Status Tracker HTML template in references/widgets.md validates cleanly and hides Refresh on done
    const { validateWidgetHtml } = await import("../src/telegram/widgets.js");
    const refMd = readFileSync(join(import.meta.dir, "..", "skills", "telegram", "references", "widgets.md"), "utf8");
    const htmlMatch = refMd.match(/```html\n([\s\S]*?)\n```/);
    expect(htmlMatch).not.toBeNull();
    const statusHtml = htmlMatch![1];
    expect(statusHtml).not.toContain("\\\\u2014");
    const check = validateWidgetHtml(statusHtml);
    expect(check.ok).toBe(true);
    if (check.ok) {
      expect(check.compressedBytes).toBeLessThanOrEqual(3696);
    }
    const statusMatch = statusHtml.match(/<script>([\s\S]*?)<\/script>/);
    const stIds = ["pl", "up", "ti", "fl", "pc", "er", "ss", "nt", "rf"];
    const stEls: Record<string, any> = {};
    for (const id of stIds) {
      stEls[id] = { style: {}, className: "", textContent: "", innerHTML: "", disabled: false, addEventListener() {} };
    }
    const runner = new Function("window", "document", statusMatch![1]);
    runner(
      {
        TelegramWidget: {
          chatData: JSON.stringify({ t: "Pipeline", s: "done", pct: 100, act: 1, steps: [] }),
          onEvent() {},
          ready() {},
          request: async () => "",
        },
      },
      { getElementById: (id: string) => stEls[id] || null }
    );
    expect(stEls.rf.className).toBe("bt");
  });
});
