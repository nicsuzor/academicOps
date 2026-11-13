import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadConfig } from "../src/config.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { PluginStore } from "../src/store.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";

interface CapturedCall {
  method: string;
  body: Record<string, unknown>;
  formData?: FormData;
}

describe("Rich media, location, interactivity, draft streaming, and poll tools", () => {
  const originalFetch = globalThis.fetch;
  let apiCalls: CapturedCall[] = [];
  let nextMessageId = 500;
  let tempDir: string;

  beforeEach(() => {
    apiCalls = [];
    nextMessageId = 500;
    tempDir = mkdtempSync(join(tmpdir(), "ida-tg-media-test-"));

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = url.split("/").pop() || "";

      let body: Record<string, unknown> = {};
      let formData: FormData | undefined;
      if (init?.body instanceof FormData) {
        formData = init.body;
        for (const [key, val] of formData.entries()) {
          if (typeof val === "string") {
            try {
              const parsed = JSON.parse(val);
              body[key] = parsed;
            } catch {
              body[key] = val;
            }
          } else {
            body[key] = `[Blob:${(val as Blob).size}]`;
          }
        }
      } else if (typeof init?.body === "string") {
        body = JSON.parse(init.body) as Record<string, unknown>;
      }
      apiCalls.push({ method, body, formData });

      if (
        method === "sendPhoto" ||
        method === "sendDocument" ||
        method === "sendVideo" ||
        method === "sendAnimation" ||
        method === "sendAudio" ||
        method === "sendVideoNote" ||
        method === "sendLocation" ||
        method === "sendVenue" ||
        method === "sendContact"
      ) {
        const id = nextMessageId++;
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: id,
              date: Math.floor(Date.now() / 1000),
              chat: { id: Number(body.chat_id ?? 12345), type: "supergroup" },
              ...(body.message_thread_id !== undefined ? { message_thread_id: Number(body.message_thread_id) } : {}),
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (method === "sendMediaGroup") {
        const mediaArr = Array.isArray(body.media) ? body.media : [];
        const result = mediaArr.map(() => ({
          message_id: nextMessageId++,
          date: Math.floor(Date.now() / 1000),
          chat: { id: Number(body.chat_id ?? 12345), type: "supergroup" },
          ...(body.message_thread_id !== undefined ? { message_thread_id: Number(body.message_thread_id) } : {}),
        }));
        return new Response(JSON.stringify({ ok: true, result }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (method === "sendDice") {
        const id = nextMessageId++;
        const emoji = (body.emoji as string) || "🎲";
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: id,
              date: Math.floor(Date.now() / 1000),
              chat: { id: Number(body.chat_id ?? 12345), type: "supergroup" },
              ...(body.message_thread_id !== undefined ? { message_thread_id: Number(body.message_thread_id) } : {}),
              dice: { emoji, value: 6 },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (method === "sendChatAction" || method === "sendMessageDraft") {
        return new Response(JSON.stringify({ ok: true, result: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (method === "sendPoll") {
        const id = nextMessageId++;
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: id,
              date: Math.floor(Date.now() / 1000),
              chat: { id: Number(body.chat_id ?? 12345), type: "supergroup" },
              ...(body.message_thread_id !== undefined ? { message_thread_id: Number(body.message_thread_id) } : {}),
              poll: {
                id: "poll-abc-123",
                question: body.question,
                options: Array.isArray(body.options)
                  ? body.options.map((o: { text: string }) => ({ text: o.text, voter_count: 0 }))
                  : [],
                total_voter_count: 0,
                is_closed: false,
                is_anonymous: body.is_anonymous ?? true,
                type: body.type ?? "regular",
                allows_multiple_answers: body.allows_multiple_answers ?? false,
              },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (method === "stopPoll") {
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              id: "poll-abc-123",
              question: "Stopped poll?",
              options: [
                { text: "Yes", voter_count: 3 },
                { text: "No", voter_count: 1 },
              ],
              total_voter_count: 4,
              is_closed: true,
              is_anonymous: true,
              type: "regular",
              allows_multiple_answers: false,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      return new Response(JSON.stringify({ ok: true, result: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    rmSync(tempDir, { recursive: true, force: true });
  });

  function createHarness(defaultChatId = 12345, activeThreadId?: number, lastInboundMessageId?: number) {
    const config = loadConfig({
      MINI_APP_URL: "https://dash.example.test/app",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: String(defaultChatId),
      STATE_DIR: tempDir,
    });
    const store = new PluginStore(config.stateDir);
    if (activeThreadId !== undefined || lastInboundMessageId !== undefined) {
      store.updateChatState(defaultChatId, {
        ...(activeThreadId !== undefined ? { activeThreadId } : {}),
        ...(lastInboundMessageId !== undefined ? { lastInboundMessageId } : {}),
      });
    }
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);
    return { bot, store, mcp };
  }

  async function callMcpTool(mcp: StdioMcpServer, name: string, args: Record<string, unknown>) {
    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: { name, arguments: args },
    });
    const result = res?.result as { content: Array<{ text: string }>; isError?: boolean };
    return {
      isError: result?.isError,
      payload: JSON.parse(result.content[0].text) as Record<string, unknown>,
    };
  }

  test("lists all 15 rich media, location, interactivity, draft, and poll tools via MCP tools/list", async () => {
    const { mcp } = createHarness();
    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
    });
    const tools = (res?.result as { tools: Array<{ name: string }> }).tools.map((t) => t.name);
    const expected = [
      "send_photo",
      "send_document",
      "send_video",
      "send_animation",
      "send_media_group",
      "send_audio",
      "send_video_note",
      "send_location",
      "send_venue",
      "send_contact",
      "send_dice",
      "send_chat_action",
      "send_message_draft",
      "send_poll",
      "stop_poll",
    ];
    for (const toolName of expected) {
      expect(tools).toContain(toolName);
    }
  });

  test("single-media tools route to default chat and active thread, format Markdown captions, and support inline buttons", async () => {
    const { mcp } = createHarness(777, 88);

    const photoRes = await callMcpTool(mcp, "send_photo", {
      photo: "https://example.com/chart.png",
      caption: "Here is **bold** summary",
      has_spoiler: true,
      buttons: [{ label: "Open", callback_data: "open_chart" }],
    });
    expect(photoRes.isError).toBeUndefined();
    expect(photoRes.payload).toEqual({
      success: true,
      message_id: 500,
      message_thread_id: 88,
    });
    expect(apiCalls[0].method).toBe("sendPhoto");
    expect(apiCalls[0].body.chat_id).toBe(777);
    expect(apiCalls[0].body.message_thread_id).toBe(88);
    expect(apiCalls[0].body.photo).toBe("https://example.com/chart.png");
    expect(apiCalls[0].body.caption).toBe("Here is bold summary");
    expect(apiCalls[0].body.caption_entities).toEqual([{ type: "bold", offset: 8, length: 4 }]);
    expect(apiCalls[0].body.has_spoiler).toBe(true);
    expect(apiCalls[0].body.reply_markup).toEqual({
      inline_keyboard: [[{ text: "Open", callback_data: "open_chart" }]],
    });

    const docRes = await callMcpTool(mcp, "send_document", {
      document: "file_id_doc_1",
      caption: "Report `v1`",
      disable_content_type_detection: true,
    });
    expect(docRes.isError).toBeUndefined();
    expect(docRes.payload.message_thread_id).toBe(88);
    expect(apiCalls[1].method).toBe("sendDocument");
    expect(apiCalls[1].body.document).toBe("file_id_doc_1");
    expect(apiCalls[1].body.disable_content_type_detection).toBe(true);
    expect(apiCalls[1].body.caption).toBe("Report v1");

    const videoRes = await callMcpTool(mcp, "send_video", {
      video: "file_id_vid_1",
      duration: 30,
      width: 1920,
      height: 1080,
      supports_streaming: true,
      has_spoiler: false,
    });
    expect(videoRes.isError).toBeUndefined();
    expect(apiCalls[2].method).toBe("sendVideo");
    expect(apiCalls[2].body.duration).toBe(30);
    expect(apiCalls[2].body.width).toBe(1920);
    expect(apiCalls[2].body.height).toBe(1080);
    expect(apiCalls[2].body.supports_streaming).toBe(true);

    const animRes = await callMcpTool(mcp, "send_animation", {
      animation: "file_id_anim_1",
      duration: 5,
      has_spoiler: true,
    });
    expect(animRes.isError).toBeUndefined();
    expect(apiCalls[3].method).toBe("sendAnimation");
    expect(apiCalls[3].body.animation).toBe("file_id_anim_1");
    expect(apiCalls[3].body.has_spoiler).toBe(true);

    const audioRes = await callMcpTool(mcp, "send_audio", {
      audio: "file_id_aud_1",
      duration: 180,
      performer: "Agent",
      title: "Briefing",
    });
    expect(audioRes.isError).toBeUndefined();
    expect(apiCalls[4].method).toBe("sendAudio");
    expect(apiCalls[4].body.performer).toBe("Agent");
    expect(apiCalls[4].body.title).toBe("Briefing");

    const videoNoteRes = await callMcpTool(mcp, "send_video_note", {
      video_note: "file_id_vnote_1",
      duration: 12,
      length: 360,
    });
    expect(videoNoteRes.isError).toBeUndefined();
    expect(apiCalls[5].method).toBe("sendVideoNote");
    expect(apiCalls[5].body.video_note).toBe("file_id_vnote_1");
    expect(apiCalls[5].body.length).toBe(360);
  });

  test("single-media tools upload local files via multipart FormData when path exists on disk", async () => {
    const { mcp } = createHarness(777, 42);
    const localPhoto = join(tempDir, "plot.png");
    writeFileSync(localPhoto, "fake-png-bytes");

    const res = await callMcpTool(mcp, "send_photo", {
      photo: localPhoto,
      caption: "Local **plot**",
    });
    expect(res.isError).toBeUndefined();
    expect(res.payload).toEqual({
      success: true,
      message_id: 500,
      message_thread_id: 42,
    });
    expect(apiCalls[0].method).toBe("sendPhoto");
    expect(apiCalls[0].formData).toBeDefined();
    expect(apiCalls[0].body.chat_id).toBe(777);
    expect(apiCalls[0].body.message_thread_id).toBe(42);
    expect(apiCalls[0].body.photo).toBe("[Blob:14]");
    expect(apiCalls[0].body.caption).toBe("Local plot");
    expect(apiCalls[0].body.caption_entities).toEqual([{ type: "bold", offset: 6, length: 4 }]);
  });

  test("send_media_group sends 2-10 album items with captions and local file attachments, and rejects invalid item counts", async () => {
    const { mcp } = createHarness(555, 19);
    const localDoc = join(tempDir, "part1.png");
    writeFileSync(localDoc, "part-1-bytes");

    const okRes = await callMcpTool(mcp, "send_media_group", {
      media: [
        { type: "photo", media: localDoc, caption: "Slide **one**", has_spoiler: true },
        { type: "photo", media: "https://example.com/slide2.png", caption: "Slide *two*" },
      ],
    });
    expect(okRes.isError).toBeUndefined();
    expect(okRes.payload).toEqual({
      success: true,
      message_ids: [500, 501],
      message_thread_id: 19,
    });
    expect(apiCalls[0].method).toBe("sendMediaGroup");
    expect(apiCalls[0].formData).toBeDefined();
    expect(apiCalls[0].body.chat_id).toBe(555);
    expect(apiCalls[0].body.message_thread_id).toBe(19);
    expect(apiCalls[0].body.file_0).toBe("[Blob:12]");
    expect(apiCalls[0].body.media).toEqual([
      {
        type: "photo",
        media: "attach://file_0",
        caption: "Slide one",
        caption_entities: [{ type: "bold", offset: 6, length: 3 }],
        has_spoiler: true,
      },
      {
        type: "photo",
        media: "https://example.com/slide2.png",
        caption: "Slide two",
        caption_entities: [{ type: "italic", offset: 6, length: 3 }],
      },
    ]);

    const tooFew = await callMcpTool(mcp, "send_media_group", {
      media: [{ type: "photo", media: "https://example.com/only-one.png" }],
    });
    expect(tooFew.isError).toBe(true);
    expect(tooFew.payload.success).toBe(false);
    expect(String(tooFew.payload.error)).toContain("2");
  });

  test("send_location, send_venue, send_contact, and send_dice route to active thread and validate coordinates", async () => {
    const { mcp } = createHarness(321, 77);

    const locRes = await callMcpTool(mcp, "send_location", {
      latitude: -27.4705,
      longitude: 153.026,
      horizontal_accuracy: 15,
    });
    expect(locRes.isError).toBeUndefined();
    expect(locRes.payload).toEqual({
      success: true,
      message_id: 500,
      message_thread_id: 77,
    });
    expect(apiCalls[0].method).toBe("sendLocation");
    expect(apiCalls[0].body.latitude).toBe(-27.4705);
    expect(apiCalls[0].body.longitude).toBe(153.026);
    expect(apiCalls[0].body.message_thread_id).toBe(77);

    const badLoc = await callMcpTool(mcp, "send_location", {
      latitude: 105,
      longitude: 153.026,
    });
    expect(badLoc.isError).toBe(true);
    expect(badLoc.payload.success).toBe(false);

    const venueRes = await callMcpTool(mcp, "send_venue", {
      latitude: -27.477,
      longitude: 153.028,
      title: "QUT Gardens Point",
      address: "2 George St, Brisbane",
    });
    expect(venueRes.isError).toBeUndefined();
    expect(apiCalls[1].method).toBe("sendVenue");
    expect(apiCalls[1].body.title).toBe("QUT Gardens Point");
    expect(apiCalls[1].body.address).toBe("2 George St, Brisbane");
    expect(apiCalls[1].body.message_thread_id).toBe(77);

    const contactRes = await callMcpTool(mcp, "send_contact", {
      phone_number: "+61400000000",
      first_name: "Ada",
      last_name: "Lovelace",
    });
    expect(contactRes.isError).toBeUndefined();
    expect(apiCalls[2].method).toBe("sendContact");
    expect(apiCalls[2].body.phone_number).toBe("+61400000000");
    expect(apiCalls[2].body.first_name).toBe("Ada");
    expect(apiCalls[2].body.last_name).toBe("Lovelace");
    expect(apiCalls[2].body.message_thread_id).toBe(77);

    const diceRes = await callMcpTool(mcp, "send_dice", {
      emoji: "🎯",
    });
    expect(diceRes.isError).toBeUndefined();
    expect(diceRes.payload).toEqual({
      success: true,
      message_id: 503,
      value: 6,
      emoji: "🎯",
      message_thread_id: 77,
    });
    expect(apiCalls[3].method).toBe("sendDice");
    expect(apiCalls[3].body.emoji).toBe("🎯");
    expect(apiCalls[3].body.message_thread_id).toBe(77);
  });

  test("send_chat_action and send_message_draft route to active thread and validate draft_id", async () => {
    const { mcp } = createHarness(654, 12);

    const actionRes = await callMcpTool(mcp, "send_chat_action", {
      action: "upload_document",
    });
    expect(actionRes.isError).toBeUndefined();
    expect(actionRes.payload).toEqual({
      success: true,
      message_thread_id: 12,
    });
    expect(apiCalls[0].method).toBe("sendChatAction");
    expect(apiCalls[0].body).toEqual({
      chat_id: 654,
      action: "upload_document",
      message_thread_id: 12,
    });

    const draftRes = await callMcpTool(mcp, "send_message_draft", {
      draft_id: 9001,
      text: "Drafting **response**...",
    });
    expect(draftRes.isError).toBeUndefined();
    expect(draftRes.payload).toEqual({
      success: true,
      draft_id: 9001,
      message_thread_id: 12,
    });
    expect(apiCalls[1].method).toBe("sendMessageDraft");
    expect(apiCalls[1].body).toEqual({
      chat_id: 654,
      draft_id: 9001,
      text: "Drafting response...",
      entities: [{ type: "bold", offset: 9, length: 8 }],
      message_thread_id: 12,
    });

    const zeroDraft = await callMcpTool(mcp, "send_message_draft", {
      draft_id: 0,
      text: "Invalid draft id",
    });
    expect(zeroDraft.isError).toBe(true);
    expect(zeroDraft.payload.success).toBe(false);
  });

  test("send_poll and stop_poll create polls, validate bounds, and close polls with error propagation", async () => {
    const { mcp } = createHarness(888, 33);

    const pollRes = await callMcpTool(mcp, "send_poll", {
      question: "Which deployment target should we use?",
      options: ["Staging", { text: "Production" }],
      is_anonymous: false,
      allows_multiple_answers: false,
      type: "quiz",
      correct_option_id: 0,
      explanation: "Always test on **Staging** first",
    });
    expect(pollRes.isError).toBeUndefined();
    expect(pollRes.payload).toEqual({
      success: true,
      message_id: 500,
      poll_id: "poll-abc-123",
      message_thread_id: 33,
    });
    expect(apiCalls[0].method).toBe("sendPoll");
    expect(apiCalls[0].body.chat_id).toBe(888);
    expect(apiCalls[0].body.message_thread_id).toBe(33);
    expect(apiCalls[0].body.question).toBe("Which deployment target should we use?");
    expect(apiCalls[0].body.options).toEqual([{ text: "Staging" }, { text: "Production" }]);
    expect(apiCalls[0].body.is_anonymous).toBe(false);
    expect(apiCalls[0].body.type).toBe("quiz");
    expect(apiCalls[0].body.correct_option_id).toBe(0);
    expect(apiCalls[0].body.explanation).toBe("Always test on Staging first");
    expect(apiCalls[0].body.explanation_entities).toEqual([{ type: "bold", offset: 15, length: 7 }]);

    const badPoll = await callMcpTool(mcp, "send_poll", {
      question: "Only one option?",
      options: ["Solo"],
    });
    expect(badPoll.isError).toBe(true);
    expect(badPoll.payload.success).toBe(false);

    const stopRes = await callMcpTool(mcp, "stop_poll", {
      message_id: 500,
    });
    expect(stopRes.isError).toBeUndefined();
    expect(stopRes.payload).toEqual({
      success: true,
      message_id: 500,
      message_thread_id: 33,
      poll: {
        id: "poll-abc-123",
        question: "Stopped poll?",
        options: [
          { text: "Yes", voter_count: 3 },
          { text: "No", voter_count: 1 },
        ],
        total_voter_count: 4,
        is_closed: true,
      },
    });
    expect(apiCalls[1].method).toBe("stopPoll");
    expect(apiCalls[1].body).toEqual({
      chat_id: 888,
      message_id: 500,
    });
  });

  test("unthreaded chats attach reply_parameters to the last inbound message when sending media or polls", async () => {
    const { mcp } = createHarness(444, undefined, 910);

    const res = await callMcpTool(mcp, "send_photo", {
      photo: "file_id_unthreaded",
    });
    expect(res.isError).toBeUndefined();
    expect(res.payload).toEqual({
      success: true,
      message_id: 500,
    });
    expect(apiCalls[0].method).toBe("sendPhoto");
    expect(apiCalls[0].body.reply_parameters).toEqual({ message_id: 910 });
    expect(apiCalls[0].body.message_thread_id).toBeUndefined();
  });

  test("inherits thread from reply_to message, retries plain caption on entity parse error, and surfaces Telegram API errors verbatim", async () => {
    const { bot, mcp } = createHarness(444, 10);
    bot.recordMessageThread(701, 99);

    let rejectEntitiesOnce = true;
    const baseFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = url.split("/").pop() || "";
      if (method === "sendPhoto" && rejectEntitiesOnce) {
        rejectEntitiesOnce = false;
        const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
        apiCalls.push({ method, body });
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: can't parse entities" }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        );
      }
      if (method === "stopPoll") {
        const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
        apiCalls.push({ method, body });
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: poll has already been closed" }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        );
      }
      return baseFetch(input, init);
    }) as typeof fetch;

    const photoRes = await callMcpTool(mcp, "send_photo", {
      photo: "file_id_thread_inherit",
      caption: "Retry **caption**",
      reply_to: 701,
    });
    expect(photoRes.isError).toBeUndefined();
    expect(photoRes.payload).toEqual({
      success: true,
      message_id: 500,
      message_thread_id: 99,
    });
    expect(apiCalls.length).toBe(2);
    expect(apiCalls[0].body.message_thread_id).toBe(99);
    expect(apiCalls[0].body.caption_entities).toBeDefined();
    expect(apiCalls[1].body.message_thread_id).toBe(99);
    expect(apiCalls[1].body.caption).toBe("Retry caption");
    expect(apiCalls[1].body.caption_entities).toBeUndefined();

    const stopErr = await callMcpTool(mcp, "stop_poll", {
      message_id: 500,
    });
    expect(stopErr.isError).toBe(true);
    expect(stopErr.payload).toEqual({
      success: false,
      error: "Bad Request: poll has already been closed",
    });
  });
});
